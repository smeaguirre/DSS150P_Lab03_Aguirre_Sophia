import json
from pathlib import Path

import pandas as pd

from src.common.audit import utc_now_iso
from src.config import SETTINGS, path_for

ALLOWED_STATUSES = set(SETTINGS['quality']['allowed_order_statuses'])
MIN_QTY = SETTINGS['quality']['min_quantity']
MAX_QTY = SETTINGS['quality']['max_quantity']

QUARANTINE_COLUMNS = [
    'source_table', 'business_key', 'reason', 'raw_record',
    'pipeline_run_id', 'quarantined_at_utc',
]


def _quarantine_records(rows: pd.DataFrame, source_table: str, reason: str,
                         key_col: str, run_id: str) -> list[dict]:
    out = []
    for _, row in rows.iterrows():
        out.append({
            'source_table': source_table,
            'business_key': row.get(key_col),
            'reason': reason,
            'raw_record': json.dumps(row.to_dict(), default=str),
            'pipeline_run_id': run_id,
            'quarantined_at_utc': utc_now_iso(),
        })
    return out


def _dedupe_latest(df: pd.DataFrame, key_col: str, ts_col: str) -> pd.DataFrame:
    """Keep the row with the greatest ts_col per key_col."""
    return (
        df.sort_values(ts_col)
          .drop_duplicates(subset=[key_col], keep='last')
          .reset_index(drop=True)
    )


def _stage_customers(raw_dir: Path, run_id: str, quarantine: list[dict]) -> pd.DataFrame:
    df = pd.read_csv(raw_dir / 'customers.csv')

    df['updated_at'] = pd.to_datetime(df['updated_at'], utc=True, errors='coerce')
    df['created_at'] = pd.to_datetime(df['created_at'], utc=True, errors='coerce')

    bad_ts = df[df['updated_at'].isna()]
    if not bad_ts.empty:
        quarantine.extend(_quarantine_records(bad_ts, 'customers', 'unparseable_updated_at', 'customer_id', run_id))
        df = df[df['updated_at'].notna()]

    df = _dedupe_latest(df, 'customer_id', 'updated_at')

    df['email'] = df['email'].astype('string').str.strip().str.lower()
    df['has_missing_email'] = df['email'].isna() | (df['email'] == '')
    df['city'] = df['city'].astype('string').str.strip().str.title()

    df['pipeline_run_id'] = run_id
    df['staged_at_utc'] = utc_now_iso()
    return df.reset_index(drop=True)


def _stage_products(raw_dir: Path, run_id: str, quarantine: list[dict]) -> pd.DataFrame:
    with (raw_dir / 'products.json').open(encoding='utf-8') as f:
        raw = json.load(f)
    df = pd.DataFrame(raw)

    df['category_name'] = df['category'].apply(lambda c: c.get('name') if isinstance(c, dict) else None)
    df['category_department'] = df['category'].apply(lambda c: c.get('department') if isinstance(c, dict) else None)
    df = df.drop(columns=['category'])

    df['unit_price'] = pd.to_numeric(df['unit_price'], errors='coerce')
    df['updated_at'] = pd.to_datetime(df['updated_at'], utc=True, errors='coerce')

    bad_ts = df[df['updated_at'].isna()]
    if not bad_ts.empty:
        quarantine.extend(_quarantine_records(bad_ts, 'products', 'unparseable_updated_at', 'product_id', run_id))
        df = df[df['updated_at'].notna()]

    # Handles duplicate product_id rows (e.g. P0300 appearing twice with
    # different updated_at) by keeping only the most recent version.
    df = _dedupe_latest(df, 'product_id', 'updated_at')

    bad_price = df[df['unit_price'].isna() | (df['unit_price'] < 0)]
    if not bad_price.empty:
        quarantine.extend(_quarantine_records(bad_price, 'products', 'invalid_unit_price', 'product_id', run_id))
        df = df[df['unit_price'].notna() & (df['unit_price'] >= 0)]

    df['pipeline_run_id'] = run_id
    df['staged_at_utc'] = utc_now_iso()
    return df.reset_index(drop=True)


def _stage_orders(raw_dir: Path, run_id: str, quarantine: list[dict]) -> pd.DataFrame:
    df = pd.read_csv(raw_dir / 'orders.csv')

    df['order_timestamp'] = pd.to_datetime(df['order_timestamp'], utc=True, errors='coerce')
    df['updated_at'] = pd.to_datetime(df['updated_at'], utc=True, errors='coerce')
    df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce')
    df['unit_price'] = pd.to_numeric(df['unit_price'], errors='coerce')
    df['discount_pct'] = pd.to_numeric(df['discount_pct'], errors='coerce')

    bad_ts = df[df['order_timestamp'].isna() | df['updated_at'].isna()]
    if not bad_ts.empty:
        quarantine.extend(_quarantine_records(bad_ts, 'orders', 'unparseable_timestamp', 'order_id', run_id))
        df = df[df['order_timestamp'].notna() & df['updated_at'].notna()]

    df = _dedupe_latest(df, 'order_id', 'updated_at')

    bad_qty = df[df['quantity'].isna() | (df['quantity'] < MIN_QTY) | (df['quantity'] > MAX_QTY)]
    if not bad_qty.empty:
        quarantine.extend(_quarantine_records(bad_qty, 'orders', 'invalid_quantity', 'order_id', run_id))
        df = df[df['quantity'].notna() & (df['quantity'] >= MIN_QTY) & (df['quantity'] <= MAX_QTY)]

    bad_status = df[~df['status'].isin(ALLOWED_STATUSES)]
    if not bad_status.empty:
        quarantine.extend(_quarantine_records(bad_status, 'orders', 'invalid_status', 'order_id', run_id))
        df = df[df['status'].isin(ALLOWED_STATUSES)]

    bad_price = df[df['unit_price'].isna() | (df['unit_price'] < 0)]
    if not bad_price.empty:
        quarantine.extend(_quarantine_records(bad_price, 'orders', 'invalid_unit_price', 'order_id', run_id))
        df = df[df['unit_price'].notna() & (df['unit_price'] >= 0)]

    df['pipeline_run_id'] = run_id
    df['staged_at_utc'] = utc_now_iso()
    return df.reset_index(drop=True)


def build_staging(raw_dir, run_id: str):
    raw_dir = Path(raw_dir)
    quarantine: list[dict] = []

    staging = {
        'customers': _stage_customers(raw_dir, run_id, quarantine),
        'products': _stage_products(raw_dir, run_id, quarantine),
        'orders': _stage_orders(raw_dir, run_id, quarantine),
    }

    quarantine_df = pd.DataFrame(quarantine, columns=QUARANTINE_COLUMNS)

    staging_dir = path_for('staging_dir')
    staging_dir.mkdir(parents=True, exist_ok=True)
    for name, frame in staging.items():
        frame.to_parquet(staging_dir / f'{name}.parquet', index=False)

    quarantine_dir = path_for('quarantine_dir')
    quarantine_dir.mkdir(parents=True, exist_ok=True)
    quarantine_df.to_parquet(quarantine_dir / 'quarantine_staging.parquet', index=False)

    return staging, quarantine_df