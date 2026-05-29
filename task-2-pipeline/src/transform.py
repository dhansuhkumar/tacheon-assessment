"""
transform.py — Flattens the Open-Meteo API response and enriches it with
derived fields ready for loading into BigQuery.

The Open-Meteo 'daily' response is a dict of parallel arrays, one value per
day per variable. This module pivots that structure into a standard row-per-day
DataFrame, coerces types explicitly, and adds computed columns that make the
data analytically useful without requiring post-load SQL work.

Output schema (one row per forecast day):

    date                (datetime64[ns]) : Forecast date.
    temperature_2m_max  (float64)        : Maximum 2m air temperature, °C.
    temperature_2m_min  (float64)        : Minimum 2m air temperature, °C.
    precipitation_sum   (float64)        : Total precipitation, mm.
    windspeed_10m_max   (float64)        : Maximum 10m wind speed, km/h.
    weathercode         (float64)        : WMO weather interpretation code.
    temp_range_c        (float64)        : temperature_2m_max - temperature_2m_min.
    heat_risk_flag      (bool)           : True when temperature_2m_max > 38.0 °C.
    is_rainy_day        (bool)           : True when precipitation_sum > 1.0 mm.
    comfort_index       (float64)        : Composite comfort score, 0–100.
                                           Formula: max(0, 100
                                             - abs(avg_temp - 25) * 3
                                             - precipitation_sum * 5
                                             - max(0, windspeed_10m_max - 25) * 2)
                                           where avg_temp = (temp_max + temp_min) / 2.
                                           Penalty components:
                                             Temperature: 3 pts per °C from 25 °C ideal.
                                             Rainfall:    5 pts per mm of precipitation.
                                             Wind:        2 pts per km/h above 25 km/h.
                                           NaN when temperature inputs are both missing.
    ingestion_timestamp (datetime64[ns]) : UTC timestamp of this pipeline run.
    data_source         (str)            : Literal "open-meteo".
"""

# Standard library
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

# Third-party
import pandas as pd

logger = logging.getLogger(__name__)

# Module-level constants
DATA_SOURCE: str = "open-meteo"
HEAT_RISK_THRESHOLD_C: float = 38.0
RAIN_THRESHOLD_MM: float = 1.0
COMFORT_IDEAL_TEMP_C: float = 25.0
COMFORT_TEMP_PENALTY: float = 3.0
COMFORT_RAIN_PENALTY: float = 5.0
COMFORT_WIND_THRESHOLD_KMH: float = 25.0
COMFORT_WIND_PENALTY: float = 2.0

EXPECTED_COLUMNS: List[str] = [
    "date",
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "windspeed_10m_max",
    "weathercode",
    "temp_range_c",
    "heat_risk_flag",
    "is_rainy_day",
    "comfort_index",
    "ingestion_timestamp",
    "data_source",
]


def _empty_dataframe() -> pd.DataFrame:
    """
    Return an empty DataFrame with the correct output schema.

    Used as the safe return value when the input is missing or malformed.
    Guarantees callers always receive a DataFrame with known columns,
    regardless of input quality.

    Returns:
        pd.DataFrame: Zero-row DataFrame with all expected output columns.
    """
    return pd.DataFrame(columns=EXPECTED_COLUMNS)


def _compute_comfort_index(row: pd.Series) -> float:
    """
    Compute the composite human comfort index for a single forecast row.

    The score starts at 100 and loses points for three discomfort factors:
    temperature deviation from an ideal of 25 °C, precipitation, and high
    wind. The result is clamped to [0.0, 100.0]. Returns float('nan') when
    both temperature inputs are NaN, making it impossible to compute a
    meaningful score.

    Args:
        row: A pandas Series with fields temperature_2m_max,
             temperature_2m_min, precipitation_sum, windspeed_10m_max.
             Any of these may be NaN (result of earlier coercion).

    Returns:
        float: Comfort index in the range [0.0, 100.0], or NaN if
               temperature data is entirely absent.
    """
    temp_max: float = row["temperature_2m_max"]
    temp_min: float = row["temperature_2m_min"]
    precipitation: float = row["precipitation_sum"]
    windspeed: float = row["windspeed_10m_max"]

    # Cannot compute a meaningful score without temperature
    if pd.isna(temp_max) and pd.isna(temp_min):
        return float("nan")

    avg_temp: float = pd.Series([temp_max, temp_min]).mean()

    temp_penalty: float = abs(avg_temp - COMFORT_IDEAL_TEMP_C) * COMFORT_TEMP_PENALTY
    rain_penalty: float = (precipitation * COMFORT_RAIN_PENALTY) if not pd.isna(precipitation) else 0.0
    wind_excess: float = max(0.0, windspeed - COMFORT_WIND_THRESHOLD_KMH) if not pd.isna(windspeed) else 0.0
    wind_penalty: float = wind_excess * COMFORT_WIND_PENALTY

    raw_score: float = 100.0 - temp_penalty - rain_penalty - wind_penalty
    return round(max(0.0, min(100.0, raw_score)), 2)


def transform_weather_data(raw_data: Dict[str, Any]) -> pd.DataFrame:
    """
    Transform the raw Open-Meteo API response into an enriched DataFrame.

    Flattens the nested 'daily' parallel arrays into one row per forecast day,
    coerces all numeric fields explicitly (NaN on parse failure), and adds six
    derived fields. Returns an empty DataFrame with correct columns if the
    input is missing, empty, or lacks the expected 'daily' key.

    Args:
        raw_data: The parsed JSON dict returned by fetch_weather_data.
                  Expected to contain a 'daily' key with parallel list values,
                  one per forecast day.

    Returns:
        pd.DataFrame: One row per forecast day with the full output schema
                      described in this module's docstring. Returns an empty
                      DataFrame (correct columns, zero rows) on bad input.
    """
    ingestion_timestamp: datetime = datetime.now(timezone.utc).replace(tzinfo=None)

    if not raw_data or "daily" not in raw_data or not raw_data["daily"]:
        logger.error(
            "transform received empty or malformed input — "
            "expected dict with 'daily' key. Returning empty DataFrame."
        )
        return _empty_dataframe()

    daily: Dict[str, Any] = raw_data["daily"]

    if "time" not in daily or not daily["time"]:
        logger.error(
            "transform: 'daily.time' key missing or empty. Returning empty DataFrame."
        )
        return _empty_dataframe()

    # --- Build base DataFrame from parallel arrays ---
    df = pd.DataFrame({
        "date": daily.get("time", []),
        "temperature_2m_max": daily.get("temperature_2m_max", []),
        "temperature_2m_min": daily.get("temperature_2m_min", []),
        "precipitation_sum": daily.get("precipitation_sum", []),
        "windspeed_10m_max": daily.get("windspeed_10m_max", []),
        "weathercode": daily.get("weathercode", []),
    })

    # --- Explicit type coercion — nulls become NaN, not crashes ---
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["temperature_2m_max"] = pd.to_numeric(df["temperature_2m_max"], errors="coerce")
    df["temperature_2m_min"] = pd.to_numeric(df["temperature_2m_min"], errors="coerce")
    df["precipitation_sum"] = pd.to_numeric(df["precipitation_sum"], errors="coerce")
    df["windspeed_10m_max"] = pd.to_numeric(df["windspeed_10m_max"], errors="coerce")
    df["weathercode"] = pd.to_numeric(df["weathercode"], errors="coerce")

    # --- Derived fields ---
    df["temp_range_c"] = (df["temperature_2m_max"] - df["temperature_2m_min"]).round(2)

    df["heat_risk_flag"] = df["temperature_2m_max"] > HEAT_RISK_THRESHOLD_C

    df["is_rainy_day"] = df["precipitation_sum"] > RAIN_THRESHOLD_MM

    df["comfort_index"] = df.apply(_compute_comfort_index, axis=1)

    df["ingestion_timestamp"] = ingestion_timestamp
    df["data_source"] = DATA_SOURCE

    # --- Reorder columns to match output schema ---
    df = df[EXPECTED_COLUMNS]

    # --- Logging summary ---
    row_count: int = len(df)
    heat_risk_count: int = int(df["heat_risk_flag"].sum())
    rainy_day_count: int = int(df["is_rainy_day"].sum())

    logger.info(
        "Transform complete — %d rows produced, %d heat-risk day(s), %d rainy day(s)",
        row_count,
        heat_risk_count,
        rainy_day_count,
    )

    return df
