import argparse
import traceback

import pandas as pd

from src.config import PROJECT_ROOT, DB, SETTINGS, path_for
from src.common.audit import new_run_id
from src.extract.files import extract_sources
from src.transform.staging import build_staging
from src.transform.curated import build_curated
from src.load.postgres import (
    upsert_curated, start_pipeline_run, complete_pipeline_run, fail_pipeline_run,
)
from src.benchmark.storage import run_benchmark, write_partitioned_parquet
from src.load.postgres import load_partition


class PipelineStageError(Exception):
    """Wraps an exception with the stage it occurred in, for diagnosis."""
    def __init__(self, stage: str, original: Exception):
        self.stage = stage
        self.original = original
        super().__init__(f"[{stage}] {type(original).__name__}: {original}")


def _run_extract(run_id: str):
    try:
        raw_dir = extract_sources(run_id)
    except Exception as e:
        raise PipelineStageError('extract', e) from e
    print(f'run_id={run_id}')
    print(f'raw_dir={raw_dir}')
    return raw_dir


def _run_transform(run_id: str, raw_dir):
    try:
        staging, staging_quarantine = build_staging(raw_dir, run_id)
    except Exception as e:
        raise PipelineStageError('transform.staging', e) from e

    try:
        curated, curated_quarantine = build_curated(staging, run_id)
    except Exception as e:
        raise PipelineStageError('transform.curated', e) from e

    rows_staging = sum(len(f) for f in staging.values())
    rows_curated = len(curated)
    rows_quarantined = len(staging_quarantine) + len(curated_quarantine)

    for name, frame in staging.items():
        print(f'staging[{name}] rows={len(frame)}')
    print(f'curated rows={rows_curated}')
    print(f'quarantine rows={rows_quarantined}')

    return curated, rows_staging, rows_curated, rows_quarantined


def _run_load(run_id: str, curated: pd.DataFrame | None = None):
    if curated is None:
        curated = pd.read_parquet(path_for('curated_dir') / 'sales_order_lines.parquet')
    try:
        n = upsert_curated(curated, run_id)
    except Exception as e:
        raise PipelineStageError('load', e) from e
    print(f'upserted_rows={n}')


def main():
    parser = argparse.ArgumentParser(description='DSS150P modular pipeline')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('validate-env')
    sub.add_parser('extract')
    sub.add_parser('transform')
    sub.add_parser('load')
    sub.add_parser('validate')
    b = sub.add_parser('benchmark'); b.add_argument('--repeats', type=int, default=SETTINGS['storage_benchmark']['repeats'])
    p = sub.add_parser('load-partition'); p.add_argument('--year', type=int, required=True); p.add_argument('--month', type=int, required=True)
    sub.add_parser('run-all')
    args = parser.parse_args()

    if args.command == 'validate-env':
        print('PROJECT_ROOT=', PROJECT_ROOT)
        print('DB host/database=', DB['host'], DB['dbname'])
        print('Configured source=', SETTINGS['pipeline']['source_dir'])
        return

    if args.command == 'extract':
        run_id = new_run_id()
        _run_extract(run_id)
        return

    if args.command == 'transform':
        run_id = new_run_id()
        raw_dir = _run_extract(run_id)
        _run_transform(run_id, raw_dir)
        return

    if args.command == 'load':
        run_id = new_run_id()
        _run_load(run_id)
        return

    if args.command == 'benchmark':
        curated_path = path_for('curated_dir') / 'sales_order_lines.parquet'
        results = run_benchmark(curated_path, path_for('benchmark_dir'), repeats=args.repeats)
        print(results.to_string(index=False))

        curated_df = pd.read_parquet(curated_path)
        write_partitioned_parquet(curated_df, path_for('partition_dir'))
        print(f'partitioned dataset written to {path_for("partition_dir")}')
        return

    if args.command == 'load-partition':
        run_id = new_run_id()
        n = load_partition(path_for('partition_dir'), args.year, args.month, run_id)
        print(f'partition_rows_loaded={n}')
        return

    if args.command == 'run-all':
        run_id = new_run_id()
        start_pipeline_run(run_id)
        try:
            raw_dir = _run_extract(run_id)
            curated, rows_staging, rows_curated, rows_quarantined = _run_transform(run_id, raw_dir)
            _run_load(run_id, curated)
            complete_pipeline_run(run_id, rows_staging, rows_curated, rows_quarantined)
        except PipelineStageError as e:
            fail_pipeline_run(run_id, str(e))
            print(f'PIPELINE FAILED at stage={e.stage}')
            print(f'  cause: {type(e.original).__name__}: {e.original}')
            traceback.print_exc()
            raise SystemExit(1)
        return

    raise NotImplementedError(f'Wire command: {args.command}')


if __name__ == '__main__':
    main()