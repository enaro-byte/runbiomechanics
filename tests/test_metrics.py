import pandas as pd

from metrics import calculate_pace, prepare_runs


def test_calculate_pace():
    assert calculate_pace(10, 60) == 6.0


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
