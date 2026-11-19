WITH ordered AS (
    SELECT
        UPPER(TRIM(ticker))                         AS ticker,
        trade_date::date                            AS trade_date,
        DATE_TRUNC('week', trade_date)::date        AS week_start_date,
        adj_close::double precision                 AS adj_close,
        volume::bigint                              AS volume,
        LAG(adj_close) OVER (PARTITION BY ticker ORDER BY trade_date) AS prev_close
    FROM {{ source('raw_data', 'etf_daily_prices') }}
)
SELECT
    ticker,
    trade_date,
    week_start_date,
    adj_close,
    volume,
    CASE
        WHEN prev_close > 0 THEN (adj_close - prev_close) / prev_close
        ELSE NULL
    END AS daily_return
FROM ordered