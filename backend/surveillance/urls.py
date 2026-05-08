from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DeviceViewSet,
    TriggerEventViewSet,
    BurstCaptureViewSet,
    AnalysisResultViewSet,
    AlertViewSet,
    IngestAndAnalyzeView,
    ESP32TriggerView,
)

router = DefaultRouter()
router.register(r"devices",  DeviceViewSet,         basename="devices")
router.register(r"triggers", TriggerEventViewSet,   basename="triggers")
router.register(r"bursts",   BurstCaptureViewSet,   basename="bursts")
router.register(r"results",  AnalysisResultViewSet, basename="results")
router.register(r"alerts",   AlertViewSet,          basename="alerts")

urlpatterns = [
    path("", include(router.urls)),
    path("ingest/",          IngestAndAnalyzeView.as_view(), name="ingest"),
    path("esp32/trigger/",   ESP32TriggerView.as_view(),     name="esp32-trigger"),
]