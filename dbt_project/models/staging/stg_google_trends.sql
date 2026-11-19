SELECT
    LOWER(TRIM(keyword))   AS keyword,
    week_start_date::date  AS week_start_date,
    interest_score::integer AS interest_score,
    ingested_at
FROM {{ source('raw_data', 'google_trends') }}
WHERE interest_score BETWEEN 0 AND 100