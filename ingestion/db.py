import os
import logging
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

def get_engine():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL is not set in environment variables.")
    return create_engine(db_url, pool_pre_ping=True)

def execute_upsert(engine, sql: str, records: list[dict]):
    if not records:
        return 0
    with engine.begin() as conn:
        conn.execute(text(sql), records)
    return len(records)