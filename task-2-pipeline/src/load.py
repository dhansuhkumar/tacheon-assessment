"""
load.py — Loads the transformed weather DataFrame into a BigQuery table.

The BigQuery schema is defined explicitly as a list of SchemaField objects.
Autodetect is not used because it can infer wrong types (e.g. BOOLEAN fields
from True/False values that happen to be all-True in one run, or FLOAT where
INTEGER is expected). An explicit schema is a contract that does not change
with the data.

WRITE_TRUNCATE is used as the write disposition. The pipeline is designed to
run daily and replace the previous forecast entirely. This makes the load
idempotent: re-running the pipeline on the same day produces the same table
state. There is no risk of duplicate rows accumulating across pipeline runs.

On any failure, the function logs the error and returns False. It never raises
to the caller. The caller is responsible for deciding whether to exit.
"""

# Standard library
import logging
from typing import Any, Dict

# Third-party
import pandas as pd
from google.api_core.exceptions import GoogleAPIError
from google.cloud import bigquery

logger = logging.getLogger(__name__)

BIGQUERY_SCHEMA = [
    bigquery.SchemaField("date", "DATE", mode="NULLABLE"),
    bigquery.SchemaField("temperature_2m_max", "FLOAT64", mode="NULLABLE"),
    bigquery.SchemaField("temperature_2m_min", "FLOAT64", mode="NULLABLE"),
    bigquery.SchemaField("precipitation_sum", "FLOAT64", mode="NULLABLE"),
    bigquery.SchemaField("windspeed_10m_max", "FLOAT64", mode="NULLABLE"),
    bigquery.SchemaField("weathercode", "FLOAT64", mode="NULLABLE"),
    bigquery.SchemaField("temp_range_c", "FLOAT64", mode="NULLABLE"),
    bigquery.SchemaField("heat_risk_flag", "BOOL", mode="NULLABLE"),
    bigquery.SchemaField("is_rainy_day", "BOOL", mode="NULLABLE"),
    bigquery.SchemaField("comfort_index", "FLOAT64", mode="NULLABLE"),
    bigquery.SchemaField("ingestion_timestamp", "TIMESTAMP", mode="NULLABLE"),
    bigquery.SchemaField("data_source", "STRING", mode="NULLABLE"),
]


def load_to_bigquery(df: pd.DataFrame, config: Dict[str, Any]) -> bool:
    """
    Load the transformed weather DataFrame into the configured BigQuery table.

    Uses WRITE_TRUNCATE to replace the table contents on every run, ensuring
    idempotency. The schema is defined explicitly — autodetect is disabled.
    Authentication uses Application Default Credentials (ADC): set the
    GOOGLE_APPLICATION_CREDENTIALS environment variable to the path of your
    service account key before running the pipeline.

    Args:
        df:     The transformed DataFrame produced by transform_weather_data.
                Must be non-empty and conform to the expected schema.
        config: The full pipeline configuration dict. Must contain a 'bigquery'
                sub-dict with keys: project_id, dataset_id, table_id.

    Returns:
        True if the load job completed successfully.
        False on GoogleAPIError or any unexpected exception.
        The caller must check the return value and act accordingly.
    """
    bq_cfg = config["bigquery"]
    project_id: str = bq_cfg["project_id"]
    dataset_id: str = bq_cfg["dataset_id"]
    table_id: str = bq_cfg["table_id"]
    table_ref: str = f"{project_id}.{dataset_id}.{table_id}"

    logger.info(
        "Loading %d rows into BigQuery table %s using WRITE_TRUNCATE",
        len(df),
        table_ref,
    )

    job_config = bigquery.LoadJobConfig(
        schema=BIGQUERY_SCHEMA,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )

    try:
        client = bigquery.Client(project=project_id)
        load_job = client.load_table_from_dataframe(df, table_ref, job_config=job_config)
        load_job.result()  # Block until the job completes

        destination_table = client.get_table(table_ref)
        logger.info(
            "Load successful — %d rows now in %s",
            destination_table.num_rows,
            table_ref,
        )
        return True

    except GoogleAPIError as api_err:
        logger.error(
            "BigQuery API error while loading to %s — %s",
            table_ref,
            str(api_err),
        )
        return False

    except Exception as unexpected_err:
        logger.error(
            "Unexpected error during BigQuery load to %s — type=%s detail=%s",
            table_ref,
            type(unexpected_err).__name__,
            str(unexpected_err),
        )
        return False
