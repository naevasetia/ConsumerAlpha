import logging
import pandas as pd
import yfinance as yf
from ingestion.db import get_engine, execute_upsert

logger = logging.getLogger("fetch_market")

# ----- configurable parameters -----
TICKERS = [
    # Broad retail
    "XRT",   # SPDR S&P Retail ETF

    # Consumer discretionary
    "XLY",   # Consumer Discretionary Select Sector ETF
    "VCR",   # Vanguard Consumer Discretionary ETF

    # Online retail
    "IBUY",  # Amplify Online Retail ETF
    "ONLN",  # ProShares Online Retail ETF

    # Home improvement & furnishings
    "XHB",   # SPDR S&P Homebuilders ETF
    "ITB",   # iShares US Home Construction ETF

    # Consumer staples (comparison)
    "XLP",   # Consumer Staples Select Sector ETF

    # Department stores & discount retail
    "RTH",   # VanEck Retail ETF
]
START_DATE = "2018-01-01"
# ------------------------------------

UPSERT_SQL = """
INSERT INTO raw.etf_daily_prices (ticker, trade_date, adj_close, volume, ingested_at)
VALUES (:ticker, :trade_date, :adj_close, :volume, CURRENT_TIMESTAMP)
ON CONFLICT (ticker, trade_date)
DO UPDATE SET
    adj_close   = EXCLUDED.adj_close,
    volume      = EXCLUDED.volume,
    ingested_at = CURRENT_TIMESTAMP;
"""

def run(start_date: str = START_DATE):
    engine = get_engine()

    for ticker in TICKERS:
        logger.info(f"Downloading {ticker}...")
        df = yf.download(ticker, start=start_date, progress=False, auto_adjust=True)
        if df.empty:
            logger.warning(f"No data returned for {ticker}")
            continue

        df = df.reset_index()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]

        records = []
        for _, row in df.iterrows():
            records.append({
                "ticker":     ticker,
                "trade_date": pd.to_datetime(row["Date"]).date(),
                "adj_close":  float(row["Close"]),
                "volume":     int(row["Volume"]),
            })

        inserted = execute_upsert(engine, UPSERT_SQL, records)
        logger.info(f"  -> {inserted} daily rows upserted for {ticker}.")

if __name__ == "__main__":
    run()