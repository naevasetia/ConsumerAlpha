SELECT
    TRIM(series_id)                            AS series_id,
    observation_date::date                     AS observation_date,
    DATE_TRUNC('month', observation_date)::date AS month_date,
    value::double precision                    AS metric_value,
    ingested_at
FROM {{ source('raw_data', 'fred_observations') }}
WHERE value IS NOT NULL