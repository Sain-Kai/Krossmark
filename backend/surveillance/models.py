import uuid
from django.db import models

class Device(models.Model):
    class DeviceType(models.TextChoices):
        LEAF = "leaf", "Leaf Node"
        RELAY = "relay", "Relay Node"
        PI = "pi", "Raspberry Pi"
        COMMAND_CENTER = "command_center", "Command Center"
        SENSOR = "sensor", "Sensor Unit"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120)
    serial_number = models.CharField(max_length=120, unique=True)
    device_type = models.CharField(max_length=32, choices=DeviceType.choices)
    api_key = models.CharField(max_length=128, unique=True, editable=False)
    location_tag = models.CharField(max_length=120, blank=True, default="")
    is_active = models.BooleanField(default=True)
    last_seen = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.api_key:
            self.api_key = uuid.uuid4().hex + uuid.uuid4().hex[:16]
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.device_type})"

class TriggerEvent(models.Model):
    class SourceLevel(models.TextChoices):
        LEAF = "leaf", "Leaf"
        INTERMEDIATE = "intermediate", "Intermediate"
        PI = "pi", "Pi"
        COMMAND = "command", "Command"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="triggers")
    source_level = models.CharField(max_length=24, choices=SourceLevel.choices, default=SourceLevel.LEAF)
    pir_triggered = models.BooleanField(default=False)
    mic_triggered = models.BooleanField(default=False)
    confidence = models.FloatField(default=0.0)
    sensor_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Trigger {self.id} from {self.device_id}"

class BurstCapture(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        DONE = "done", "Done"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="bursts")
    trigger = models.ForeignKey(TriggerEvent, on_delete=models.SET_NULL, null=True, blank=True, related_name="bursts")
    video_file = models.FileField(upload_to="bursts/videos/", null=True, blank=True)
    audio_file = models.FileField(upload_to="bursts/audio/", null=True, blank=True)
    frame_count = models.PositiveIntegerField(default=0)
    audio_sample_rate = models.PositiveIntegerField(default=48000)
    metadata = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Burst {self.id} ({self.status})"

class AnalysisResult(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    burst = models.OneToOneField(BurstCapture, on_delete=models.CASCADE, related_name="result")
    threat_level = models.PositiveSmallIntegerField(default=1)
    confidence = models.FloatField(default=0.0)
    group_intent = models.CharField(max_length=64, blank=True, default="")
    scene_intent = models.CharField(max_length=64, blank=True, default="")
    decision = models.CharField(max_length=64, blank=True, default="")
    briefing = models.TextField(blank=True, default="")
    audit = models.JSONField(default=dict, blank=True)
    actors = models.JSONField(default=list, blank=True)
    video_context = models.JSONField(default=dict, blank=True)
    raw_output = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Result {self.id} threat={self.threat_level}"

class Alert(models.Model):
    class Severity(models.TextChoices):
        INFO = "info", "Info"
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    analysis_result = models.ForeignKey(AnalysisResult, on_delete=models.CASCADE, related_name="alerts")
    severity = models.CharField(max_length=16, choices=Severity.choices, default=Severity.MEDIUM)
    title = models.CharField(max_length=140)
    message = models.TextField()
    acknowledged = models.BooleanField(default=False)
    ack_by = models.CharField(max_length=120, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.severity.upper()} alert: {self.title}"
