from __future__ import annotations
from pathlib import Path
from typing import List, Optional
import wave

import cv2
import numpy as np

def load_frames_from_video(video_path: str, max_frames: int = 6) -> List[np.ndarray]:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return []

    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if frame_count <= 0:
        frame_count = max_frames

    picks = set(np.linspace(0, max(0, frame_count - 1), num=min(max_frames, frame_count)).astype(int).tolist())
    frames = []
    idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if idx in picks:
            frames.append(frame)
        idx += 1
    cap.release()
    return frames

def load_audio_from_wav(audio_path: str) -> Optional[np.ndarray]:
    path = Path(audio_path)
    if not path.exists():
        return None

    try:
        with wave.open(str(path), "rb") as wf:
            n_channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            n_frames = wf.getnframes()
            raw = wf.readframes(n_frames)
            if sampwidth == 2:
                dtype = np.int16
            elif sampwidth == 4:
                dtype = np.int32
            else:
                dtype = np.int16
            audio = np.frombuffer(raw, dtype=dtype).astype(np.float32)
            if n_channels > 1:
                audio = audio.reshape(-1, n_channels).mean(axis=1)
            scale = np.max(np.abs(audio)) or 1.0
            return audio / scale
    except Exception:
        return None
