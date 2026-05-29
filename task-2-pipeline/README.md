# Task 2 — Data Pipeline

**Author:** Dhanush Kumar

---

## API Choice and Why

This pipeline uses [Open-Meteo](https://open-meteo.com/), a free and open-source weather API. I chose it for three specific reasons. First, it requires no API key, which means the pipeline runs end-to-end without any credential setup beyond BigQuery — a grader can clone this repo, configure GCP, and run it immediately. Second, the response structure is a nested dict of parallel arrays (`daily.temperature_2m_max`, `daily.precipitation_sum`, etc.), which is exactly the kind of structure that demonstrates non-trivial JSON flattening in the transform step. A flat API response would make the pipeline too simple to evaluate the transform logic. Third, Mumbai latitude/longitude data in late May and June sits in a pre-monsoon window where temperatures frequently exceed 35°C, making the `heat_risk_flag` and `comfort_index` derived fields genuinely meaningful rather than contrived.

---

## How to Run

**Prerequisites:** Python 3.9+, a Google account, access to GCP.

### 1. Clone the repo and install dependencies

```bash
git clone <your-repo-url>
cd tacheon/task-2-pipeline
pip install -r requirements.txt
```

### 2. Set up GCP (see BigQuery Setup below)

Create a GCP project, enable the BigQuery API, create a dataset named `weather_pipeline`, and generate a service account key with BigQuery Data Editor and Job User roles.

### 3. Set credentials

```bash
# Option A — service account key file (recommended for local runs)
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/service-account-key.json"

# Windows PowerShell equivalent
$env:GOOGLE_APPLICATION_CREDENTIALS = "C:\path\to\your\service-account-key.json"
```

Copy `.env.example` to `.env` and fill in your values. Never commit `.env`.

### 4. Edit config.yaml

Open `config/config.yaml` and set your GCP project ID:

```yaml
bigquery:
  project_id: "your-actual-project-id"   # ← change this
  dataset_id: "weather_pipeline"
  table_id: "mumbai_forecast"
```

All other values (API URL, coordinates, parameters) are pre-configured for Mumbai and ready to run.

### 5. Run the pipeline

```bash
# From the task-2-pipeline/ directory
python src/pipeline.py
```

The pipeline will print a summary to stdout on success:

```
========================================================
  PIPELINE SUMMARY
========================================================
  Status          : SUCCESS
  Started         : 2026-05-29 05:00:01 UTC
  Finished        : 2026-05-29 05:00:04 UTC
  Duration        : 3.21s
  Rows fetched    : 7
  Rows loaded     : 7
  Destination     : your-project.weather_pipeline.mumbai_forecast
  Heat-risk days  : 5
  Rainy days      : 2
========================================================
```

### 6. Run the tests (optional, no GCP needed)

```bash
python -m pytest tests/ -v
```

All 9 tests run offline. No API calls, no BigQuery credentials required.

---

## BigQuery Setup

### Create a project

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project (or use an existing one)
3. Enable the BigQuery API: **APIs & Services → Enable APIs → BigQuery API**

### Create the dataset

In the BigQuery console, create a dataset named `weather_pipeline` in your preferred region. The pipeline will create the table `mumbai_forecast` automatically on first run.

Or via `bq` CLI:

```bash
bq mk --dataset --location=US your-project-id:weather_pipeline
```

### GCP Sandbox note

If using a GCP Free Tier / Sandbox account, be aware that **DML statements (INSERT, UPDATE, DELETE) are not supported**. This pipeline uses `load_table_from_dataframe` with `WRITE_TRUNCATE`, which is a load job — not a DML statement. Load jobs work correctly on Sandbox accounts. The SQL queries in `sql/summary_query.sql` are read-only SELECT statements and also work on Sandbox.

### Service account permissions required

- `roles/bigquery.dataEditor` — to create and write to tables
- `roles/bigquery.jobUser` — to run load jobs

---

## SQL Query and Output

### Query 1 — Analytical Summary

```sql
SELECT
    MIN(date)                                           AS forecast_start,
    MAX(date)                                           AS forecast_end,
    COUNT(*)                                            AS total_days,
    ROUND(AVG(temperature_2m_max), 1)                  AS avg_max_temp_c,
    ROUND(MAX(temperature_2m_max), 1)                  AS peak_max_temp_c,
    ROUND(AVG(temperature_2m_min), 1)                  AS avg_min_temp_c,
    ROUND(AVG(temp_range_c), 1)                        AS avg_daily_temp_range_c,
    ROUND(SUM(precipitation_sum), 1)                   AS total_precipitation_mm,
    ROUND(AVG(windspeed_10m_max), 1)                   AS avg_max_windspeed_kmh,
    COUNTIF(heat_risk_flag = TRUE)                     AS heat_risk_days,
    COUNTIF(is_rainy_day = TRUE)                       AS rainy_days,
    ROUND(AVG(comfort_index), 1)                       AS avg_comfort_index,
    data_source,
    MAX(ingestion_timestamp)                            AS last_pipeline_run_utc
FROM `<project_id>.weather_pipeline.mumbai_forecast`
GROUP BY data_source;
```

**Output after running the pipeline** *(paste actual BigQuery output here after your first run — replace this block):*

```
forecast_start | forecast_end | total_days | avg_max_temp_c | peak_max_temp_c | avg_min_temp_c | avg_daily_temp_range_c | total_precipitation_mm | avg_max_windspeed_kmh | heat_risk_days | rainy_days | avg_comfort_index | data_source | last_pipeline_run_utc
---------------|--------------|------------|----------------|-----------------|----------------|------------------------|------------------------|-----------------------|----------------|------------|-------------------|-------------|----------------------
[paste here]
```

> **To complete this section:** Run `python src/pipeline.py`, then open the BigQuery console, run Query 1 from `sql/summary_query.sql` against your table, and paste the output above.

### Query 2 — Data Quality Check

```sql
SELECT
    COUNT(*)                                                    AS total_rows,
    COUNT(DISTINCT date)                                        AS distinct_dates,
    MIN(date)                                                   AS earliest_date,
    MAX(date)                                                   AS latest_date,
    COUNTIF(temperature_2m_max IS NULL)                        AS null_temp_max,
    COUNTIF(precipitation_sum IS NULL)                         AS null_precipitation,
    COUNTIF(data_source IS NULL OR data_source = '')            AS missing_source_label,
    TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), MAX(ingestion_timestamp), HOUR) AS hours_since_last_load,
    CASE
        WHEN TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), MAX(ingestion_timestamp), HOUR) > 25
        THEN 'STALE'
        ELSE 'FRESH'
    END                                                         AS freshness_status
FROM `<project_id>.weather_pipeline.mumbai_forecast`;
```

**Output after running the pipeline** *(paste here):*

```
total_rows | distinct_dates | earliest_date | latest_date | null_temp_max | null_precipitation | missing_source_label | hours_since_last_load | freshness_status
-----------|----------------|---------------|-------------|---------------|--------------------|----------------------|-----------------------|-----------------
[paste here]
```

---

## Production Strategy

### Scheduling

**Lightweight option — Cloud Scheduler + Cloud Run Jobs.**
Package the pipeline as a Docker container, deploy it as a Cloud Run Job, and point a Cloud Scheduler job at it to trigger daily at 5am. This is the right choice when the pipeline is a single script with no complex dependencies between tasks. Setup takes under an hour, cost is effectively zero for a daily run, and there is no infrastructure to manage.

**Robust option — Cloud Composer (managed Airflow).**
Use this when the pipeline grows to include multiple dependent tasks, branching logic, upstream data validation, or SLAs that require task-level retry and alerting. Composer's overhead (cost, setup time, learning curve) is only justified when the DAG complexity warrants it. For this single-flow pipeline, it would be over-engineering.

**Why `WRITE_TRUNCATE` matters for scheduling.**
The pipeline uses `WRITE_TRUNCATE` as the BigQuery write disposition. This means every run replaces the table's contents rather than appending. If the scheduler fires twice on the same day (which happens when a job is retried after a transient failure), the result is the same table state — not a duplicate dataset. Idempotency is the correct default for scheduled data loads.

### Failure Detection

Detection works at three layers:

**Layer 1 — Structured logging.**
Every module logs at INFO and ERROR level using Python's `logging` module. When deployed on Cloud Run, these logs are automatically captured by Cloud Logging. The pipeline exits with status code 1 on any step failure, which Cloud Run surfaces as a failed job execution.

**Layer 2 — Cloud Monitoring alert.**
Create a log-based metric in Cloud Logging that counts log entries at ERROR severity from this pipeline. Then create a Cloud Monitoring alert policy that fires when this metric exceeds 0 in a rolling 24-hour window. This sends a notification (email, PagerDuty, Slack) within minutes of any pipeline error.

**Layer 3 — BigQuery freshness check.**
Run Query 2 from `sql/summary_query.sql` as a scheduled query in BigQuery every 6 hours. If `hours_since_last_load` exceeds 25, the `freshness_status` column returns `'STALE'`. A downstream monitoring query or Looker Studio alert can surface this. This layer catches the failure mode where the pipeline itself succeeded but wrote no data — a scenario that layers 1 and 2 would miss.

### Scaling to 10x Data Volume

Four changes to handle 10x the current load:

**1. Async fetching with `httpx` + `asyncio`.**
If the pipeline is extended to cover multiple cities or multiple weather providers, replace `requests` with `httpx` and use `asyncio.gather` to fire all API calls in parallel. Fetching 10 cities currently takes 10 × 30s sequentially; with async it takes 30s total (bound by the slowest response, not the sum).

**2. GCS staging + `load_table_from_uri` for large payloads.**
`load_table_from_dataframe` loads in-memory. At 10x rows, memory pressure becomes a concern. The correct approach for large loads is to write the DataFrame to a Parquet file in Google Cloud Storage first, then use `load_table_from_uri` to load from GCS into BigQuery. This decouples the load volume from the memory footprint of the pipeline container.

**3. Partition the BigQuery table by date.**
Add `time_partitioning=bigquery.TimePartitioning(field="date")` to the `LoadJobConfig`. Queries that filter by date range then only scan the relevant partitions rather than the full table, reducing both query cost and latency as the table grows over months.

**4. Move transformation to dbt.**
When the pipeline produces data consumed by multiple downstream teams, `transform.py` becomes a bottleneck for governance: no lineage, no column-level documentation, no test framework. Moving transformation into dbt models adds column-level documentation, lineage tracking, and dbt's built-in test layer (`not_null`, `accepted_values`, custom schema tests) — without changing the load step.
