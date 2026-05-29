"""
pipeline.py — Orchestrates the fetch → transform → load sequence.

This is the entry point for the pipeline. It reads config once, configures
logging, then calls each module in sequence. If any step fails, it logs the
failure and exits with a non-zero status code so that the calling scheduler
(Cloud Scheduler, cron, CI) can detect and alert on the failure.

Run from the task-2-pipeline/ directory:
    python src/pipeline.py

Or with the -m flag (preferred, makes imports unambiguous):
    python -m src.pipeline
"""

# Standard library
import logging
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict

# Third-party
import yaml

# Ensure the src/ directory is on the path so sibling modules resolve correctly
# when running as a script rather than a module.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Local
from fetch import fetch_weather_data
from transform import transform_weather_data
from load import load_to_bigquery

# Path to config — resolved relative to this file so it works regardless of
# the directory the script is invoked from.
PROJECT_ROOT: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH: str = os.path.join(PROJECT_ROOT, "config", "config.yaml")


def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load and return the pipeline configuration from a YAML file.

    Args:
        config_path: Absolute path to the config.yaml file.

    Returns:
        Parsed config as a nested dict.

    Raises:
        FileNotFoundError: If the config file does not exist at the given path.
        yaml.YAMLError: If the file exists but cannot be parsed as valid YAML.
    """
    with open(config_path, "r", encoding="utf-8") as config_file:
        return yaml.safe_load(config_file)


def configure_logging(config: Dict[str, Any]) -> None:
    """
    Configure the root logger using settings from the config dict.

    Args:
        config: Full pipeline config. Must contain a 'logging' sub-dict
                with keys: level, format, datefmt.
    """
    log_cfg = config["logging"]
    logging.basicConfig(
        level=getattr(logging, log_cfg["level"].upper(), logging.INFO),
        format=log_cfg["format"],
        datefmt=log_cfg.get("datefmt", "%Y-%m-%d %H:%M:%S"),
    )


def main() -> None:
    """
    Main orchestration function for the weather data pipeline.

    Sequence:
        1. Load config from config.yaml.
        2. Configure logging.
        3. Record pipeline start time.
        4. Fetch raw data from Open-Meteo API.
        5. Transform raw data into enriched DataFrame.
        6. Load DataFrame into BigQuery.
        7. Log duration and print a clean summary.

    Exits with status code 1 if any step fails. This allows the calling
    scheduler or CI process to detect and alert on pipeline failures.
    """
    # --- Load config ---
    try:
        config = load_config(CONFIG_PATH)
    except FileNotFoundError:
        print(f"ERROR: config.yaml not found at {CONFIG_PATH}", file=sys.stderr)
        sys.exit(1)
    except yaml.YAMLError as yaml_err:
        print(f"ERROR: Failed to parse config.yaml — {yaml_err}", file=sys.stderr)
        sys.exit(1)

    configure_logging(config)
    logger = logging.getLogger(__name__)

    # --- Pipeline start ---
    pipeline_start: datetime = datetime.now(timezone.utc)
    start_monotonic: float = time.monotonic()

    logger.info(
        "Pipeline started at %s UTC",
        pipeline_start.strftime("%Y-%m-%d %H:%M:%S"),
    )

    # --- Step 1: Fetch ---
    logger.info("Step 1/3 — Fetching data from Open-Meteo API")
    raw_data = fetch_weather_data(config)

    if raw_data is None:
        logger.error("Fetch step failed — pipeline cannot continue. Exiting with status 1.")
        sys.exit(1)

    rows_fetched: int = len(raw_data.get("daily", {}).get("time", []))

    # --- Step 2: Transform ---
    logger.info("Step 2/3 — Transforming raw API response")
    df = transform_weather_data(raw_data)

    if df.empty:
        logger.error("Transform step produced empty DataFrame — pipeline cannot continue. Exiting with status 1.")
        sys.exit(1)

    rows_transformed: int = len(df)
    heat_risk_count: int = int(df["heat_risk_flag"].sum())
    rainy_day_count: int = int(df["is_rainy_day"].sum())

    # --- Step 3: Load ---
    logger.info("Step 3/3 — Loading %d rows into BigQuery", rows_transformed)
    load_success: bool = load_to_bigquery(df, config)

    if not load_success:
        logger.error("Load step failed — pipeline did not complete successfully. Exiting with status 1.")
        sys.exit(1)

    # --- Pipeline end ---
    end_monotonic: float = time.monotonic()
    duration_seconds: float = end_monotonic - start_monotonic
    pipeline_end: datetime = datetime.now(timezone.utc)

    logger.info(
        "Pipeline finished at %s UTC — duration %.2fs",
        pipeline_end.strftime("%Y-%m-%d %H:%M:%S"),
        duration_seconds,
    )

    # --- Clean summary to stdout ---
    bq_cfg = config["bigquery"]
    table_ref = f"{bq_cfg['project_id']}.{bq_cfg['dataset_id']}.{bq_cfg['table_id']}"

    print("\n" + "=" * 56)
    print("  PIPELINE SUMMARY")
    print("=" * 56)
    print(f"  Status          : SUCCESS")
    print(f"  Started         : {pipeline_start.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"  Finished        : {pipeline_end.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"  Duration        : {duration_seconds:.2f}s")
    print(f"  Rows fetched    : {rows_fetched}")
    print(f"  Rows loaded     : {rows_transformed}")
    print(f"  Destination     : {table_ref}")
    print(f"  Heat-risk days  : {heat_risk_count}")
    print(f"  Rainy days      : {rainy_day_count}")
    print("=" * 56 + "\n")


if __name__ == "__main__":
    main()
