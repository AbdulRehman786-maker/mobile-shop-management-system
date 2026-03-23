r"""
One-time data sync from local SQLite to PostgreSQL.

Usage (PowerShell):

    $env:TARGET_DATABASE_URL="postgresql://user:pass@host/db?sslmode=require"
    .\venv\Scripts\python.exe sync_sqlite_to_postgres.py

The script preserves primary keys and resets PostgreSQL sequences after import.
"""
from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from dotenv import load_dotenv
from sqlalchemy import MetaData, create_engine, text


ROOT = Path(__file__).resolve().parent
SQLITE_PATH = ROOT / "instance" / "mobile_shop.db"
TABLE_ORDER = [
    "users",
    "suppliers",
    "customers",
    "products",
    "purchases",
    "sales",
    "purchase_items",
    "sale_items",
    "inventory_logs",
]


def _normalize_postgres_url(url: str) -> str:
    split = urlsplit(url)
    query = [(key, value) for key, value in parse_qsl(split.query, keep_blank_values=True) if key not in {"sslmode", "channel_binding"}]
    cleaned_url = urlunsplit((split.scheme, split.netloc, split.path, urlencode(query), split.fragment))

    url = cleaned_url
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+pg8000://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+pg8000://", 1)
    return url


def main() -> None:
    load_dotenv()

    if not SQLITE_PATH.exists():
        raise FileNotFoundError(f"SQLite database not found: {SQLITE_PATH}")

    target_url = os.environ.get("TARGET_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not target_url:
        raise RuntimeError("Set TARGET_DATABASE_URL to your PostgreSQL connection string.")

    sqlite_engine = create_engine(f"sqlite:///{SQLITE_PATH}")
    postgres_engine = create_engine(_normalize_postgres_url(target_url))

    sqlite_meta = MetaData()
    sqlite_meta.reflect(bind=sqlite_engine)

    postgres_meta = MetaData()
    postgres_meta.reflect(bind=postgres_engine)

    missing = [table for table in TABLE_ORDER if table not in postgres_meta.tables]
    if missing:
        raise RuntimeError(
            "Target PostgreSQL database is missing tables. "
            f"Run migrations first. Missing: {', '.join(missing)}"
        )

    with sqlite_engine.connect() as source, postgres_engine.begin() as target:
        print("[1/4] clearing target tables")
        for table_name in reversed(TABLE_ORDER):
            target.execute(text(f'TRUNCATE TABLE "{table_name}" RESTART IDENTITY CASCADE'))

        print("[2/4] copying records")
        for table_name in TABLE_ORDER:
            rows = source.execute(text(f'SELECT * FROM "{table_name}"')).mappings().all()
            if not rows:
                print(f"  - {table_name}: 0 rows")
                continue

            target.execute(postgres_meta.tables[table_name].insert(), [dict(row) for row in rows])
            print(f"  - {table_name}: {len(rows)} rows")

        print("[3/4] resetting PostgreSQL sequences")
        for table_name in TABLE_ORDER:
            if "id" not in postgres_meta.tables[table_name].columns:
                continue

            target.execute(
                text(
                    """
                    SELECT setval(
                        pg_get_serial_sequence(:table_name, 'id'),
                        COALESCE((SELECT MAX(id) FROM "{table_name}"), 1),
                        COALESCE((SELECT MAX(id) FROM "{table_name}") IS NOT NULL, false)
                    )
                    """.replace("{table_name}", table_name)
                ),
                {"table_name": table_name},
            )

        print("[4/4] done")
        print("Local SQLite data successfully copied to PostgreSQL.")


if __name__ == "__main__":
    main()
