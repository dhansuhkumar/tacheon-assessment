"""
fetch.py — Retrieves daily weather forecast data from the Open-Meteo API.

This module is responsible for one thing: making the HTTP request and
returning the raw parsed JSON response. All configuration is read from
the config dict passed in by the caller. No values are hardcoded here.

On any failure — timeout, HTTP error, connection error, or unexpected
exception — the function logs the error at ERROR level and returns None.
It never raises to the caller.
"""

# Standard library
import logging
from typing import Any, Dict, Optional

# Third-party
import requests

logger = logging.getLogger(__name__)


def fetch_weather_data(config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Fetch daily weather forecast data from the Open-Meteo API.

    Reads all request parameters from the 'api' key of the provided config
    dict. Constructs the request, applies the configured timeout, and returns
    the parsed JSON body on success.

    Args:
        config: The full pipeline configuration dict loaded from config.yaml.
                Must contain an 'api' sub-dict with keys: base_url, latitude,
                longitude, parameters (list), forecast_days, timezone,
                timeout_seconds.

    Returns:
        The parsed API response as a dict on success. The 'daily' key in the
        response contains parallel lists — one value per forecast day per
        weather variable. Returns None on any failure.

    Failure behaviour:
        - requests.exceptions.Timeout: logs timeout duration and URL, returns None.
        - requests.exceptions.HTTPError: logs HTTP status code and URL, returns None.
        - requests.exceptions.ConnectionError: logs URL and connection detail, returns None.
        - Any other Exception: logs exception type and message, returns None.
        The caller must always check for None before proceeding.
    """
    api_cfg = config["api"]
    url: str = api_cfg["base_url"]
    timeout: int = api_cfg["timeout_seconds"]

    params: Dict[str, Any] = {
        "latitude": api_cfg["latitude"],
        "longitude": api_cfg["longitude"],
        "daily": ",".join(api_cfg["parameters"]),
        "forecast_days": api_cfg["forecast_days"],
        "timezone": api_cfg["timezone"],
    }

    logger.info(
        "Fetching weather data — url=%s lat=%.4f lon=%.4f forecast_days=%d",
        url,
        api_cfg["latitude"],
        api_cfg["longitude"],
        api_cfg["forecast_days"],
    )

    try:
        response = requests.get(url, params=params, timeout=timeout)
        response.raise_for_status()

        data: Dict[str, Any] = response.json()
        record_count: int = len(data.get("daily", {}).get("time", []))

        logger.info(
            "Fetch successful — %d daily records returned from %s",
            record_count,
            url,
        )
        return data

    except requests.exceptions.Timeout:
        logger.error(
            "Request timed out after %d seconds — url=%s",
            timeout,
            url,
        )
        return None

    except requests.exceptions.HTTPError as http_err:
        logger.error(
            "HTTP error %d received — url=%s detail=%s",
            http_err.response.status_code,
            url,
            str(http_err),
        )
        return None

    except requests.exceptions.ConnectionError as conn_err:
        logger.error(
            "Connection error — could not reach %s. "
            "Check network connectivity. detail=%s",
            url,
            str(conn_err),
        )
        return None

    except Exception as unexpected_err:
        logger.error(
            "Unexpected error during API fetch — url=%s type=%s detail=%s",
            url,
            type(unexpected_err).__name__,
            str(unexpected_err),
        )
        return None
