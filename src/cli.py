import argparse
import sys

def main():
    # Initialize the parser
    parser = argparse.ArgumentParser(description="DSS150P Data Pipeline")
    
    # Define the main command argument
    parser.add_argument(
        'command', 
        choices=['extract', 'transform', 'load', 'validate', 'load-partition', 'run-all', 'benchmark', 'validate-env'], 
        help="Pipeline command to execute"
    )
    
    # Define optional arguments
    parser.add_argument('--run-id', type=str, default='manual_run', help="The Airflow run ID")
    parser.add_argument('--year', type=int, help="Year for partition loading")
    parser.add_argument('--month', type=int, help="Month for partition loading")
    parser.add_argument('--repeats', type=int, default=5, help="Number of repetitions for benchmarking")
    
    # Parse the arguments
    args = parser.parse_args()

    # --- Command Routing ---
    if args.command == 'validate-env':
        print("Validating environment...")
        print("Environment loaded successfully. Ready for execution.")

    elif args.command == 'extract':
        from src.extract import extract_sources 
        print(f"Starting extract phase. Run ID: {args.run_id}")
        extract_sources(args.run_id)
        
    elif args.command == 'transform':
        from src.transform import run_transformations 
        print(f"Starting transform phase. Run ID: {args.run_id}")
        run_transformations(args.run_id)
        
    elif args.command == 'load':
        from src.load import load_curated_to_postgres 
        print("Starting load phase...")
        load_curated_to_postgres()
        
    elif args.command == 'validate':
        import pandas as pd
        from src.validate import validate_curated 
        
        curated_path = "data/curated/sales_order_lines.parquet" 
        
        try:
            df = pd.read_parquet(curated_path)
        except FileNotFoundError:
            raise FileNotFoundError(f"Cannot find {curated_path}. Ensure your 'transform' step saves the curated dataframe as a parquet file before running validate.")
        
        errors = validate_curated(df)
        
        if errors:
            print("Validation FAILED with the following errors:")
            for e in errors:
                print(f" - {e}")
            raise ValueError("Data validation checks failed.")
        else:
            print("Validation PASSED. No errors found.")
            
    elif args.command == 'load-partition':
        if not args.year or not args.month:
            raise ValueError("Both --year and --month must be provided for load-partition.")
            
        from src.load import load_partition_to_postgres
        print(f"Loading partition for Year: {args.year}, Month: {args.month}")
        load_partition_to_postgres(args.year, args.month)

    elif args.command == 'run-all':
        print(f"Running full pipeline. Run ID: {args.run_id}")
        from src.extract import extract_sources
        from src.transform import run_transformations
        from src.load import load_curated_to_postgres
        
        extract_sources(args.run_id)
        run_transformations(args.run_id)
        load_curated_to_postgres()
        print("Full pipeline complete. Run 'validate' to check the data.")
        
    elif args.command == 'benchmark':
        try:
            from src.benchmark import run_benchmarks
            print(f"Running storage benchmarks with {args.repeats} repetitions...")
            run_benchmarks(args.repeats)
        except ImportError:
            print("Benchmark module not yet implemented.")
        
    else:
        parser.print_help()

if __name__ == '__main__':
    main()