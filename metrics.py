"""Core data-cleaning and running-metric helpers for RunBiomechanics."""

from __future__ import annotations

import pandas as pd

REQUIRED_COLUMNS = ("date", "distance_km", "duration_min")
NUMERIC_COLUMNS = (
    "distance_km",
    "duration_min",
    "avg_hr_bpm",
    "cadence_spm",
    "elevation_m",
)
OPTIONAL_COLUMNS = ("avg_hr_bpm", "cadence_spm", "elevation_m", "shoes", "surface")


def normalize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize common column names to the app's documented CSV schema."""
    result = frame.copy()
    result.columns = [str(column).strip().lower().replace(" ", "_") for column in result.columns]
    aliases = {
        "distance": "distance_km",
        "duration": "duration_min",
        "heart_rate": "avg_hr_bpm",
        "average_hr": "avg_hr_bpm",
        "cadence": "cadence_spm",
        "shoe": "shoes",
    }
    for old, new in aliases.items():
        if old in result.columns and new not in result.columns:
            result = result.rename(columns={old: new})
    return result


def format_pace(minutes_per_km: float) -> str:
    """Format pace as MM:SS min/km."""
    total_seconds = max(0, round(float(minutes_per_km) * 60))
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes}:{seconds:02d} min/km"


def prepare_runs(frame: pd.DataFrame) -> pd.DataFrame:
    """Validate, clean and enrich an imported running-session dataframe.

    Rows with invalid dates, non-positive distances or non-positive durations
    are excluded. Required columns are date, distance_km and duration_min.
    """
    result = normalize_columns(frame)
    missing = [column for column in REQUIRED_COLUMNS if column not in result.columns]
    if missing:
        raise ValueError("Colonnes obligatoires manquantes : " + ", ".join(missing))

    result["date"] = pd.to_datetime(result["date"], errors="coerce")
    for column in NUMERIC_COLUMNS:
        if column in result.columns:
            result[column] = pd.to_numeric(result[column], errors="coerce")

    result = result.dropna(subset=list(REQUIRED_COLUMNS))
    result = result[(result["distance_km"] > 0) & (result["duration_min"] > 0)].copy()
    result["pace_min_km"] = result["duration_min"] / result["distance_km"]
    result["pace_label"] = result["pace_min_km"].map(format_pace)

    if "shoes" not in result.columns:
        result["shoes"] = "Non renseignées"
    else:
        result["shoes"] = result["shoes"].fillna("Non renseignées").astype(str)

    if "surface" not in result.columns:
        result["surface"] = "Non renseignée"
    else:
        result["surface"] = result["surface"].fillna("Non renseignée").astype(str)

    return result.sort_values("date").reset_index(drop=True)


def summarize_runs(frame: pd.DataFrame) -> dict[str, float | int | None]:
    """Return a compact summary of already-prepared running sessions."""
    if frame.empty:
        return {
            "sessions": 0,
            "distance_km": 0.0,
            "pace_min_km": None,
            "avg_hr_bpm": None,
            "cadence_spm": None,
        }

    distance = float(frame["distance_km"].sum())
    duration = float(frame["duration_min"].sum())
    avg_hr = frame["avg_hr_bpm"].mean() if "avg_hr_bpm" in frame else None
    cadence = frame["cadence_spm"].mean() if "cadence_spm" in frame else None

    return {
        "sessions": int(len(frame)),
        "distance_km": distance,
        "pace_min_km": duration / distance if distance > 0 else None,
        "avg_hr_bpm": float(avg_hr) if pd.notna(avg_hr) else None,
        "cadence_spm": float(cadence) if pd.notna(cadence) else None,
    }
