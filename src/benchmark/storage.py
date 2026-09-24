import json
import os
import platform
import statistics
import time
from pathlib import Path

import pandas as pd
import psycopg

from src.config import DB

RESULT_COLUMNS = [
    'format', 'size_bytes', 'write_time_s',
    'full_read_median_s', 'full_read_row_count',
    'filtered_read_median_s', 'filtered_read_row_count',
    'repeats', 'measured_at_utc',
    'platform', 'python_version', 'cpu_count',
]


def _hw_context() -> dict:
    return {
        'platform': platform.platform(),
        'python_version': platform.python_version(),
        'cpu_count': os.cpu_count(),
    }


def _median_timed(fn, repeats: int):
    """Run fn() `repeats` times, return (median_seconds, last_row_count)."""
    durations = []
    row_count = None
    for _ in range(repeats):
        start = time.perf_counter()
        result = fn()
        durations.append(time.perf_counter() - start)
        row_count = len(result)
    return statistics.median(durations), row_count


def _connect():
    return psycopg.connect(
        host=DB['host'], port=DB['port'], dbname=DB['dbname'],
        user=DB['user'], password=DB['password'],
    )


def run_benchmark(curated_path, output_dir, repeats: int = 5):
    """Compare the same logical dataset in CSV, JSON Lines, Parquet, and PostgreSQL."""
    curated_path = Path(curated_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_parquet(curated_path)
    hw = _hw_context()
    measured_at = pd.Timestamp.utcnow().isoformat()
    results = []

    # --- CSV ---
    csv_path = output_dir / 'sales_order_lines.csv'
    start = time.perf_counter()
    df.to_csv(csv_path, index=False)
    csv_write_time = time.perf_counter() - start

    full_median, full_rows = _median_timed(lambda: pd.read_csv(csv_path), repeats)
    filt_median, filt_rows = _median_timed(
        lambda: pd.read_csv(csv_path).query("status == 'DELIVERED'"), repeats
    )
    results.append({
        'format': 'csv', 'size_bytes': csv_path.stat().st_size,
        'write_time_s': csv_write_time,
        'full_read_median_s': full_median, 'full_read_row_count': full_rows,
        'filtered_read_median_s': filt_median, 'filtered_read_row_count': filt_rows,
        'repeats': repeats, 'measured_at_utc': measured_at, **hw,
    })

    # --- JSON Lines ---
    jsonl_path = output_dir / 'sales_order_lines.jsonl'
    start = time.perf_counter()
    df.to_json(jsonl_path, orient='records', lines=True, date_format='iso')
    jsonl_write_time = time.perf_counter() - start

    def _read_jsonl():
        return pd.read_json(jsonl_path, lines=True)

    full_median, full_rows = _median_timed(_read_jsonl, repeats)
    filt_median, filt_rows = _median_timed(
        lambda: _read_jsonl().query("status == 'DELIVERED'"), repeats
    )
    results.append({
        'format': 'jsonl', 'size_bytes': jsonl_path.stat().st_size,
        'write_time_s': jsonl_write_time,
        'full_read_median_s': full_median, 'full_read_row_count': full_rows,
        'filtered_read_median_s': filt_median, 'filtered_read_row_count': filt_rows,
        'repeats': repeats, 'measured_at_utc': measured_at, **hw,
    })

    # --- Parquet (compressed, snappy) ---
    parquet_path = output_dir / 'sales_order_lines.parquet'
    start = time.perf_counter()
    df.to_parquet(parquet_path, index=False, compression='snappy')
    parquet_write_time = time.perf_counter() - start

    full_median, full_rows = _median_timed(lambda: pd.read_parquet(parquet_path), repeats)
    # Predicate pushdown: only DELIVERED row groups/pages need to be materialized.
    filt_median, filt_rows = _median_timed(
        lambda: pd.read_parquet(parquet_path, filters=[('status', '==', 'DELIVERED')]),
        repeats,
    )
    results.append({
        'format': 'parquet', 'size_bytes': parquet_path.stat().st_size,
        'write_time_s': parquet_write_time,
        'full_read_median_s': full_median, 'full_read_row_count': full_rows,
        'filtered_read_median_s': filt_median, 'filtered_read_row_count': filt_rows,
        'repeats': repeats, 'measured_at_utc': measured_at, **hw,
    })

    # --- PostgreSQL (already loaded in Goal 2; measure size + query time only) ---
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT pg_total_relation_size('curated.sales_order_lines')")
            pg_size = cur.fetchone()[0]

        def _pg_full():
            with conn.cursor() as c:
                c.execute("SELECT * FROM curated.sales_order_lines")
                return c.fetchall()

        def _pg_filtered():
            with conn.cursor() as c:
                c.execute("SELECT * FROM curated.sales_order_lines WHERE status = 'DELIVERED'")
                return c.fetchall()

        full_median, full_rows = _median_timed(_pg_full, repeats)
        filt_median, filt_rows = _median_timed(_pg_filtered, repeats)

    results.append({
        'format': 'postgresql', 'size_bytes': pg_size,
        'write_time_s': None,  # already loaded during Goal 2; not re-measured here
        'full_read_median_s': full_median, 'full_read_row_count': full_rows,
        'filtered_read_median_s': filt_median, 'filtered_read_row_count': filt_rows,
        'repeats': repeats, 'measured_at_utc': measured_at, **hw,
    })

    results_df = pd.DataFrame(results, columns=RESULT_COLUMNS)
    results_path = output_dir / 'benchmark_results.csv'
    results_df.to_csv(results_path, index=False)

    return results_df


def write_partitioned_parquet(df, output_dir):
    """Write Parquet partitioned by order_year/order_month."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    df = df.copy()
    ts = pd.to_datetime(df['order_timestamp'], utc=True)
    df['order_year'] = ts.dt.year
    df['order_month'] = ts.dt.month

    df.to_parquet(
        output_dir,
        index=False,
        partition_cols=['order_year', 'order_month'],
        compression='snappy',
    )
    return output_dir