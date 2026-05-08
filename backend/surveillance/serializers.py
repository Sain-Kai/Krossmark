from rest_framework import serializers
from .models import Device, TriggerEvent, BurstCapture, AnalysisResult, Alert

class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = "__all__"
        read_only_fields = ("id", "api_key", "created_at", "last_seen")

class DeviceRegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = ("name", "serial_number", "device_type", "location_tag", "metadata")

class TriggerEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = TriggerEvent
        fields = "__all__"
        read_only_fields = ("id", "created_at")

class BurstCaptureSerializer(serializers.ModelSerializer):
    class Meta:
        model = BurstCapture
        fields = "__all__"
        read_only_fields = ("id", "status", "error_message", "created_at", "processed_at")

class AnalysisResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalysisResult
        fields = "__all__"
        read_only_fields = ("id", "created_at")

class AlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alert
        fields = "__all__"
        read_only_fields = ("id", "created_at")
