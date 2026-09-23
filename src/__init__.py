import pandas as pd

def validate_curated(df: pd.DataFrame) -> list[str]:
    """Return a list of human-readable validation errors."""
    errors = []

    # 1. order_id uniqueness/non-null
    if df['order_id'].isnull().any():
        errors.append("Validation Error: Null values found in business key 'order_id'.")
    if df['order_id'].duplicated().any():
        errors.append("Validation Error: Duplicate values found in 'order_id'.")

    # 2. quantity range (1 to 20 based on lab spec)
    if not df['quantity'].between(1, 20).all():
        errors.append("Validation Error: 'quantity' contains values outside the allowed range of 1-20.")

    # 3. nonnegative amounts
    amount_columns = ['gross_amount', 'discount_amount', 'net_amount']
    for col in amount_columns:
        if col in df.columns and (df[col] < 0).any():
            errors.append(f"Validation Error: Negative monetary values found in '{col}'.")

    # 4. allowed statuses
    allowed_statuses = {'PENDING', 'SHIPPED', 'DELIVERED', 'CANCELLED'} 
    if not df['status'].isin(allowed_statuses).all():
        errors.append("Validation Error: Unrecognized 'status' values found.")

    # 5. required audit fields
    audit_fields = ['source_updated_at', 'pipeline_run_id', 'processed_at_utc', 'record_hash']
    missing_fields = [f for f in audit_fields if f not in df.columns]
    if missing_fields:
        errors.append(f"Validation Error: Missing required audit columns: {missing_fields}")
    
    for col in audit_fields:
        if col in df.columns and df[col].isnull().any():
            errors.append(f"Validation Error: Null values found in audit column '{col}'.")

    return errors