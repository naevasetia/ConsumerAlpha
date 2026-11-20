
WITH trends_pivoted AS (
    SELECT
        week_start_date,

        -- Electronics
        AVG(CASE WHEN keyword IN (
            'buy laptop',
            'best smartphone',
            'buy iphone',
            'washing machine price',
            'refrigerator sale',
            'buy television',
            'headphones sale'
        ) THEN interest_score END) AS trend_electronics,

        -- Furniture and furnishings
        AVG(CASE WHEN keyword IN (
            'furniture sale',
            'sofa set price',
            'mattress sale',
            'bedroom furniture',
            'home decor',
            'office furniture'
        ) THEN interest_score END) AS trend_furniture,

        -- Home improvement
        AVG(CASE WHEN keyword IN (
            'home renovation',
            'home improvement',
            'kitchen remodeling',
            'flooring materials',
            'paint prices',
            'garden supplies'
        ) THEN interest_score END) AS trend_home_improvement,

        -- Deals and discounts
        AVG(CASE WHEN keyword IN (
            'discount code',
            'clearance sale',
            'black friday deals',
            'online shopping deals',
            'walmart deals',
            'amazon deals',
            'coupon codes',
            'cheap alternatives',
            'best deals online',
            'price comparison'
        ) THEN interest_score END) AS trend_deals,

        -- Financial pressure
        AVG(CASE WHEN keyword IN (
            'buy now pay later',
            'credit card debt'
        ) THEN interest_score END) AS trend_financial_pressure

    FROM {{ ref('stg_google_trends') }}
    GROUP BY week_start_date
),

reddit_weekly AS (
    SELECT
        week_start_date,

        SUM(post_count) AS reddit_total_posts,

        SUM(avg_vader_compound * post_count)
            / NULLIF(SUM(post_count), 0) AS reddit_avg_sentiment,

        SUM(neg_share * post_count)
            / NULLIF(SUM(post_count), 0) AS reddit_neg_share,

        -- Budgeting and financial communities
        SUM(CASE WHEN subreddit IN (
            'frugal',
            'povertyfinance',
            'ynab',
            'personalfinance',
            'financialindependence',
            'creditcards',
            'debt',
            'adulting',
            'poverty'
        ) THEN post_count ELSE 0 END) AS reddit_budget_volume,

        -- Deals and discount communities
        SUM(CASE WHEN subreddit IN (
            'deals',
            'buildapcsales',
            'dealsreddit',
            'coupons',
            'blackfriday'
        ) THEN post_count ELSE 0 END) AS reddit_deals_volume,

        -- Shopping and product communities
        SUM(CASE WHEN subreddit IN (
            'buyitforlife',
            'appliances',
            'furniture',
            'electronics',
            'shopping',
            'thriftstorehauls'
        ) THEN post_count ELSE 0 END) AS reddit_shopping_volume

    FROM {{ ref('stg_reddit_sentiment') }}
    GROUP BY week_start_date
),

etf_weekly AS (
    SELECT
        week_start_date,

        AVG(CASE WHEN ticker = 'XRT'
            THEN adj_close END) AS xrt_avg_close,

        STDDEV(CASE WHEN ticker = 'XRT'
            THEN daily_return END) AS xrt_volatility,

        AVG(CASE WHEN ticker = 'XLY'
            THEN adj_close END) AS xly_avg_close

    FROM {{ ref('stg_etf_prices') }}
    GROUP BY week_start_date
)

SELECT
    t.week_start_date,
    DATE_TRUNC('month', t.week_start_date)::date AS month_date,

    t.trend_electronics,
    t.trend_furniture,
    t.trend_home_improvement,
    t.trend_deals,
    t.trend_financial_pressure,

    r.reddit_total_posts,
    r.reddit_avg_sentiment,
    r.reddit_neg_share,
    r.reddit_budget_volume,
    r.reddit_deals_volume,
    r.reddit_shopping_volume,

    e.xrt_avg_close,
    e.xrt_volatility,
    e.xly_avg_close

FROM trends_pivoted t

LEFT JOIN reddit_weekly r
    USING (week_start_date)

LEFT JOIN etf_weekly e
    USING (week_start_date)