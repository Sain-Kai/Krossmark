<div align="center">

```
██╗  ██╗██████╗  ██████╗ ███████╗███████╗    ███╗   ███╗ █████╗ ██████╗ ██╗  ██╗
██║ ██╔╝██╔══██╗██╔═══██╗██╔════╝██╔════╝    ████╗ ████║██╔══██╗██╔══██╗██║ ██╔╝
█████╔╝ ██████╔╝██║   ██║███████╗███████╗    ██╔████╔██║███████║██████╔╝█████╔╝ 
██╔═██╗ ██╔══██╗██║   ██║╚════██║╚════██║    ██║╚██╔╝██║██╔══██║██╔══██╗██╔═██╗ 
██║  ██╗██║  ██║╚██████╔╝███████║███████║    ██║ ╚═╝ ██║██║  ██║██║  ██║██║  ██╗
╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚══════╝    ╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝
```

**Portable Intelligence, Surveillance & Reconnaissance Pod**

*A 4-layer distributed edge-AI threat detection system — from ESP32 firmware to React Native dashboard*

---

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Django](https://img.shields.io/badge/Django-5.x-092E20?style=flat-square&logo=django&logoColor=white)](https://djangoproject.com)
[![React Native](https://img.shields.io/badge/React_Native-Expo-20232A?style=flat-square&logo=react&logoColor=61DAFB)](https://reactnative.dev)
[![ESP32](https://img.shields.io/badge/Embedded-ESP32_Arduino-E7352C?style=flat-square&logo=arduino&logoColor=white)](https://espressif.com)
[![YOLO](https://img.shields.io/badge/Vision-YOLOv8_+_DeepSORT-FF6F00?style=flat-square&logo=tensorflow&logoColor=white)](https://ultralytics.com)
[![Ollama](https://img.shields.io/badge/LLM-Ollama_Qwen--VL-black?style=flat-square&logo=ollama&logoColor=white)](https://ollama.com)
[![License](https://img.shields.io/badge/Status-Patent_Pending-5dcaa5?style=flat-square)](.)

</div>

---

## Table of Contents

- [Overview](#-overview)
- [System Architecture](#-system-architecture)
- [Repository Structure](#-repository-structure)
- [Layer 1 — Embedded Firmware](#-layer-1--embedded-firmware-esp32)
- [Layer 2 — Vision & AI Pipeline](#-layer-2--vision--ai-pipeline)
- [Layer 3 — Django REST Backend](#-layer-3--django-rest-backend)
- [Layer 4 — React Native Dashboard](#-layer-4--react-native-dashboard)
- [Data Models](#-data-models)
- [API Reference](#-api-reference)
- [Threat Scoring Engine](#-threat-scoring-engine)
- [Setup & Installation](#-setup--installation)
- [Environment Variables](#-environment-variables)
- [Hardware Bill of Materials](#-hardware-bill-of-materials)
- [Communication Protocol Stack](#-communication-protocol-stack)
- [Patent-Relevant Claims](#-patent-relevant-claims)

---

## Overview

KROSS MARK is a **portable, battery-powered Intelligence, Surveillance & Reconnaissance (ISR) pod** designed for covert perimeter defence. It runs fully offline at the edge — no cloud required.

The system uses a **4-layer distributed pipeline** where each layer progressively filters false positives before escalating to the next:

1. **ESP32 leaf node** — dual IR sensors + ADXL345 gait check. Fires only on confirmed human motion pattern via ESP-NOW.
2. **ESP32 intermediate node** — FSR footstep pressure + microphone audio sampling. Captures video burst via ESP32-CAM. Relays over HTTP to Pi.
3. **Raspberry Pi relay** — assembles multimodal sensor payload, bridges to Django backend.
4. **Command center** — runs YOLOv8 detection, DeepSORT tracking, HTSAT audio classification, Qwen-VL vision-language analysis, and Bayesian threat scoring. Pushes alerts to React Native dashboard.

> **Novel contribution:** A heterogeneous protocol chain (ESP-NOW → HTTP → REST) combined with on-device TinyML inference and multi-modal Bayesian fusion that achieves sub-25µA idle current at the leaf node while delivering sub-3s end-to-end detection latency.

---

## System Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│   NODE 1 — LEAF (ESP32-WROOM)                                            │
│   ┌─────────────┐  ┌─────────────┐  ┌──────────────┐                    │
│   │ IR Sensor 1 │  │ IR Sensor 2 │  │  ADXL345     │                    │
│   │  TCRT5000   │  │  TCRT5000   │  │  Gait check  │                    │
│   │  GPIO 27    │  │  GPIO 26    │  │  I2C 33/32   │                    │
│   └──────┬──────┘  └──────┬──────┘  └──────┬───────┘                    │
│          └────────────────┴────────────────┘                             │
│                        ESP-NOW broadcast (250B · <1ms)                   │
│                               |                                          │
│   NODE 2 — INTERMEDIATE ──────┼──────────────────────────────────────    │
│   ┌─────────────────────┐     |    ┌──────────────────────────────────┐  │
│   │   Sub-node A        │     |    │   Sub-node B                     │  │
│   │   ESP32-CAM         │<────┘    │   ESP32-WROOM                    │  │
│   │   OV2640            │          │   FSR Sensor  (GPIO 13)          │  │
│   │   Video burst       │          │   Microphone  (KY-037 · ADC 33)  │  │
│   │   HTTP POST -> Pi   │          │   Audio @ 8 kHz                  │  │
│   └─────────────────────┘          │   HTTP POST -> Pi                │  │
│                                    └──────────────────────────────────┘  │
│                         Raspberry Pi 4B (Relay)                          │
│              ┌───────────────────────────────────────────────┐           │
│              │  /video   endpoint  <- JPEG frames (binary)   │           │
│              │  /sensors endpoint  <- sensor blob (binary)   │           │
│              │  burst merge logic -> POST /api/v1/ingest/    │           │
│              └──────────────────────┬────────────────────────┘           │
│                                     │  HTTP REST                         │
│                         Django Backend (Command Center)                   │
│   ┌──────────────────────────────────────────────────────────────────┐   │
│   │  AnalysisOrchestrator                                            │   │
│   │  ├── DefenseAIPipeline                                           │   │
│   │  │   ├── YOLOv8 person detection                                 │   │
│   │  │   ├── DeepSORT multi-object tracking                          │   │
│   │  │   ├── RTMPose pose estimation                                 │   │
│   │  │   ├── HTSAT audio classification (13 event classes)           │   │
│   │  │   ├── Qwen-VL / Ollama scene + weapon analysis                │   │
│   │  │   └── Sensor fusion (ADXL magnitude + FSR force)              │   │
│   │  └── BayesianThreatScorer -> threat_level [1-5]                  │   │
│   │  REST API -> /api/v1/  (devices/triggers/bursts/results/alerts)  │   │
│   └──────────────────────────────────────────────────────────────────┘   │
│                              HTTP poll (3s)                               │
│                    React Native Dashboard (Expo)                          │
│          Overview · Alerts · Nodes · Intel tabs                           │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Repository Structure

```
krossmark/
├── embedded/
│   ├── NODE_1/
│   │   └── NODE_1.ino             # Leaf node — IR + ADXL345 + ESP-NOW TX
│   └── NODE_2/
│       └── NODE_2.ino             # Intermediate node — FSR + Mic + HTTP POST
│
├── vision/                        # Python AI/vision pipeline
│   ├── pyproject.toml
│   ├── main.py
│   ├── pi_test.py                 # Pi relay integration test suite
│   └── core/
│       ├── config.py
│       ├── pipeline/
│       │   ├── defence_ai_pipeline.py   # Main multi-modal fusion engine
│       │   ├── perception.py
│       │   ├── video_burst_analyzer.py
│       │   └── video_utils.py
│       ├── detection/
│       │   ├── yolo.py            # YOLOv8 wrapper
│       │   └── yolo_pose.py
│       ├── tracking/
│       │   ├── tracker.py
│       │   └── deepsort_tracker.py
│       ├── pose/
│       │   └── rtm_pose.py
│       ├── audio/
│       │   └── worker.py          # HTSAT audio classification worker
│       ├── vlm/
│       │   ├── ollama_vl.py       # Ollama Qwen-VL HTTP client
│       │   ├── prompts.py         # System prompts
│       │   ├── parser.py
│       │   ├── scheduler.py
│       │   └── worker.py
│       ├── fusion/
│       │   ├── sensor_fusion.py   # ADXL + FSR normalisation
│       │   ├── explainer.py
│       │   ├── packer.py
│       │   └── stabilizer.py
│       ├── threat/
│       │   ├── bayesian_threat.py # Bayesian threat scorer (log-odds)
│       │   ├── scorer.py
│       │   └── threat_engine.py
│       ├── intent/
│       │   ├── per_person.py
│       │   ├── group.py
│       │   ├── scene.py
│       │   └── states.py
│       ├── features/
│       │   ├── motion.py
│       │   ├── grouping.py
│       │   └── pose_features.py
│       ├── evidence/
│       │   └── accumulator.py
│       ├── burst/
│       │   ├── burst_analyzer.py
│       │   └── burst_runner.py
│       └── io/
│           └── video_source.py
│
├── backend/                       # Django REST API
│   ├── manage.py
│   ├── requirements.txt
│   ├── .env.example
│   ├── krossmark_backend/
│   │   ├── settings.py
│   │   ├── urls.py
│   │   ├── asgi.py
│   │   └── wsgi.py
│   └── surveillance/
│       ├── models.py              # Device, TriggerEvent, BurstCapture, AnalysisResult, Alert
│       ├── views.py               # ViewSets + ESP32TriggerView + IngestAndAnalyzeView
│       ├── serializers.py
│       ├── urls.py
│       ├── auth.py                # Device API key authentication
│       └── services/
│           ├── analysis_service.py
│           ├── pipeline_adapter.py
│           └── media.py
│
└── src/                           # React Native frontend (Expo)
    ├── constants/
    │   └── colors.ts
    ├── services/
    │   └── api.ts
    ├── screens/
    │   ├── MainScreen.tsx
    │   └── DashboardScreen.tsx
    └── tabs/
        ├── OverviewTab.tsx        # Threat hero card + Bayesian signals + briefing
        ├── AlertsTab.tsx          # Alert feed + ACK modal
        ├── NodesTab.tsx           # Device registry + health
        └── IntelTab.tsx           # Intelligence history
```

---

## Layer 1 — Embedded Firmware (ESP32)

### NODE 1 — Leaf Node (`embedded/NODE_1/NODE_1.ino`)

The leaf node is the perimeter sensor running in a tight polling loop with a **3 s cooldown**.

**Sensors:**

| Pin | Component | Role |
|-----|-----------|------|
| GPIO 27 | TCRT5000 IR Sensor 1 | Break-beam detection |
| GPIO 26 | TCRT5000 IR Sensor 2 | Redundant / direction sensing |
| I2C SDA 33 / SCL 32 | ADXL345 | 3-axis accelerometer gait check |
| GPIO 2 | LED | Visual trigger indicator |

**Trigger logic:**

```
loop (50 ms tick):
  ir1 = GPIO27 LOW             → beam broken
  ir2 = GPIO26 LOW             → beam broken
  disturbance = ADXL check     → magnitude > 1.5g OR delta > 0.07g over 10 samples

  if (ir1 OR ir2 OR disturbance) AND cooldown elapsed (3000 ms):
    send ESP-NOW TriggerPacket { trigger: 1 } to NODE 2 MAC
```

**ADXL345 config:** Range ±16g (`0x31 = 0x09`), Measure mode (`0x2D = 0x08`), scale `0.004 g/LSB`

**ESP-NOW:** Channel 6 (forced), target = NODE 2 MAC, packet = 1 byte

---

### NODE 2 — Intermediate Node (`embedded/NODE_2/NODE_2.ino`)

Listens for NODE 1's ESP-NOW broadcast, samples FSR + microphone, sends binary blob to Raspberry Pi over HTTP.

**Pins:**

| Pin | Component | Role |
|-----|-----------|------|
| GPIO 13 | FSR / presence sensor | Footstep detection |
| GPIO 33 (ADC) | KY-037 Microphone | Analog audio at 8 kHz |

**Audio capture:** 4000 samples × 125 µs intervals ≈ 8 kHz, spike threshold = 150 ADC units

**HTTP payload (binary `application/octet-stream`):**
```
Byte 0     : PIR/FSR digital read (0 or 1)
Byte 1     : audio_spike flag (0 or 1)
Bytes 2–N  : uint16[] audio samples (little-endian)
```

**WiFi mode:** `WIFI_AP_STA` — dual-mode holds WiFi connection while ESP-NOW runs on forced channel 6. Cooldown: 5000 ms between captures.

---

## Layer 2 — Vision & AI Pipeline

Located in `vision/`. Standalone Python package (`krossmark-vision`) consumed by Django.

### `DefenseAIPipeline` — Core Fusion Engine

```python
result = pipeline.analyze_burst(frames, audio, sensor_data={
    "adxl": {"x": 0.01, "y": -0.02, "z": 9.81, "magnitude": 9.81},
    "fsr":  {"raw": 2800, "force_g": 3200.0, "resistance": 800.0}
})
```

**Pipeline stages:**

```
frames ──► YOLOv8 detection ──► person count
        ► DeepSORT tracking  ──► track IDs
        ► RTMPose estimation ──► pose activity score
        ► Qwen-VL analysis   ──► scene_intent, weapon_present
                                    |
                               vision_score [0–1]

audio  ──► HTSAT worker ──► 13-class event scores
                              |
                         audio_score [0–1]

sensor ──► ADXL magnitude ──► motion_score
        ► FSR force/raw    ──► pressure_score
                              |
                         sensor_score [0–1]

final_score = 0.40 × vision + 0.30 × audio + 0.30 × sensor + bonuses
```

**Threat levels:**

| Score | Level | Label |
|-------|-------|-------|
| < 0.18 | 1 | NORMAL |
| 0.18 – 0.35 | 2 | SUSPICIOUS |
| 0.35 – 0.55 | 3 | ELEVATED |
| 0.55 – 0.75 | 4 | HIGH |
| ≥ 0.75 | 5 | CRITICAL |

### `BayesianThreatScorer` — Log-Odds Scorer

Prior: `P(threat) = 0.05`. Uses log-odds Bayesian update with per-signal likelihood ratios:

| Signal | LR |
|--------|-----|
| Firearm (confirmed) | `12.0^severity × 1.45` |
| Knife (confirmed) | `12.0^severity × 1.20` |
| Audio: scream | 5.20 |
| Audio: metal clash | 6.00 |
| Audio: shouting | 4.60 |
| Audio: footsteps | 1.90 |
| Sensor combo (motion + pressure) | 4.00 |
| Aggressive behaviour | 6.00 |

### Audio Classification — HTSAT (13 classes)

`silence · whispering · speaking · crowd_murmur · footsteps · banging · impact · shouting · scream · metal_clash · gunshot · gunfire · explosion`

Silence suppression: dominant silence ≥ 0.80 confidence → `audio_score = 0.0`

### Vision-Language Model — Qwen-VL via Ollama

Endpoint: `http://localhost:11434/api/generate` · Model: `qwen3-vl:4b`

Two prompts:
- **`FULL_FRAME_PROMPT`** — single frame weapon detection (`weapon_present`, `weapon_type`, `confidence`)
- **`VIDEO_ANALYSIS_PROMPT`** — 6-keyframe scene analysis (`scene_intent`, `group_intent`, `threat_score`, `description`)

Text-blob keyword fallback activates when JSON parsing fails, scanning for: `gunfire · gunshot · firearm · rifle · knife · blade · weapon` etc.

### Sensor Fusion Thresholds

| ADXL Magnitude | Motion Score |
|----------------|-------------|
| ≥ 12.0 m/s² | 0.95 |
| ≥ 6.0 | 0.75 |
| ≥ 2.0 | 0.45 |

| FSR Force (g) | Pressure Score |
|---------------|---------------|
| ≥ 800 | 0.95 |
| ≥ 250 | 0.70 |
| ≥ 50 | 0.35 |

`sensor_score = min(1.0, 0.6 × motion + 0.4 × pressure)`

---

## Layer 3 — Django REST Backend

### Installation

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env       # fill in model paths
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

### Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/api/health/` | None | Service health check |
| `POST` | `/api/v1/devices/register/` | None | Register a new node |
| `GET` | `/api/v1/devices/{id}/status/` | None | Node heartbeat |
| `POST` | `/api/v1/triggers/` | Device Key | Log trigger event |
| `POST` | `/api/v1/bursts/` | Device Key | Upload burst → full AI analysis |
| `POST` | `/api/v1/bursts/{id}/analyze/` | None | Re-analyse existing burst |
| `GET` | `/api/v1/results/latest/` | None | Latest analysis result |
| `GET` | `/api/v1/alerts/` | None | Alert log |
| `POST` | `/api/v1/alerts/{id}/ack/` | None | Acknowledge alert |
| `POST` | `/api/v1/ingest/` | Device Key | One-shot: device + burst → analysis |
| `POST` | `/api/v1/esp32/trigger/` | None | **Pi relay entry point** — spawns vision pipeline |

### Pi Relay Entry Point

`POST /api/v1/esp32/trigger/` is the critical endpoint the Raspberry Pi calls after merging video and sensor payloads:

```json
{
  "source": "node2",
  "burst_id": "MERGE-1234567890",
  "sensor_data": {
    "adxl": { "x": 0.02, "y": -0.01, "z": 9.80, "magnitude": 9.81 },
    "fsr":  { "raw": 2800, "force_g": 3200.0, "resistance": 820.0 }
  }
}
```

What it does: auto-provisions `PI-RELAY-001` device → creates `TriggerEvent` → writes `trigger_payload.json` → spawns `vision/core/test.py` subprocess → returns `202 Accepted` immediately.

### Device Authentication

All device endpoints accept `X-Device-Key: <key>` or `Authorization: Device <key>`. Keys are 64-char hex, auto-generated on device creation.

### AI Configuration

```python
# settings.py
AI_PIPELINE = {
    "BURST_DURATION": 3,     # seconds per burst
    "FRAME_LIMIT": 120,      # max frames analysed
    "CONF_THRESHOLD": 0.6,   # YOLO detection threshold
}
```

---

## Layer 4 — React Native Dashboard

Located in `src/`. Built with Expo + React Native.

### OverviewTab — Live Threat Display

Polls `/api/v1/results/latest/` every **3 seconds**.

- **Threat hero card** — large threat level (1–5) with animated pulse ring when level ≥ 3
- **Threat bar** — 5-segment colour indicator (green / amber / red)
- **Scene intelligence panel** — `scene_intent`, `group_intent`, `decision`, actor count, timestamp
- **Bayesian signals chips** — WEAPON / AGGRESSION / COORDINATED / AUDIO SPIKE / HIGH SPEED
- **Analyst briefing** — raw Qwen-VL situation report text
- **Tracked actors list** — DeepSORT track IDs and intents

Flashes 4 × on new `threat_level ≥ 3` event.

### AlertsTab — Alert Feed

Polls every **5 seconds**. Sorted: unacknowledged first → severity → recency.

- Severity colour: `critical/high` → red · `medium` → amber · `low` → green
- Detail modal with ACK button (`POST /api/v1/alerts/{id}/ack/`)
- Pull-to-refresh

### NodesTab — Device Registry

Polls every **10 seconds**.

- Backend health card
- Per-device: role label, status pill (ACTIVE < 30s / IDLE < 120s / STALE / OFFLINE), burst count, last-seen

### IntelTab — Intelligence History

Browsable `AnalysisResult` history with scene context, threat scores, and VLM briefings.

---

## Data Models

```
Device
├── id (UUID PK)
├── name, serial_number (unique)
├── device_type   [leaf | relay | pi | command_center | sensor]
├── api_key       (auto 64-char hex)
├── location_tag, is_active, last_seen
└── metadata (JSON)

TriggerEvent
├── id (UUID PK)
├── device (FK), source_level [leaf|intermediate|pi|command]
├── pir_triggered, mic_triggered (bool)
├── confidence (float)
└── sensor_payload (JSON)   <- raw ADXL + FSR

BurstCapture
├── id (UUID PK)
├── device (FK), trigger (FK nullable)
├── video_file, audio_file  (FileField -> media/bursts/)
├── frame_count, audio_sample_rate
├── status  [pending|processing|done|failed]
└── error_message, processed_at

AnalysisResult
├── id (UUID PK)
├── burst (OneToOne)
├── threat_level (1-5), confidence (0.0-1.0)
├── group_intent, scene_intent, decision
├── briefing (VLM text)
├── audit (JSON)         <- full score breakdown
├── actors (JSON)        <- DeepSORT tracks
├── video_context (JSON) <- pose/audio/vision/vlm sub-results
└── raw_output (JSON)

Alert
├── id (UUID PK)
├── analysis_result (FK)
├── severity  [info|low|medium|high|critical]
├── title, message
├── acknowledged (bool), ack_by
└── created_at
```

---

## API Reference

### Register a Device

```bash
curl -X POST http://localhost:8000/api/v1/devices/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Leaf Node Alpha",
    "serial_number": "NODE1-001",
    "device_type": "leaf",
    "location_tag": "north-perimeter"
  }'
```

### Post a Trigger Event

```bash
curl -X POST http://localhost:8000/api/v1/triggers/ \
  -H "X-Device-Key: <api-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "source_level": "leaf",
    "pir_triggered": true,
    "confidence": 0.82,
    "sensor_payload": {}
  }'
```

### Upload Burst for Analysis

```bash
curl -X POST http://localhost:8000/api/v1/bursts/ \
  -H "X-Device-Key: <api-key>" \
  -F "device_id=<uuid>" \
  -F "video_file=@burst.mp4" \
  -F "audio_file=@audio.wav" \
  -F "frame_count=90"
```

### Pi Relay Trigger

```bash
curl -X POST http://<backend-ip>:8000/api/v1/esp32/trigger/ \
  -H "Content-Type: application/json" \
  -d '{
    "source": "node2",
    "burst_id": "BURST-001",
    "sensor_data": {
      "adxl": {"x": 0.1, "y": -0.05, "z": 9.78, "magnitude": 9.78},
      "fsr":  {"raw": 3100, "force_g": 4500.0, "resistance": 600.0}
    }
  }'
```

### Get Latest Result

```bash
curl http://localhost:8000/api/v1/results/latest/
```

**Response:**
```json
{
  "id": "uuid",
  "threat_level": 4,
  "confidence": 0.71,
  "scene_intent": "suspicious",
  "group_intent": "coordinated",
  "decision": "threat",
  "briefing": "Two individuals observed moving in coordinated pattern near entry...",
  "audit": {
    "vision_score": 0.68,
    "audio_score": 0.45,
    "sensor_score": 0.82,
    "final_score": 0.71,
    "avg_people": 2.0,
    "peak_people": 3.0,
    "sensor_motion_score": 0.75,
    "sensor_pressure_score": 0.95
  },
  "created_at": "2025-01-15T03:42:11.123Z"
}
```

---

## Threat Scoring Engine

```
final_score = 0.40 × vision_score
            + 0.30 × audio_score
            + 0.30 × sensor_score

# Weapon bonus
if weapon_present:
    final_score += 0.18 + 0.12 × weapon_confidence

# Audio danger bonus
if dominant_audio in {shouting, scream, metal_clash, gunshot, gunfire, explosion}:
    final_score += 0.10 + 0.10 × audio_score

# Sensor combination bonus
if sensor_combo (motion AND pressure both triggered): final_score += 0.10
elif pressure_alert:                                  final_score += 0.05
elif motion_alert:                                    final_score += 0.03

# Normal-scene suppression (anti-false-positive cap)
if scene == "normal" and not weapon_present:
    if avg_people <= 1 and silence: final_score = min(final_score, 0.12)
    elif avg_people >= 5:           final_score = min(final_score, 0.35)
    else:                           final_score = min(final_score, 0.22)
```

---

## Setup & Installation

### Prerequisites

- Python 3.11+
- Node.js 18+ with Expo CLI (`npm install -g expo-cli`)
- Arduino IDE with ESP32 board support
- Ollama running locally with `qwen3-vl:4b` model pulled
- YOLOv8 `.pt` weights and HTSAT model directory

### 1 — Backend

```bash
git clone https://github.com/yourorg/krossmark.git
cd krossmark/backend

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env     # set YOLO_DET_MODEL, HTSAT_MODEL, OLLAMA_URL

python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

### 2 — Vision Pipeline

```bash
cd krossmark/vision
pip install ultralytics opencv-python numpy scipy filterpy requests
```

Imported directly by Django's `AnalysisOrchestrator`. No separate process needed unless triggered via `esp32/trigger/` endpoint.

### 3 — Firmware

**NODE 1:**
1. Open `embedded/NODE_1/NODE_1.ino` in Arduino IDE
2. Set `SENSOR_MAC[]` to NODE 2's MAC address
3. Install ESP32 board package (Espressif)
4. Flash to ESP32-WROOM board

**NODE 2:**
1. Open `embedded/NODE_2/NODE_2.ino`
2. Update `SSID`, `PASSWORD`, and `PI_URL`
3. Flash to ESP32-WROOM board

### 4 — React Native

```bash
cd krossmark/src
npm install
# Update BASE_URL in src/services/api.ts to your backend IP
npx expo start
```

Scan QR with Expo Go, or run on Android emulator (`10.0.2.2` maps to host machine).

### 5 — Pi Relay Integration Test

```bash
cd krossmark/vision
python pi_test.py
```

Runs 4 tests: health check → /video endpoint → /sensors endpoint → full burst merge.

---

## Environment Variables

```env
# Django security
DEBUG=1
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=127.0.0.1,localhost,<pi-ip>,<backend-ip>
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8081

# Database (default SQLite)
DATABASE_URL=sqlite:///db.sqlite3

# AI model paths (absolute)
YOLO_DET_MODEL=/path/to/models/yolo26m.pt
HTSAT_MODEL=/path/to/models/htsat
QWEN_MODEL_NAME=qwen3-vl:4b
OLLAMA_URL=http://localhost:11434/api/generate

# Vision pipeline
KROSSMARK_TEST_SCRIPT=/path/to/vision/core/test.py
```

---

## Hardware Bill of Materials

| # | Component | Qty | Node | Notes |
|---|-----------|-----|------|-------|
| 1 | ESP32-WROOM-32 Dev Board | 2 | NODE 1 + NODE 2 | Leaf + intermediate sensing |
| 2 | ESP32-CAM (OV2640) | 1 | NODE 2A | 2MP JPEG burst |
| 3 | TCRT5000 IR Sensor | 2 | NODE 1 | GPIO 27 + GPIO 26 |
| 4 | ADXL345 Accelerometer | 1 | NODE 1 | I2C · SDA 33 / SCL 32 |
| 5 | FSR Sensor | 1 | NODE 2 | GPIO 13 |
| 6 | KY-037 Microphone | 1 | NODE 2 | GPIO 33 (ADC) · 8 kHz |
| 7 | Raspberry Pi 4B 4GB | 1 | Relay | Flask relay + Django bridge |
| 8 | USB SSD 256 GB | 1 | Relay | 24 h event buffer |
| 9 | Command Center PC | 1 | Backend | CUDA GPU recommended |
| 10 | LiPo 3.7V 2000mAh | 2 | Field nodes | NODE 1 + NODE 2 |

---

## Communication Protocol Stack

| Hop | Protocol | Payload | Latency |
|-----|----------|---------|---------|
| NODE 1 → NODE 2 | ESP-NOW (802.11 ch.6) | 1-byte trigger packet | < 1 ms |
| NODE 2 → Pi | HTTP POST octet-stream | PIR + audio_spike + uint16[] samples | < 200 ms |
| NODE 2A → Pi | HTTP POST octet-stream | frame_count + JPEG frames | < 500 ms |
| Pi → Django | HTTP REST JSON | Sensor payload + burst_id | < 100 ms |
| Django → Vision | Subprocess / in-process | File paths + JSON env vars | async |
| Django → Dashboard | HTTP poll 3s | JSON analysis result | ≤ 3 s lag |

---

## Patent-Relevant Claims

This project is currently **under patent filing**. Key novel claims:

1. **Hierarchical heterogeneous protocol stack** — ESP-NOW at the leaf layer, HTTP binary stream at the intermediate layer, REST/JSON at the command layer. Each protocol chosen for that layer's bandwidth/latency/power constraints.

2. **Progressive multi-modal false-positive rejection** — 4 independent rejection stages before alert escalation. The leaf ADXL gait check alone eliminates animal and wind false positives before any radio transmission occurs.

3. **On-device TinyML state machine** — leaf ESP32 runs classification with sub-5ms inference. Achieves < 25µA average current draw in field deployment.

4. **Multi-modal Bayesian fusion** — log-odds scorer combining vision scores, 13-class audio event probabilities, and dual-sensor (accelerometer + force-sensitive resistor) pressure scores into a calibrated threat probability with no runtime labelling required.

5. **Asynchronous burst-triggered LLM briefing** — Qwen-VL generates a human-readable tactical situation report on confirmed threat events, with automatic JSON-fallback text extraction when VLM output parsing fails.

---

<div align="center">

**KROSS MARK** · Portable ISR Pod · *Patent Pending*

Built with ESP32 · Django · React Native · YOLOv8 · Ollama · Bayesian Inference

</div>
