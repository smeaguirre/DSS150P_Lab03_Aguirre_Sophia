from pathlib import Path
import shutil
from src.config import path_for

SOURCE_FILES = ["customers.csv", "products.json", "orders.csv"]


def extract_sources(run_id: str) -> Path:
    """Copy immutable source snapshots into a run-specific raw directory."""
    source_dir = path_for('source_dir')
    raw_root = path_for('raw_dir')
    run_dir = raw_root / f"run_id={run_id}"
    run_dir.mkdir(parents=True, exist_ok=True)

    for filename in SOURCE_FILES:
        src_path = source_dir / filename
        if not src_path.exists():
            raise FileNotFoundError(f"Missing source file: {src_path}")
        shutil.copy2(src_path, run_dir / filename)

    return run_dir