
WITH retail_sales AS (
    SELECT
        series_id AS category_code,
        month_date,
        metric_value AS retail_sales_millions,

        LAG(metric_value, 1)
            OVER (PARTITION BY series_id ORDER BY month_date)
            AS sales_lag_1m,

        LAG(metric_value, 12)
            OVER (PARTITION BY series_id ORDER BY month_date)
            AS sales_lag_12m

    FROM {{ ref('stg_fred_series') }}

    WHERE series_id IN (
        'RSAFS',
        'RSGMS',
        'RSFHFS',
        'RSEAS',
        'RSDBS'
    )
),

sales_growth AS (
    SELECT
        category_code,
        month_date,
        retail_sales_millions,

        CASE
            WHEN sales_lag_12m > 0
            THEN ((retail_sales_millions - sales_lag_12m)
                / sales_lag_12m) * 100.0
        END AS retail_sales_yoy_pct,

        CASE
            WHEN sales_lag_1m > 0
            THEN ((retail_sales_millions - sales_lag_1m)
                / sales_lag_1m) * 100.0
        END AS retail_sales_mom_pct

    FROM retail_sales
),

features_yoy AS (
    SELECT
        month_date,

        -- Google Trends YoY changes

        (trend_electronics_m - LAG(trend_electronics_m, 12)
            OVER (ORDER BY month_date))
        / NULLIF(LAG(trend_electronics_m, 12)
            OVER (ORDER BY month_date), 0) * 100.0
            AS trend_electronics_yoy,

        (trend_furniture_m - LAG(trend_furniture_m, 12)
            OVER (ORDER BY month_date))
        / NULLIF(LAG(trend_furniture_m, 12)
            OVER (ORDER BY month_date), 0) * 100.0
            AS trend_furniture_yoy,

        (trend_home_improvement_m - LAG(trend_home_improvement_m, 12)
            OVER (ORDER BY month_date))
        / NULLIF(LAG(trend_home_improvement_m, 12)
            OVER (ORDER BY month_date), 0) * 100.0
            AS trend_home_improvement_yoy,

        (trend_deals_m - LAG(trend_deals_m, 12)
            OVER (ORDER BY month_date))
        / NULLIF(LAG(trend_deals_m, 12)
            OVER (ORDER BY month_date), 0) * 100.0
            AS trend_deals_yoy,

        (trend_financial_pressure_m
            - LAG(trend_financial_pressure_m, 12)
                OVER (ORDER BY month_date))
        / NULLIF(LAG(trend_financial_pressure_m, 12)
            OVER (ORDER BY month_date), 0) * 100.0
            AS trend_financial_pressure_yoy,

        -- Reddit sentiment
        reddit_sentiment_m,
        reddit_neg_share_m,

        -- Reddit activity YoY changes

        (reddit_weekly_posts_m - LAG(reddit_weekly_posts_m, 12)
            OVER (ORDER BY month_date))
        / NULLIF(LAG(reddit_weekly_posts_m, 12)
            OVER (ORDER BY month_date), 0) * 100.0
            AS reddit_posts_yoy,

        (reddit_budget_volume_m - LAG(reddit_budget_volume_m, 12)
            OVER (ORDER BY month_date))
        / NULLIF(LAG(reddit_budget_volume_m, 12)
            OVER (ORDER BY month_date), 0) * 100.0
            AS reddit_budget_yoy,

        (reddit_deals_volume_m - LAG(reddit_deals_volume_m, 12)
            OVER (ORDER BY month_date))
        / NULLIF(LAG(reddit_deals_volume_m, 12)
            OVER (ORDER BY month_date), 0) * 100.0
            AS reddit_deals_yoy,

        (reddit_shopping_volume_m - LAG(reddit_shopping_volume_m, 12)
            OVER (ORDER BY month_date))
        / NULLIF(LAG(reddit_shopping_volume_m, 12)
            OVER (ORDER BY month_date), 0) * 100.0
            AS reddit_shopping_yoy,

        -- ETF indicators

        (xrt_price_m - LAG(xrt_price_m, 12)
            OVER (ORDER BY month_date))
        / NULLIF(LAG(xrt_price_m, 12)
            OVER (ORDER BY month_date), 0) * 100.0
            AS xrt_yoy,

        xrt_vol_m,

        (xly_price_m - LAG(xly_price_m, 12)
            OVER (ORDER BY month_date))
        / NULLIF(LAG(xly_price_m, 12)
            OVER (ORDER BY month_date), 0) * 100.0
            AS xly_yoy,

        -- Lagged macroeconomic indicators

        (lagged_retail_job_openings
            - LAG(lagged_retail_job_openings, 12)
                OVER (ORDER BY month_date))
        / NULLIF(LAG(lagged_retail_job_openings, 12)
            OVER (ORDER BY month_date), 0) * 100.0
            AS job_openings_yoy,

        lagged_umich_sentiment,
        lagged_cc_delinquency

    FROM {{ ref('int_monthly_features') }}
)

SELECT
    f.month_date,

    c.category_code,
    c.category_name,
    c.sector_group,

    s.retail_sales_millions,
    s.retail_sales_yoy_pct,
    s.retail_sales_mom_pct,

    LAG(s.retail_sales_yoy_pct, 1)
        OVER (
            PARTITION BY c.category_code
            ORDER BY f.month_date
        ) AS target_yoy_lag_1m,

    -- Google Trends
    f.trend_electronics_yoy,
    f.trend_furniture_yoy,
    f.trend_home_improvement_yoy,
    f.trend_deals_yoy,
    f.trend_financial_pressure_yoy,

    -- Reddit
    f.reddit_sentiment_m,
    f.reddit_neg_share_m,
    f.reddit_posts_yoy,
    f.reddit_budget_yoy,
    f.reddit_deals_yoy,
    f.reddit_shopping_yoy,

    -- ETFs
    f.xrt_yoy,
    f.xrt_vol_m,
    f.xly_yoy,

    -- Macroeconomic indicators
    f.job_openings_yoy,
    f.lagged_umich_sentiment,
    f.lagged_cc_delinquency

FROM features_yoy f

CROSS JOIN {{ ref('dim_retail_categories') }} c

LEFT JOIN sales_growth s
    ON f.month_date = s.month_date
    AND c.category_code = s.category_code

WHERE COALESCE(
    f.trend_electronics_yoy,
    f.trend_furniture_yoy,
    f.trend_home_improvement_yoy,
    f.trend_deals_yoy,
    f.trend_financial_pressure_yoy
) IS NOT NULL