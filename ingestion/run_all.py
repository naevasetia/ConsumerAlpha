import sys
import logging
from ingestion import fetch_fred_census, fetch_trends, fetch_reddit, fetch_market

logger = logging.getLogger("run_all")

def main():
    incremental = "--incremental" in sys.argv
    logger.info(f"Starting ingestion (incremental={incremental})...")

    fetch_fred_census.run()
    fetch_trends.run()
    fetch_reddit.run(lookback_days=21 if incremental else 1800)
    fetch_market.run()

    logger.info("All ingestion jobs done.")

if __name__ == "__main__":
    main()