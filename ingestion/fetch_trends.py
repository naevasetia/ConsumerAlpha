import time
import logging
import pandas as pd
from trendspy import Trends
from ingestion.db import get_engine, execute_upsert

logger = logging.getLogger("fetch_trends")

# ----- configurable parameters -----
KEYWORDS = [
    # Electronics & Appliances
    "buy laptop",
    "best smartphone",
    "buy iphone",
    "washing machine price",
    "refrigerator sale",
    "buy television",
    "headphones sale",

    # Furniture & Home Furnishings
    "furniture sale",
    "sofa set price",
    "mattress sale",
    "bedroom furniture",
    "home decor",
    "office furniture",

    # Building Materials & Home Improvement
    "home renovation",
    "home improvement",
    "kitchen remodeling",
    "flooring materials",
    "paint prices",
    "garden supplies",

    # General Merchandise
    "discount code",
    "clearance sale",
    "black friday deals",
    "online shopping deals",
    " Walmart deals",
    "Amazon deals",

    # Consumer Spending & Financial Behaviour
    "buy now pay later",
    "credit card debt",
    "coupon codes",
    "cheap alternatives",
    "best deals online",
    "price comparison",
]
TIMEFRAME    = "today 5-y"
GEO          = "US"
SLEEP_SECS   = 3
# ------------------------------------

UPSERT_SQL = """
INSERT INTO raw.google_trends (keyword, week_start_date, interest_score, ingested_at)
VALUES (:keyword, :week_start_date, :interest_score, CURRENT_TIMESTAMP)
ON CONFLICT (keyword, week_start_date)
DO UPDATE SET
    interest_score = EXCLUDED.interest_score,
    ingested_at    = CURRENT_TIMESTAMP;
"""

def run():
    tr = Trends()
    engine = get_engine()
    total_rows = 0

    for kw in KEYWORDS:
        logger.info(f"Fetching Google Trends for '{kw}'...")
        try:
            df = tr.interest_over_time([kw], timeframe=TIMEFRAME, geo=GEO)
            if df is None or df.empty:
                logger.warning(f"No data for: {kw}")
                continue

            df = df.reset_index()
            date_col = df.columns[0]

            records = []
            for _, row in df.iterrows():
                dt = pd.to_datetime(row[date_col]).date()
                monday = dt - pd.Timedelta(days=dt.weekday())  # normalize to Monday
                records.append({
                    "keyword":         kw,
                    "week_start_date": monday,
                    "interest_score":  int(row[kw]),
                })

            inserted = execute_upsert(engine, UPSERT_SQL, records)
            total_rows += inserted
            logger.info(f"  -> {inserted} weekly rows upserted.")
        except Exception as exc:
            logger.error(f"Failed for '{kw}': {exc}")

        time.sleep(SLEEP_SECS)

    logger.info(f"Google Trends ingestion done. Total rows: {total_rows}")

if __name__ == "__main__":
    run()