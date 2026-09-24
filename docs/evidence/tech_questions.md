1. Why is record_hash useful for rerun-safe loading, and which columns should not be included in it?
    A record_hash (often MD5 or SHA-256) creates a unique fingerprint for a row based on its business data. During an UPSERT, the database can simply compare the incoming hash against the existing hash. If they match, the row hasn't changed, and the pipeline can skip the expensive update operation (Change Data Capture).
    You must exclude pipeline metadata columns (like pipeline_run_id, processed_at_utc, or file_name) from the hash calculation. If you include them, the hash will change every time the pipeline runs, tricking the database into thinking every row is an "update" and completely defeating the purpose of the hash.

2. Why should raw data usually be preserved even when staging/curated outputs are sufficient for analytics?
    Raw data acts as the immutable "source of truth" (the Bronze layer in a Medallion architecture). If a bug is discovered in your transform logic months from now, or if business rules change (e.g., how you calculate net_amount), you can simply replay the pipeline from the raw data to rebuild the curated tables. If you delete the raw data, that historical context is lost forever, making disaster recovery and pipeline evolution impossible.

3. What is the difference between a data-quality rejection and a system exception?

    System Exception: The infrastructure or code failed (e.g., FileNotFoundError, database connection timeout, out-of-memory). The pipeline cannot proceed and must crash, turn red, and trigger engineering alerts.

    Data-Quality Rejection: The code executed perfectly, but the data itself violates business rules (e.g., negative quantities, unknown statuses like 'PACKED'). The pipeline should generally catch this, route the bad data to a Quarantine folder, and gracefully continue processing the valid data without crashing the system.

4. Why might Parquet outperform CSV for selected analytical workloads even if both contain the same rows?
    Parquet is a columnar storage format, whereas CSV is row-based. In analytical workloads (which typically select only a few specific columns, like summing gross_amount grouped by month), Parquet allows the engine to read only those specific columns from disk (column pruning). Furthermore, Parquet stores min/max statistics for chunks of data, allowing the query engine to completely skip over blocks of data that don't match a filter (predicate pushdown), whereas a CSV requires scanning the entire text file start to finish.

5. Why is a DAG that contains all transformation logic directly considered harder to maintain?
    If you write Pandas logic directly inside an Airflow DAG file using @task decorators, you tightly couple your business logic to your orchestrator. This makes the code impossible to run, debug, or unit-test locally without spinning up a full Dockerized Airflow environment. By delegating the logic to a CLI module (like src.cli), the DAG remains a lightweight, readable scheduling map, and developers can test the pipeline locally using standard Python commands.

6. How do retries interact with idempotency? Give an example where retries without idempotency cause damage.
    Retries automatically re-execute tasks that encounter transient failures. Idempotency guarantees that running a task one time or one hundred times results in the exact same final state.
    Example of damage: If a task uses a standard INSERT statement (not idempotent) and fails halfway through loading 10,000 rows, 5,000 rows are committed. When Airflow retries the task, it runs the INSERT again, loading 10,000 rows. You now have 15,000 rows, permanently corrupting your database with 5,000 duplicates.

7. What trade-off is introduced by partitioning too aggressively?
    Aggressive partitioning (e.g., partitioning by order_id or by day for a low-volume system) creates the "small file problem." You end up with thousands of tiny directories, each containing files that are only a few kilobytes. The I/O overhead of opening/closing files and the metadata overhead of scanning the directory tree will drastically outweigh any performance gained by query pruning, severely slowing down the system.

8. How would you adapt the pipeline if the source became an API or database instead of local files?
    Because of the pipeline's modular architecture, you would only need to rewrite the src/extract/ module. You would replace the local file reading logic with an API client (like requests) or a database connector (like psycopg2), and save the retrieved data to the data/raw/ directory. The transform, validate, and load modules, as well as the Airflow DAG, would remain 100% untouched because they expect to pick up data from the raw folder, regardless of how it got there.tech_questions.md
