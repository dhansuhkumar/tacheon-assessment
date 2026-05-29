-- ============================================================
-- File    : summary_query.sql
-- Table   : <project_id>.weather_pipeline.mumbai_forecast
-- Purpose : Two queries against the Mumbai weather forecast table.
--
--   Query 1 — Analytical Summary
--     Aggregates the 7-day forecast into a single summary row.
--     Shows temperature range, precipitation totals, risk-day counts,
--     and the average comfort index. Answers the question: "What is
--     the weather story for Mumbai in the next 7 days?"
--
--   Query 2 — Data Quality Check
--     Validates that the pipeline loaded correctly. Checks row count,
--     null rates for key fields, date range coverage, and data freshness
--     (hours since last ingestion). A freshness age above 25 hours
--     indicates the daily pipeline did not run as scheduled.
--
-- Replace <project_id> with your actual GCP project ID before running.
-- ============================================================


-- ============================================================
-- QUERY 1: Analytical Summary
-- ============================================================
SELECT
    MIN(date)                                           AS forecast_start,
    MAX(date)                                           AS forecast_end,
    COUNT(*)                                            AS total_days,

    -- Temperature
    ROUND(AVG(temperature_2m_max), 1)                  AS avg_max_temp_c,
    ROUND(MAX(temperature_2m_max), 1)                  AS peak_max_temp_c,
    ROUND(AVG(temperature_2m_min), 1)                  AS avg_min_temp_c,
    ROUND(AVG(temp_range_c), 1)                        AS avg_daily_temp_range_c,

    -- Precipitation
    ROUND(SUM(precipitation_sum), 1)                   AS total_precipitation_mm,
    ROUND(AVG(precipitation_sum), 1)                   AS avg_daily_precipitation_mm,

    -- Wind
    ROUND(AVG(windspeed_10m_max), 1)                   AS avg_max_windspeed_kmh,
    ROUND(MAX(windspeed_10m_max), 1)                   AS peak_windspeed_kmh,

    -- Risk and comfort flags
    COUNTIF(heat_risk_flag = TRUE)                     AS heat_risk_days,
    COUNTIF(is_rainy_day = TRUE)                       AS rainy_days,
    COUNTIF(heat_risk_flag = TRUE AND is_rainy_day = TRUE)
                                                        AS hot_and_rainy_days,

    -- Comfort index
    ROUND(AVG(comfort_index), 1)                       AS avg_comfort_index,
    ROUND(MIN(comfort_index), 1)                       AS worst_comfort_day_score,
    ROUND(MAX(comfort_index), 1)                       AS best_comfort_day_score,

    -- Pipeline metadata
    data_source,
    MAX(ingestion_timestamp)                            AS last_pipeline_run_utc

FROM
    `<project_id>.weather_pipeline.mumbai_forecast`

GROUP BY
    data_source
;


-- ============================================================
-- QUERY 2: Data Quality Check
-- ============================================================
SELECT
    -- Row count and date coverage
    COUNT(*)                                                    AS total_rows,
    COUNT(DISTINCT date)                                        AS distinct_dates,
    MIN(date)                                                   AS earliest_date,
    MAX(date)                                                   AS latest_date,
    DATE_DIFF(MAX(date), MIN(date), DAY) + 1                   AS days_in_range,

    -- Null checks for critical fields
    COUNTIF(date IS NULL)                                       AS null_date_count,
    COUNTIF(temperature_2m_max IS NULL)                        AS null_temp_max,
    COUNTIF(temperature_2m_min IS NULL)                        AS null_temp_min,
    COUNTIF(precipitation_sum IS NULL)                         AS null_precipitation,
    COUNTIF(windspeed_10m_max IS NULL)                         AS null_windspeed,
    COUNTIF(comfort_index IS NULL)                             AS null_comfort_index,

    -- Source and ingestion integrity
    COUNTIF(data_source IS NULL OR data_source = '')            AS missing_source_label,
    COUNTIF(ingestion_timestamp IS NULL)                        AS missing_ingestion_ts,

    -- Freshness check: hours since the most recent pipeline run
    -- Alert if this exceeds 25 hours — indicates a missed daily run
    TIMESTAMP_DIFF(
        CURRENT_TIMESTAMP(),
        MAX(ingestion_timestamp),
        HOUR
    )                                                           AS hours_since_last_load,

    CASE
        WHEN TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), MAX(ingestion_timestamp), HOUR) > 25
        THEN 'STALE — pipeline may have missed a run'
        ELSE 'FRESH'
    END                                                         AS freshness_status

FROM
    `<project_id>.weather_pipeline.mumbai_forecast`
;
