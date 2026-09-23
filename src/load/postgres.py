import pandas as pd
import psycopg

from src.config import DB
from datetime import datetime, timezone

# Matches curated.sales_order_lines column order exactly.
CURATED_COLUMNS = [
    'order_id', 'customer_id', 'product_id', 'order_timestamp',
    'customer_city', 'customer_tier', 'product_name', 'category', 'brand',
    'quantity', 'unit_price', 'discount_pct',
    'gross_amount', 'discount_amount', 'net_amount', 'status',
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

def start_pipeline_run(run_id: str) -> None:
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO audit.pipeline_runs
                    (pipeline_run_id, started_at_utc, status)
                VALUES (%s, %s, 'RUNNING')
                ON CONFLICT (pipeline_run_id) DO NOTHING
                """,
                (run_id, datetime.now(timezone.utc)),
            )
        conn.commit()


def complete_pipeline_run(run_id: str, rows_staging: int, rows_curated: int,
                           rows_quarantined: int) -> None:
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE audit.pipeline_runs
                SET completed_at_utc = %s,
                    status = 'SUCCESS',
                    rows_staging = %s,
                    rows_curated = %s,
                    rows_quarantined = %s
                WHERE pipeline_run_id = %s
                """,
                (datetime.now(timezone.utc), rows_staging, rows_curated,
                 rows_quarantined, run_id),
            )
        conn.commit()


def fail_pipeline_run(run_id: str, message: str) -> None:
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE audit.pipeline_runs
                SET completed_at_utc = %s,
                    status = 'FAILED',
                    message = %s
                WHERE pipeline_run_id = %s
                """,
                (datetime.now(timezone.utc), message[:2000], run_id),
            )
        conn.commit()

def load_partition(partition_dir, year: int, month: int, run_id: str) -> int:
    """Load only a selected year/month partition and record audit.partition_loads."""
    import pandas as pd
    from pathlib import Path

    partition_dir = Path(partition_dir)
    target = partition_dir / f'order_year={year}' / f'order_month={month}'
    if not target.exists():
        raise FileNotFoundError(f"No partition found at {target}")

    df = pd.read_parquet(target)
    # partition_cols are dropped from the file contents on write; restore them
    # since they're needed for the upsert payload's completeness/traceability.
    df['order_year'] = year
    df['order_month'] = month

    n = upsert_curated(df, run_id)

    partition_key = f"{year}-{month:02d}"
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO audit.partition_loads
                    (partition_key, loaded_at_utc, row_count, pipeline_run_id)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (partition_key) DO UPDATE SET
                    loaded_at_utc = EXCLUDED.loaded_at_utc,
                    row_count = EXCLUDED.row_count,
                    pipeline_run_id = EXCLUDED.pipeline_run_id
                """,
                (partition_key, datetime.now(timezone.utc), n, run_id),
            )
        conn.commit()

    return n