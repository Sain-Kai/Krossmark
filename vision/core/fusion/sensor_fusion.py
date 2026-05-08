from __future__ import annotations

from typing import Any, Dict


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def build_sensor_context(sensor_data: Dict[str, Any] | None) -> Dict[str, Any]:
    sensor_data = sensor_data or {}
    adxl = sensor_data.get("adxl") or {}
    fsr = sensor_data.get("fsr") or {}

    adxl_mag = abs(_to_float(adxl.get("magnitude", 0.0)))
    fsr_force = max(0.0, _to_float(fsr.get("force_g", 0.0)))
    fsr_raw = max(0, _to_int(fsr.get("raw", 0)))

    motion_score = 0.0
    if adxl_mag >= 12.0:
        motion_score = 0.95
    elif adxl_mag >= 6.0:
        motion_score = 0.75
    elif adxl_mag >= 2.0:
        motion_score = 0.45
    elif adxl_mag > 0.0:
        motion_score = 0.2

    pressure_score = 0.0
    if fsr_force >= 800.0:
        pressure_score = 0.95
    elif fsr_force >= 250.0:
        pressure_score = 0.7
    elif fsr_force >= 50.0:
        pressure_score = 0.35
    elif fsr_raw > 0:
        pressure_score = 0.1

    sensor_score = min(1.0, (0.6 * motion_score) + (0.4 * pressure_score))

    return {
        "raw": {
            "adxl": adxl,
            "fsr": fsr,
        },
        "normalized": {
            "adxl": {
                "x": _to_float(adxl.get("x", 0.0)),
                "y": _to_float(adxl.get("y", 0.0)),
                "z": _to_float(adxl.get("z", 0.0)),
                "magnitude": adxl_mag,
            },
            "fsr": {
                "raw": fsr_raw,
                "resistance": _to_float(fsr.get("resistance", 0.0)),
                "force_g": fsr_force,
            },
        },
        "scores": {
            "motion": motion_score,
            "pressure": pressure_score,
            "sensor": sensor_score,
        },
    }
