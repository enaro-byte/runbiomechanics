import pandas as pd

from metrics import prepare_runs, format_pace, summarize_runs


def test_format_pace():
    assert format_pace(6.0) == "6:00 min/km"


def test_prepare_runs_calculates_pace():
    df = pd.DataFrame({
        "date": ["2026-10-01"],
        "distance_km": [5.0],
        "duration_min": [30.0],
    })

    result = prepare_runs(df)

    assert result.iloc[0]["pace_min_km"] == 6.0


def test_prepare_runs_removes_invalid_distance():
    df = pd.DataFrame({
        "date": ["2026-10-01", "2026-10-02"],
        "distance_km": [5.0, 0],
        "duration_min": [30.0, 20.0],
    })

    result = prepare_runs(df)

    assert len(result) == 1


def test_summarize_runs():
    df = pd.DataFrame({
        "distance_km": [5.0, 10.0],
        "duration_min": [30.0, 60.0],
    })

    result = summarize_runs(df)

    assert result["sessions"] == 2
    assert result["distance_km"] == 15.0
    assert result["pace_min_km"] == 6.0
