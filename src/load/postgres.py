import pandas as pd
import psycopg

from src.config import DB

CURATED_COLUMNS = [
    'order_id', 'customer_id', 'product_id', 'order_timestamp', 'quantity',
    'unit_price', 'discount_pct', 'status',
    'gross_amount', 'discount_amount', 'net_amount',
    'customer_email', 'customer_city', 'customer_tier',
    'product_name', 'product_category_name', 'product_category_department', 'product_brand',
    'source_updated_at', 'pipeline_run_id', 'processed_at_utc', 'record_hash',
]

UPSERT_SQL = f"""
INSERT INTO curated.sales_order_lines ({', '.join(CURATED_COLUMNS)})
VALUES ({', '.join(f'%({c})s' for c in CURATED_COLUMNS)})
ON CONFLICT (order_id) DO UPDATE SET
    {', '.join(f"{c} = EXCLUDED.{c}" for c in CURATED_COLUMNS if c != 'order_id')}
WHERE curated.sales_order_lines.record_hash IS DISTINCT FROM EXCLUDED.record_hash
"""


def _connect():
    return psycopg.connect(
        host=DB['host'], port=DB['port'], dbname=DB['dbname'],
        user=DB['user'], password=DB['password'],
    )


def upsert_curated(df: pd.DataFrame, run_id: str) -> int:
    """Load curated.sales_order_lines using rerun-safe UPSERT semantics.

    order_id is the conflict key. record_hash gates the update: rows whose
    business content hasn't changed since the last load are skipped.
    """
    missing = [c for c in CURATED_COLUMNS if c not in df.columns]
    if missing:
        raise KeyError(f"Curated DataFrame is missing expected columns: {missing}")

    records = df[CURATED_COLUMNS].to_dict(orient='records')
    for r in records:
        for k, v in r.items():
            if isinstance(v, pd.Timestamp):
                r[k] = v.to_pydatetime()

    if not records:
        return 0

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.executemany(UPSERT_SQL, records)
        conn.commit()

    return len(records)


def load_partition(df, year: int, month: int, run_id: str) -> int:
    """Load only a selected year/month partition and record audit.partition_loads."""
    raise NotImplementedError('Implement Goal 3 selected-partition load')