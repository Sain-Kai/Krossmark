# test_pi_relay.py — run on your LAPTOP
# Tests the Pi relay endpoints independently

import requests
import numpy as np
import struct
import cv2
import time

PI_URL = "http://172.25.171.232:5000"

def test_pi_health():
    print("
── Test 1: Pi health check ───────────────")
    try:
        r = requests.get(f"{PI_URL}/health", timeout=5)
        print(f"Status: {r.status_code}")
        print(f"Response: {r.json()}")
        print("PASS" if r.status_code == 200 else "FAIL")
    except Exception as e:
        print(f"FAIL — Pi not reachable: {e}")
        print("  Check: is pi_relay.py running on the Pi?")
        print("  Check: are both on same WiFi network?")

def make_fake_video_payload(num_frames=10):
    """Build binary payload matching what Unit B sends."""
    frame_jpegs = []
    for i in range(num_frames):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        # Moving box so motion check passes
        x = 100 + i * 20
        cv2.rectangle(frame, (x, 100), (x+80, 380), (0, 180, 80), -1)
        _, buf = cv2.imencode('.jpg', frame,
                              [cv2.IMWRITE_JPEG_QUALITY, 85])
        frame_jpegs.append(buf.tobytes())

    # [4B frame_count][for each: 4B size + JPEG]
    payload = struct.pack('<I', num_frames)
    for jpg in frame_jpegs:
        payload += struct.pack('<I', len(jpg)) + jpg
    return payload


def make_fake_sensor_payload(num_audio=24000):
    """Build binary payload matching what Unit A sends."""
    # [1B fsr][1B audio_spike][uint16 * N]
    audio = np.random.randint(1800, 2300, num_audio, dtype=np.uint16)
    payload  = bytes([1, 1])  # FSR=1, AudioSpike=1
    payload += audio.tobytes()
    return payload


def test_pi_video_endpoint():
    print("
── Test 2: Pi /video endpoint ────────────")
    burst_id = f"TEST-{int(time.time())}"
    payload  = make_fake_video_payload(num_frames=10)
    print(f"  Burst ID : {burst_id}")
    print(f"  Payload  : {len(payload)} bytes  ({10} frames)")
    try:
        r = requests.post(
            f"{PI_URL}/video",
            data=payload,
            headers={
                "Content-Type":  "application/octet-stream",
                "X-Burst-ID":    burst_id,
                "X-Frame-Count": "10",
            },
            timeout=15,
        )
        print(f"  Status   : {r.status_code}")
        print(f"  Response : {r.json()}")
        print("PASS" if r.status_code == 200 else "FAIL")
        return burst_id
    except Exception as e:
        print(f"FAIL: {e}")
        return None


def test_pi_sensors_endpoint(burst_id=None):
    print("
── Test 3: Pi /sensors endpoint ──────────")
    if burst_id is None:
        burst_id = f"TEST-{int(time.time())}"
    payload = make_fake_sensor_payload()
    print(f"  Burst ID : {burst_id}")
    print(f"  Payload  : {len(payload)} bytes  (3s audio)")
    try:
        r = requests.post(
            f"{PI_URL}/sensors",
            data=payload,
            headers={
                "Content-Type":  "application/octet-stream",
                "X-Burst-ID":    burst_id,
                "X-Audio-Rate":  "8000",
                "X-FSR":         "1",
                "X-Audio-Spike": "1",
            },
            timeout=15,
        )
        print(f"  Status   : {r.status_code}")
        print(f"  Response : {r.json()}")
        print("PASS" if r.status_code == 200 else "FAIL")
    except Exception as e:
        print(f"FAIL: {e}")


def test_full_merge():
    """
    Send video and sensors with the SAME burst_id.
    Pi should merge them and forward to Django.
    Watch the Pi terminal for merge + Django response.
    """
    print("
── Test 4: Full merge (video + sensors) ──")
    burst_id = f"MERGE-{int(time.time())}"
    print(f"  Burst ID : {burst_id}")
    print("  Sending video first, then sensors 1s later...")

    video_payload  = make_fake_video_payload(num_frames=15)
    sensor_payload = make_fake_sensor_payload()

    try:
        # Send video
        r1 = requests.post(
            f"{PI_URL}/video",
            data=video_payload,
            headers={
                "Content-Type":  "application/octet-stream",
                "X-Burst-ID":    burst_id,
                "X-Frame-Count": "15",
            },
            timeout=15,
        )
        print(f"  Video POST   : {r1.status_code}")

        time.sleep(1)  # simulate slight timing difference

        # Send sensors
        r2 = requests.post(
            f"{PI_URL}/sensors",
            data=sensor_payload,
            headers={
                "Content-Type":  "application/octet-stream",
                "X-Burst-ID":    burst_id,
                "X-Audio-Rate":  "8000",
                "X-FSR": "1", "X-Audio-Spike": "1",
            },
            timeout=15,
        )
        print(f"  Sensors POST : {r2.status_code}")
        print()
        print("  Watch the Pi terminal — you should see:")
        print("  [Pi] Both payloads ready for burst MERGE-xxx")
        print("  [Pi] Motion score: xx.xx")
        print("  [Pi] Django response: 201")
        print()
        print("  Watch Django terminal — you should see:")
        print("  POST /api/v1/ingest/ HTTP/1.1  201")
        print()
        print("PASS (check Pi + Django terminals for merge confirmation)")

    except Exception as e:
        print(f"FAIL: {e}")

if __name__ == "__main__":
    print("=" * 50)
    print(" Krossmark Pi Relay Test Suite")
    print("=" * 50)
    print(f"Pi target: {PI_URL}")
    print()

    test_pi_health()
    bid = test_pi_video_endpoint()   # sends video only — Pi stores it
    time.sleep(2)
    test_pi_sensors_endpoint(bid)    # sends sensors with same ID — Pi merges
    time.sleep(2)
    test_full_merge()                # sends both together — full flow

    print("
" + "=" * 50)
    print(" Pi relay tests complete.")
    print("=" * 50)
