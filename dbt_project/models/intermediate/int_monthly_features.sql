
WITH monthly_alt AS (
    SELECT
        month_date,

        -- Google Trends monthly averages
        AVG(trend_electronics) AS trend_electronics_m,
        AVG(trend_furniture) AS trend_furniture_m,
        AVG(trend_home_improvement) AS trend_home_improvement_m,
        AVG(trend_deals) AS trend_deals_m,
        AVG(trend_financial_pressure) AS trend_financial_pressure_m,

        -- Reddit monthly averages
        AVG(reddit_total_posts) AS reddit_weekly_posts_m,
        AVG(reddit_avg_sentiment) AS reddit_sentiment_m,
        AVG(reddit_neg_share) AS reddit_neg_share_m,

        AVG(reddit_budget_volume) AS reddit_budget_volume_m,
        AVG(reddit_deals_volume) AS reddit_deals_volume_m,
        AVG(reddit_shopping_volume) AS reddit_shopping_volume_m,

        -- ETF monthly averages
        AVG(xrt_avg_close) AS xrt_price_m,
        AVG(xrt_volatility) AS xrt_vol_m,
        AVG(xly_avg_close) AS xly_price_m

    FROM {{ ref('int_weekly_signals') }}
    GROUP BY month_date
),

macro_raw AS (
    SELECT
        month_date,

        MAX(CASE WHEN series_id = 'JTS4400JOL'
            THEN metric_value END) AS retail_job_openings,

        MAX(CASE WHEN series_id = 'UMCSENT'
            THEN metric_value END) AS umich_sentiment,

        MAX(CASE WHEN series_id = 'DRCCLACBS'
            THEN metric_value END) AS cc_delinquency

    FROM {{ ref('stg_fred_series') }}

    WHERE series_id IN (
        'JTS4400JOL',
        'UMCSENT',
        'DRCCLACBS'
    )

    GROUP BY month_date
),

macro_lagged AS (
    SELECT
        month_date,

        -- One-month publication lag
        LAG(retail_job_openings, 1)
            OVER (ORDER BY month_date)
            AS lagged_retail_job_openings,

        LAG(umich_sentiment, 1)
            OVER (ORDER BY month_date)
            AS lagged_umich_sentiment,

        -- Three-month lag for quarterly delinquency data
        LAG(cc_delinquency, 3)
            OVER (ORDER BY month_date)
            AS lagged_cc_delinquency

    FROM macro_raw
)

SELECT
    a.*,

    m.lagged_retail_job_openings,
    m.lagged_umich_sentiment,
    m.lagged_cc_delinquency

FROM monthly_alt a

LEFT JOIN macro_lagged m
    USING (month_date)