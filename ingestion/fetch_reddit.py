import time
import logging
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from ingestion.db import get_engine, execute_upsert

logger = logging.getLogger("fetch_reddit")

# ----- configurable parameters -----
SUBREDDITS = [
    # Budgeting & saving
    "frugal",
    "povertyfinance",
    "ynab",
    "personalfinance",
    "financialindependence",

    # Deals & shopping
    "deals",
    "buildapcsales",
    "dealsreddit",
    "coupons",
    "blackfriday",

    # Consumer purchases
    "buyitforlife",
    "Appliances",
    "furniture",
    "electronics",
    "shopping",

    # Consumer spending & sentiment
    "CreditCards",
    "debt",
    "adulting",
    "poverty",
    "ThriftStoreHauls",
]
CHUNK_DAYS       = 14
SLEEP_SECS       = 0.5
DEFAULT_LOOKBACK = 1800   # approx 5 years for initial backfill
INCR_LOOKBACK    = 21     # 3 weeks for weekly runs
# ------------------------------------

UPSERT_SQL = """
INSERT INTO raw.reddit_daily_sentiment (
    subreddit, post_date, post_count, avg_vader_compound, neg_share, ingested_at
)
VALUES (
    :subreddit, :post_date, :post_count, :avg_vader_compound, :neg_share, CURRENT_TIMESTAMP
)
ON CONFLICT (subreddit, post_date)
DO UPDATE SET
    post_count         = EXCLUDED.post_count,
    avg_vader_compound = EXCLUDED.avg_vader_compound,
    neg_share          = EXCLUDED.neg_share,
    ingested_at        = CURRENT_TIMESTAMP;
"""

def fetch_subreddit_window(subreddit: str, after_ts: int, before_ts: int) -> list[dict]:
    url = "https://arctic-shift.photon-reddit.com/api/posts/search"
    params = {"subreddit": subreddit, "after": after_ts, "before": before_ts, "limit": 100}
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json().get("data", [])

def run(lookback_days: int = DEFAULT_LOOKBACK):
    """
    Initial backfill: run with lookback_days=1800 (default).
    Weekly incremental: run with lookback_days=21.
    """
    analyzer = SentimentIntensityAnalyzer()
    engine   = get_engine()
    end_dt   = datetime.now(timezone.utc)
    start_dt = end_dt - timedelta(days=lookback_days)

    for sub in SUBREDDITS:
        logger.info(f"Fetching r/{sub} from {start_dt.date()} to {end_dt.date()}...")
        all_posts = []
        cursor = start_dt

        while cursor < end_dt:
            chunk_end = min(cursor + timedelta(days=CHUNK_DAYS), end_dt)
            try:
                posts = fetch_subreddit_window(sub, int(cursor.timestamp()), int(chunk_end.timestamp()))
                for p in posts:
                    title   = p.get("title", "")
                    created = p.get("created_utc")
                    if not title or not created:
                        continue
                    score = analyzer.polarity_scores(title)["compound"]
                    all_posts.append({
                        "post_date": datetime.fromtimestamp(created, tz=timezone.utc).date(),
                        "compound":  score,
                        "is_neg":    1 if score < -0.05 else 0,
                    })
                time.sleep(SLEEP_SECS)
            except Exception as exc:
                logger.warning(f"Chunk error for r/{sub} at {cursor.date()}: {exc}")
            cursor = chunk_end

        if not all_posts:
            continue

        df    = pd.DataFrame(all_posts)
        daily = (
            df.groupby("post_date", as_index=False)
              .agg(
                  post_count         =("compound", "count"),
                  avg_vader_compound =("compound", "mean"),
                  neg_share          =("is_neg",    "mean"),
              )
        )
        daily["subreddit"] = sub
        inserted = execute_upsert(engine, UPSERT_SQL, daily.to_dict(orient="records"))
        logger.info(f"  -> {inserted} daily rows upserted for r/{sub}.")

if __name__ == "__main__":
    run()