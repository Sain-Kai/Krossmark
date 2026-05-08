import json
import os
import subprocess
import sys
from pathlib import Path

from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser

from .models import Device, TriggerEvent, BurstCapture, AnalysisResult, Alert
from .serializers import (
    DeviceSerializer,
    DeviceRegisterSerializer,
    TriggerEventSerializer,
    BurstCaptureSerializer,
    AnalysisResultSerializer,
    AlertSerializer,
)
from .auth import DeviceKeyAuthentication
from .services.analysis_service import AnalysisOrchestrator


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve_test_script_path() -> Path:
    return _project_root() / "vision" / "core" / "test.py"


def _write_trigger_payload_file(trigger_payload: dict) -> Path:
    project_root = _project_root()
    payload_path = project_root / "trigger_payload.json"
    payload_path.write_text(
        json.dumps(trigger_payload, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    return payload_path


def _start_test_script(trigger_payload: dict) -> Path:
    script_path = _resolve_test_script_path()
    project_root = _project_root()
    payload_path = _write_trigger_payload_file(trigger_payload)

    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_root) + os.pathsep + env.get("PYTHONPATH", "")
    env["KROSSMARK_TRIGGER_PAYLOAD"] = json.dumps(trigger_payload, ensure_ascii=False, default=str)
    env["KROSSMARK_TRIGGER_PAYLOAD_FILE"] = str(payload_path)

    log_path = project_root / "trigger_log.txt"
    log_file = open(log_path, "a", buffering=1, encoding="utf-8")

    creationflags = 0
    if sys.platform.startswith("win"):
        creationflags = subprocess.CREATE_NEW_CONSOLE

    subprocess.Popen(
        [
            sys.executable,
            str(script_path),
            "--trigger-payload-file",
            str(payload_path),
        ],
        cwd=str(project_root),
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        creationflags=creationflags,
    )

    print(f"[BACKEND] test.py launched -> {script_path}")
    print(f"[BACKEND] log file        -> {log_path}")
    return script_path


class HealthCheckView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            "status": "ok",
            "service": "krossmark-backend",
            "time": timezone.now().isoformat(),
        })


class DeviceViewSet(viewsets.ModelViewSet):
    queryset = Device.objects.all().order_by("-created_at")
    serializer_class = DeviceSerializer
    permission_classes = [AllowAny]

    @action(detail=False, methods=["post"], url_path="register")
    def register(self, request):
        serializer = DeviceRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        device = Device.objects.create(**serializer.validated_data)
        return Response(DeviceSerializer(device).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"], url_path="status")
    def device_status(self, request, pk=None):
        device = self.get_object()
        return Response({
            "device_id": str(device.id),
            "name": device.name,
            "device_type": device.device_type,
            "is_active": device.is_active,
            "last_seen": device.last_seen,
            "created_at": device.created_at,
        })


class TriggerEventViewSet(viewsets.ModelViewSet):
    queryset = TriggerEvent.objects.select_related("device").all().order_by("-created_at")
    serializer_class = TriggerEventSerializer
    authentication_classes = [DeviceKeyAuthentication]
    permission_classes = [AllowAny]
    parser_classes = [JSONParser]

    def perform_create(self, serializer):
        device = None
        key = self.request.headers.get("X-Device-Key")
        auth = self.request.headers.get("Authorization", "")
        if not key and auth.startswith("Device "):
            key = auth.split(" ", 1)[1].strip()
        if key:
            device = Device.objects.filter(api_key=key, is_active=True).first()
        if device is None:
            raise ValueError("A valid device key is required.")
        device.last_seen = timezone.now()
        device.save(update_fields=["last_seen"])
        serializer.save(device=device)


class BurstCaptureViewSet(viewsets.ModelViewSet):
    queryset = BurstCapture.objects.select_related("device", "trigger").all().order_by("-created_at")
    serializer_class = BurstCaptureSerializer
    authentication_classes = [DeviceKeyAuthentication]
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        device_id = data.get("device_id")
        trigger_id = data.get("trigger_id")

        device = Device.objects.filter(id=device_id).first() if device_id else None
        trigger = TriggerEvent.objects.filter(id=trigger_id).first() if trigger_id else None

        if device is None:
            return Response(
                {"detail": "device_id is required and must be valid."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        burst = BurstCapture.objects.create(
            device=device,
            trigger=trigger,
            frame_count=int(data.get("frame_count") or 0),
            audio_sample_rate=int(data.get("audio_sample_rate") or 48000),
            metadata=data.get("metadata") if isinstance(data.get("metadata"), dict) else {},
        )

        if "video_file" in request.FILES:
            burst.video_file = request.FILES["video_file"]
        if "audio_file" in request.FILES:
            burst.audio_file = request.FILES["audio_file"]
        burst.save()

        try:
            result = AnalysisOrchestrator().analyze_and_persist(burst)
            return Response({
                "burst": BurstCaptureSerializer(burst).data,
                "result": AnalysisResultSerializer(result).data,
            }, status=status.HTTP_201_CREATED)
        except Exception as exc:
            burst.status = BurstCapture.Status.FAILED
            burst.error_message = str(exc)
            burst.save(update_fields=["status", "error_message"])
            return Response({"detail": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=["post"], url_path="analyze")
    def analyze(self, request, pk=None):
        burst = self.get_object()
        result = AnalysisOrchestrator().analyze_and_persist(burst)
        return Response({
            "burst": BurstCaptureSerializer(burst).data,
            "result": AnalysisResultSerializer(result).data,
        })


class AnalysisResultViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AnalysisResult.objects.select_related(
        "burst", "burst__device"
    ).all().order_by("-created_at")
    serializer_class = AnalysisResultSerializer
    permission_classes = [AllowAny]

    @action(detail=False, methods=["get"], url_path="latest")
    def latest(self, request):
        result = self.get_queryset().first()
        if not result:
            return Response({}, status=status.HTTP_404_NOT_FOUND)
        return Response(self.get_serializer(result).data)


class AlertViewSet(viewsets.ModelViewSet):
    queryset = Alert.objects.select_related(
        "analysis_result", "analysis_result__burst"
    ).all().order_by("-created_at")
    serializer_class = AlertSerializer
    permission_classes = [AllowAny]

    @action(detail=True, methods=["post"], url_path="ack")
    def ack(self, request, pk=None):
        alert = self.get_object()
        alert.acknowledged = True
        alert.ack_by = request.data.get("ack_by", "dashboard")
        alert.save(update_fields=["acknowledged", "ack_by"])
        return Response(self.get_serializer(alert).data)


class IngestAndAnalyzeView(APIView):
    """
    One-shot endpoint for sensor gateways / pi nodes.
    POST JSON or multipart with:
      - device_id
      - trigger_id optional
      - video_file optional
      - audio_file optional
      - metadata optional JSON
    """
    authentication_classes = [DeviceKeyAuthentication]
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        data = request.data
        device_id = data.get("device_id")
        device = Device.objects.filter(id=device_id).first()
        if device is None:
            return Response(
                {"detail": "device_id missing or invalid"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        trigger = None
        trigger_id = data.get("trigger_id")
        if trigger_id:
            trigger = TriggerEvent.objects.filter(id=trigger_id).first()

        burst = BurstCapture.objects.create(
            device=device,
            trigger=trigger,
            frame_count=int(data.get("frame_count") or 0),
            audio_sample_rate=int(data.get("audio_sample_rate") or 48000),
            metadata=data.get("metadata") if isinstance(data.get("metadata"), dict) else {},
        )

        if "video_file" in request.FILES:
            burst.video_file = request.FILES["video_file"]
        if "audio_file" in request.FILES:
            burst.audio_file = request.FILES["audio_file"]
        burst.save()

        result = AnalysisOrchestrator().analyze_and_persist(burst)

        return Response({
            "burst": BurstCaptureSerializer(burst).data,
            "result": AnalysisResultSerializer(result).data,
        }, status=status.HTTP_201_CREATED)


class ESP32TriggerView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [JSONParser]

    def post(self, request):
        data = request.data if isinstance(request.data, dict) else {}

        print("\n[BACKEND] TRIGGER RECEIVED")
        print(data)

        burst_id = data.get("burst_id")
        sensor_container = data.get("sensor_data") if isinstance(data.get("sensor_data"), dict) else {}

        adxl = data.get("adxl") if isinstance(data.get("adxl"), dict) else sensor_container.get("adxl", {})
        fsr = data.get("fsr") if isinstance(data.get("fsr"), dict) else sensor_container.get("fsr", {})

        print("\n[SENSOR DATA RECEIVED]")
        print("ADXL:", adxl)
        print("FSR :", fsr)

        device, _ = Device.objects.get_or_create(
            serial_number="PI-RELAY-001",
            defaults={
                "name": "Raspberry Pi Relay",
                "device_type": Device.DeviceType.PI,
                "location_tag": "entrance",
            },
        )

        device.last_seen = timezone.now()
        device.save(update_fields=["last_seen"])

        trigger = TriggerEvent.objects.create(
            device=device,
            source_level=TriggerEvent.SourceLevel.PI,
            pir_triggered=False,
            mic_triggered=False,
            confidence=0.0,
            sensor_payload={
                "adxl": adxl,
                "fsr": fsr,
            },
        )

        trigger_payload = {
            "source": data.get("source", "node2"),
            "burst_id": burst_id,
            "ts": data.get("ts", timezone.now().timestamp()),
            "note": data.get("note", "relay trigger from Pi"),
            "trigger_id": str(trigger.id),
            "sensor_data": {
                "adxl": adxl,
                "fsr": fsr,
            },
        }

        print("\n[BACKEND] SENSOR PAYLOAD FOR TEST.PY")
        print(trigger_payload)

        try:
            _start_test_script(trigger_payload)
        except Exception as exc:
            print("[BACKEND] Failed to launch test.py:", exc)
            return Response(
                {"status": "error", "detail": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "status": "triggered",
                "message": "test.py launched with sensor data",
                "trigger_id": str(trigger.id),
                "burst_id": burst_id,
                "sensor_data": trigger_payload["sensor_data"],
            },
            status=202,
        )