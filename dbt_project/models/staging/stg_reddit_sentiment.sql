SELECT
    LOWER(TRIM(subreddit))                    AS subreddit,
    post_date::date                           AS post_date,
    DATE_TRUNC('week', post_date)::date       AS week_start_date,
    post_count::integer                       AS post_count,
    avg_vader_compound::double precision      AS avg_vader_compound,
    neg_share::double precision               AS neg_share
FROM {{ source('raw_data', 'reddit_daily_sentiment') }}
WHERE post_count > 0