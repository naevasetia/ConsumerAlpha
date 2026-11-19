import os
import logging
import requests
from ingestion.db import get_engine, execute_upsert

logger = logging.getLogger("fetch_fred_census")

# ----- configurable parameters -----
START_DATE = "2018-01-01"

FRED_SERIES = {
    "RSAFS":      "Total Retail and Food Services Sales",
    "RSGMS":      "General Merchandise Stores Sales",
    "RSFHFS":     "Furniture and Home Furnishings Stores Sales",
    "RSEAS":      "Electronics and Appliance Stores Sales",
    "RSDBS":      "Building Material and Garden Equipment Dealers Sales",
    "JTS4400JOL": "Job Openings: Retail Trade",
    "UMCSENT":    "University of Michigan: Consumer Sentiment",
    "DRCCLACBS":  "Delinquency Rate on Credit Card Loans",
}
# ------------------------------------

UPSERT_SQL = """
INSERT INTO raw.fred_observations (series_id, observation_date, value, ingested_at)
VALUES (:series_id, :observation_date, :value, CURRENT_TIMESTAMP)
ON CONFLICT (series_id, observation_date)
DO UPDATE SET
    value       = EXCLUDED.value,
    ingested_at = CURRENT_TIMESTAMP;
"""

def fetch_series(series_id: str, api_key: str, start_date: str = START_DATE) -> list[dict]:
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id":         series_id,
        "api_key":           api_key,
        "file_type":         "json",
        "observation_start": start_date,
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()

    records = []
    for obs in resp.json().get("observations", []):
        val_str = obs.get("value", ".")
        if val_str == ".":   # FRED uses "." for missing values
            continue
        records.append({
            "series_id":        series_id,
            "observation_date": obs["date"],
            "value":            float(val_str),
        })
    return records

def run():
    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        raise ValueError("FRED_API_KEY missing in environment.")

    engine = get_engine()
    total_rows = 0

    for series_id, desc in FRED_SERIES.items():
        logger.info(f"Fetching {series_id} ({desc})...")
        rows = fetch_series(series_id, api_key)
        inserted = execute_upsert(engine, UPSERT_SQL, rows)
        total_rows += inserted
        logger.info(f"  -> {inserted} rows upserted.")

    logger.info(f"FRED ingestion done. Total rows: {total_rows}")

if __name__ == "__main__":
    run()