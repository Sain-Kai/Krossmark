# Krossmark Django Backend

REST backend for the multi-layer border surveillance stack.

## What it covers
- Device registration for leaf / relay / pi / command-center nodes
- Trigger ingestion from ESP32 nodes
- Burst upload for 3-second video/audio captures
- Analysis result storage
- Threat / alert records for the dashboard
- Adapter layer for your existing Python perception pipeline

## Main endpoints
- `POST /api/v1/devices/register/`
- `POST /api/v1/triggers/`
- `POST /api/v1/bursts/`
- `POST /api/v1/bursts/<uuid>/analyze/`
- `POST /api/v1/esp32/trigger/`  ← launches `test.py` in the background
- `GET /api/v1/results/latest/`
- `GET /api/v1/alerts/`
- `GET /api/health/`

## Notes
The service is designed to integrate with your existing `vision.core.pipeline.defense_ai_pipeline.DefenseAIPipeline`.
If that import is not available yet, it falls back to a safe heuristic analyzer so the backend still works.

## Trigger flow
The Raspberry Pi relay only needs to POST to `POST /api/v1/esp32/trigger/`. The backend will start `test.py` in the background and immediately return `202 Accepted`.

Set `KROSSMARK_TEST_SCRIPT` if `test.py` lives somewhere else.
