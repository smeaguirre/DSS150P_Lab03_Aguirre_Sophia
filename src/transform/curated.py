import json

import pandas as pd

from src.common.audit import record_hash as compute_record_hash
from src.common.audit import utc_now_iso
from src.config import path_for

HASH_KEYS = [
    'order_id', 'customer_id', 'product_id', 'order_timestamp',
    'quantity', 'unit_price', 'discount_pct', 'status',
    'gross_amount', 'discount_amount', 'net_amount',
]

QUARANTINE_COLUMNS = [
    'source_table', 'business_key', 'reason', 'raw_record',
    'pipeline_run_id', 'quarantined_at_utc',
]


def _quarantine_orphans(rows: pd.DataFrame, reason: str, run_id: str) -> list[dict]:
    out = []
    for _, row in rows.iterrows():
        out.append({
            'source_table': 'curated_join',
            'business_key': row.get('order_id'),
            'reason': reason,
            'raw_record': json.dumps(row.to_dict(), default=str),
            'pipeline_run_id': run_id,
            'quarantined_at_utc': utc_now_iso(),
        })
    return out


def _prefix_columns(df: pd.DataFrame, key_col: str, prefix: str) -> pd.DataFrame:
    """Prefix every column except the join key, avoiding double-prefixing
    columns (like customer_tier) that already carry the prefix."""
    rename_map = {
        c: c if c == key_col or c.startswith(prefix) else f'{prefix}{c}'
        for c in df.columns
    }
    return df.rename(columns=rename_map)


def build_curated(staging: dict, run_id: str):
    orders = staging['orders'].copy()
    customers = _prefix_columns(staging['customers'], 'customer_id', 'customer_')
    products = _prefix_columns(staging['products'], 'product_id', 'product_')

    quarantine_records: list[dict] = []

    known_customers = customers['customer_id']
    known_products = products['product_id']

    missing_customer = orders[~orders['customer_id'].isin(known_customers)]
    if not missing_customer.empty:
        quarantine_records.extend(_quarantine_orphans(missing_customer, 'orphan_customer_reference', run_id))

    missing_product = orders[~orders['product_id'].isin(known_products)]
    if not missing_product.empty:
        quarantine_records.extend(_quarantine_orphans(missing_product, 'orphan_product_reference', run_id))

    valid_orders = orders[
        orders['customer_id'].isin(known_customers)
        & orders['product_id'].isin(known_products)
    ].copy()

    curated = valid_orders.merge(customers, on='customer_id', how='left') \
                           .merge(products, on='product_id', how='left')

    curated['gross_amount'] = curated['quantity'] * curated['unit_price']
    curated['discount_amount'] = curated['gross_amount'] * curated['discount_pct']
    curated['net_amount'] = curated['gross_amount'] - curated['discount_amount']

    curated['source_updated_at'] = curated['updated_at']
    curated['pipeline_run_id'] = run_id
    curated['processed_at_utc'] = utc_now_iso()

    curated['record_hash'] = curated.apply(
        lambda r: compute_record_hash(r.to_dict(), HASH_KEYS), axis=1
    )
    curated = curated.reset_index(drop=True)

    quarantine_df = pd.DataFrame(quarantine_records, columns=QUARANTINE_COLUMNS)

    curated_dir = path_for('curated_dir')
    curated_dir.mkdir(parents=True, exist_ok=True)
    curated.to_parquet(curated_dir / 'sales_order_lines.parquet', index=False)

    quarantine_dir = path_for('quarantine_dir')
    quarantine_dir.mkdir(parents=True, exist_ok=True)
    quarantine_df.to_parquet(quarantine_dir / 'quarantine_curated.parquet', index=False)

    return curated, quarantine_df