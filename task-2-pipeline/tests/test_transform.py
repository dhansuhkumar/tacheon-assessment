"""
test_transform.py — Unit tests for the transform module.

Tests cover:
    1. Normal input produces the correct number of output rows.
    2. Null values in the API response are handled without crashing,
       and produce NaN rather than errors.
    3. Derived fields (temp_range_c, heat_risk_flag, is_rainy_day,
       comfort_index) are calculated correctly for a known input.
    4. Empty or malformed input returns an empty DataFrame with the
       correct column schema — not an exception.
    5. heat_risk_flag boundary: exactly 38.0 °C must not flag (> not >=),
       and 38.1 °C must flag.

No external services are called. These tests are fully offline.
Run from the task-2-pipeline/ directory: pytest tests/
"""

# Standard library
from typing import Any, Dict, List, Optional

# Third-party
import pandas as pd
import pytest

# Local — resolved via conftest.py path injection
from transform import (
    EXPECTED_COLUMNS,
    HEAT_RISK_THRESHOLD_C,
    transform_weather_data,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_api_response(
    times: Optional[List[str]] = None,
    temp_max: Optional[List[Any]] = None,
    temp_min: Optional[List[Any]] = None,
    precipitation: Optional[List[Any]] = None,
    windspeed: Optional[List[Any]] = None,
    weathercode: Optional[List[Any]] = None,
) -> Dict[str, Any]:
    """
    Build a minimal mock Open-Meteo API response dict.

    Defaults to three days of clean, representative Mumbai data.
    Any argument can be overridden to inject specific test values,
    including None entries to simulate missing data from the API.
    """
    n = len(times) if times is not None else 3
    return {
        "daily": {
            "time": times if times is not None else [
                "2026-05-29", "2026-05-30", "2026-05-31"
            ],
            "temperature_2m_max": temp_max if temp_max is not None else [34.0, 35.0, 33.0],
            "temperature_2m_min": temp_min if temp_min is not None else [26.0, 27.0, 25.0],
            "precipitation_sum": precipitation if precipitation is not None else [0.0, 1.5, 0.0],
            "windspeed_10m_max": windspeed if windspeed is not None else [18.0, 22.0, 15.0],
            "weathercode": weathercode if weathercode is not None else [0, 61, 0],
        }
    }


# ---------------------------------------------------------------------------
# Test 1: Normal input produces the correct number of rows
# ---------------------------------------------------------------------------

def test_normal_input_returns_correct_row_count() -> None:
    """
    Three dates in the API response should produce exactly three rows.
    Verifies that the flatten step works correctly and produces one row
    per forecast day, no more and no fewer.
    """
    raw = make_api_response()
    df = transform_weather_data(raw)

    assert len(df) == 3, f"Expected 3 rows, got {len(df)}"
    assert list(df.columns) == EXPECTED_COLUMNS


# ---------------------------------------------------------------------------
# Test 2: Null values are handled without crashing
# ---------------------------------------------------------------------------

def test_null_values_in_api_response_handled_gracefully() -> None:
    """
    None values in the API response arrays should be coerced to NaN,
    not raise an exception. The transform must complete and return a
    DataFrame — not crash, not skip rows, and not silently drop columns.
    """
    raw = make_api_response(
        temp_max=[34.0, None, 33.0],
        temp_min=[26.0, None, 25.0],
        precipitation=[0.0, None, 0.0],
        windspeed=[18.0, None, 15.0],
    )

    # Must not raise
    df = transform_weather_data(raw)

    assert len(df) == 3, "Null values should not drop rows"
    assert pd.isna(df.loc[1, "temperature_2m_max"]), "None should coerce to NaN, not 0 or a string"
    assert pd.isna(df.loc[1, "temperature_2m_min"]), "None in temp_min should become NaN"
    assert pd.isna(df.loc[1, "temp_range_c"]), "temp_range_c should be NaN when inputs are NaN"


# ---------------------------------------------------------------------------
# Test 3: Derived fields are calculated correctly for known inputs
# ---------------------------------------------------------------------------

def test_derived_fields_calculated_correctly() -> None:
    """
    Verify each derived field against a manually computed expected value.

    Known input (day 0):
        temp_max = 36.0, temp_min = 28.0, precipitation = 2.0, windspeed = 30.0

    Expected:
        temp_range_c = 36.0 - 28.0 = 8.0
        heat_risk_flag = False (36.0 is not > 38.0)
        is_rainy_day = True (2.0 > 1.0)
        avg_temp = (36.0 + 28.0) / 2 = 32.0
        temp_penalty = abs(32.0 - 25.0) * 3 = 21.0
        rain_penalty = 2.0 * 5 = 10.0
        wind_penalty = (30.0 - 25.0) * 2 = 10.0
        comfort_index = max(0, 100 - 21 - 10 - 10) = 59.0
    """
    raw = make_api_response(
        times=["2026-05-29"],
        temp_max=[36.0],
        temp_min=[28.0],
        precipitation=[2.0],
        windspeed=[30.0],
        weathercode=[61],
    )
    df = transform_weather_data(raw)

    assert len(df) == 1
    assert df.loc[0, "temp_range_c"] == pytest.approx(8.0, abs=0.01)
    assert df.loc[0, "heat_risk_flag"] is False or df.loc[0, "heat_risk_flag"] == False
    assert df.loc[0, "is_rainy_day"] is True or df.loc[0, "is_rainy_day"] == True
    assert df.loc[0, "comfort_index"] == pytest.approx(59.0, abs=0.1)
    assert df.loc[0, "data_source"] == "open-meteo"
    assert df.loc[0, "ingestion_timestamp"] is not None


# ---------------------------------------------------------------------------
# Test 4: Empty or malformed input returns empty DataFrame with correct schema
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad_input", [
    {},
    {"daily": {}},
    {"daily": {"time": []}},
    None,
    {"wrong_key": "wrong_value"},
])
def test_empty_or_malformed_input_returns_empty_dataframe(
    bad_input: Any,
) -> None:
    """
    Any input that lacks a valid 'daily.time' array should return a zero-row
    DataFrame — not raise an exception, not return None, and not return a
    DataFrame with wrong columns.

    Parametrised to cover the most likely real-world failure shapes:
    - Completely empty dict (network succeeded but response was empty)
    - Dict with 'daily' key but no contents
    - Dict with 'daily.time' as an empty list
    - None (e.g. if caller passes fetch result without checking)
    - Dict with an unexpected top-level key
    """
    df = transform_weather_data(bad_input)

    assert isinstance(df, pd.DataFrame), "Should always return a DataFrame"
    assert len(df) == 0, "Bad input should produce zero rows"
    assert list(df.columns) == EXPECTED_COLUMNS, (
        f"Columns must match schema even for empty DataFrame. "
        f"Got: {list(df.columns)}"
    )


# ---------------------------------------------------------------------------
# Test 5: heat_risk_flag boundary — strictly greater than 38.0 °C
# ---------------------------------------------------------------------------

def test_heat_risk_flag_boundary() -> None:
    """
    heat_risk_flag must fire only when temperature_2m_max is strictly
    greater than 38.0 °C (the threshold defined in transform.py).

    At exactly 38.0 °C: flag must be False (not > threshold).
    At 38.1 °C:         flag must be True  (> threshold).
    At 37.9 °C:         flag must be False (below threshold).

    This test pins the boundary precisely so a future change to the
    threshold (e.g. changing > to >=) fails loudly.
    """
    raw = make_api_response(
        times=["2026-05-29", "2026-05-30", "2026-05-31"],
        temp_max=[37.9, HEAT_RISK_THRESHOLD_C, 38.1],
        temp_min=[26.0, 26.0, 26.0],
        precipitation=[0.0, 0.0, 0.0],
        windspeed=[15.0, 15.0, 15.0],
        weathercode=[0, 0, 0],
    )
    df = transform_weather_data(raw)

    assert len(df) == 3

    # 37.9 °C — below threshold
    assert not df.loc[0, "heat_risk_flag"], (
        f"37.9 °C should NOT flag (threshold is > {HEAT_RISK_THRESHOLD_C})"
    )

    # Exactly 38.0 °C — equal to threshold, must NOT flag (strict >)
    assert not df.loc[1, "heat_risk_flag"], (
        f"Exactly {HEAT_RISK_THRESHOLD_C} °C should NOT flag (condition is strictly >)"
    )

    # 38.1 °C — above threshold, must flag
    assert df.loc[2, "heat_risk_flag"], (
        f"38.1 °C SHOULD flag (38.1 > {HEAT_RISK_THRESHOLD_C})"
    )
