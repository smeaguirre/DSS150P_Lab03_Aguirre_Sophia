import argparse

import pandas as pd

from src.config import PROJECT_ROOT, DB, SETTINGS, path_for
from src.common.audit import new_run_id
from src.extract.files import extract_sources
from src.transform.staging import build_staging
from src.transform.curated import build_curated
from src.load.postgres import upsert_curated


def _run_extract():
    run_id = new_run_id()
    raw_dir = extract_sources(run_id)
    print(f'run_id={run_id}')
    print(f'raw_dir={raw_dir}')
    return run_id, raw_dir


def _run_transform(run_id, raw_dir):
    staging, staging_quarantine = build_staging(raw_dir, run_id)
    curated, curated_quarantine = build_curated(staging, run_id)
    for name, frame in staging.items():
        print(f'staging[{name}] rows={len(frame)}')
    print(f'curated rows={len(curated)}')
    print(f'quarantine rows={len(staging_quarantine) + len(curated_quarantine)}')
    return curated


def _run_load(curated: pd.DataFrame | None = None):
    if curated is None:
        curated = pd.read_parquet(path_for('curated_dir') / 'sales_order_lines.parquet')
    run_id = new_run_id()
    n = upsert_curated(curated, run_id)
    print(f'upserted_rows={n}')


def main():
    parser = argparse.ArgumentParser(description='DSS150P modular pipeline')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('validate-env')
    sub.add_parser('extract')
    sub.add_parser('transform')
    sub.add_parser('load')
    sub.add_parser('validate')
    b = sub.add_parser('benchmark'); b.add_argument('--repeats', type=int, default=5)
    p = sub.add_parser('load-partition'); p.add_argument('--year', type=int, required=True); p.add_argument('--month', type=int, required=True)
    sub.add_parser('run-all')
    args = parser.parse_args()

    if args.command == 'validate-env':
        print('PROJECT_ROOT=', PROJECT_ROOT)
        print('DB host/database=', DB['host'], DB['dbname'])
        print('Configured source=', SETTINGS['pipeline']['source_dir'])
        return

    if args.command == 'extract':
        _run_extract()
        return

    if args.command == 'transform':
        run_id, raw_dir = _run_extract()
        _run_transform(run_id, raw_dir)
        return

    if args.command == 'load':
        _run_load()
        return

    if args.command == 'run-all':
        run_id, raw_dir = _run_extract()
        curated = _run_transform(run_id, raw_dir)
        _run_load(curated)
        return

    raise NotImplementedError(f'Wire command: {args.command}')

if __name__ == '__main__':
    main()