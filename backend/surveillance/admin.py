from django.contrib import admin
from .models import Device, TriggerEvent, BurstCapture, AnalysisResult, Alert

@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ("name", "device_type", "is_active", "last_seen", "created_at")
    search_fields = ("name", "serial_number", "api_key")
    list_filter = ("device_type", "is_active")

@admin.register(TriggerEvent)
class TriggerEventAdmin(admin.ModelAdmin):
    list_display = ("id", "device", "source_level", "pir_triggered", "mic_triggered", "confidence", "created_at")
    list_filter = ("source_level", "pir_triggered", "mic_triggered")
    search_fields = ("device__name", "device__serial_number")

@admin.register(BurstCapture)
class BurstCaptureAdmin(admin.ModelAdmin):
    list_display = ("id", "device", "status", "frame_count", "created_at", "processed_at")
    list_filter = ("status",)
    search_fields = ("device__name",)

@admin.register(AnalysisResult)
class AnalysisResultAdmin(admin.ModelAdmin):
    list_display = ("burst", "threat_level", "confidence", "group_intent", "scene_intent", "decision", "created_at")
    list_filter = ("threat_level", "group_intent", "scene_intent", "decision")

@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ("id", "analysis_result", "severity", "acknowledged", "created_at")
    list_filter = ("severity", "acknowledged")
