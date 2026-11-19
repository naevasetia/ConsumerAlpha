CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS intermediate;
CREATE SCHEMA IF NOT EXISTS mart;

-- Official retail sales + macro indicators from FRED
CREATE TABLE IF NOT EXISTS raw.fred_observations (
    series_id        VARCHAR(50)              NOT NULL,
    observation_date DATE                     NOT NULL,
    value            DOUBLE PRECISION,
    ingested_at      TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (series_id, observation_date)
);

-- Google Trends weekly search interest (scale: 0-100)
CREATE TABLE IF NOT EXISTS raw.google_trends (
    keyword          VARCHAR(100) NOT NULL,
    week_start_date  DATE         NOT NULL,
    interest_score   INTEGER      NOT NULL,
    ingested_at      TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (keyword, week_start_date)
);

-- Reddit post counts + VADER sentiment scores by subreddit/day
CREATE TABLE IF NOT EXISTS raw.reddit_daily_sentiment (
    subreddit           VARCHAR(100)     NOT NULL,
    post_date           DATE             NOT NULL,
    post_count          INTEGER          NOT NULL,
    avg_vader_compound  DOUBLE PRECISION NOT NULL,
    neg_share           DOUBLE PRECISION NOT NULL,
    ingested_at         TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (subreddit, post_date)
);

-- Daily adjusted close + volume for retail ETFs
CREATE TABLE IF NOT EXISTS raw.etf_daily_prices (
    ticker      VARCHAR(20)      NOT NULL,
    trade_date  DATE             NOT NULL,
    adj_close   DOUBLE PRECISION NOT NULL,
    volume      BIGINT           NOT NULL,
    ingested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ticker, trade_date)
);