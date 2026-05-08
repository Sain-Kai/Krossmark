from django.utils import timezone
from ..models import BurstCapture, AnalysisResult, Alert
from .pipeline_adapter import DefenseAnalysisService, result_to_alert_severity

class AnalysisOrchestrator:
    def __init__(self):
        self.service = DefenseAnalysisService()

    def analyze_and_persist(self, burst: BurstCapture) -> AnalysisResult:
        burst.status = BurstCapture.Status.PROCESSING
        burst.error_message = ""
        burst.save(update_fields=["status", "error_message"])

        raw = self.service.analyze_burst(burst)

        result = AnalysisResult.objects.create(
            burst=burst,
            threat_level=int(raw.get("threat_level", 1) or 1),
            confidence=float(raw.get("confidence", 0.0) or 0.0),
            group_intent=str(raw.get("group_intent", "")),
            scene_intent=str(raw.get("scene_intent", "")),
            decision=str(raw.get("decision", "")),
            briefing=str(raw.get("briefing", "")),
            audit=raw.get("audit", {}),
            actors=raw.get("actors", []),
            video_context=raw.get("video_context", {}),
            raw_output=raw,
        )

        burst.status = BurstCapture.Status.DONE
        burst.processed_at = timezone.now()
        burst.save(update_fields=["status", "processed_at"])

        if result.threat_level >= 3:
            severity = result_to_alert_severity(result.threat_level)
            Alert.objects.create(
                analysis_result=result,
                severity=severity,
                title=f"Threat level {result.threat_level} detected",
                message=result.briefing or "Threat detected by analysis pipeline.",
            )

        return result
