`uv pip install -r requirements.txt
Resolved 12 packages in 932ms
Prepared 12 packages in 10.28s
Installed 12 packages in 194ms
 + numpy==2.4.6
 + pandas==2.2.3
 + psycopg==3.2.3
 + psycopg-binary==3.2.3
 + pyarrow==17.0.0
 + python-dateutil==2.9.0.post0
 + python-dotenv==1.0.1
 + pytz==2026.3.post1
 + pyyaml==6.0.2
 + six==1.17.0
 + typing-extensions==4.16.0
 + tzdata==2026.4

python -m src.cli validate-env
PROJECT_ROOT= /Users/urielle.zach/dss150p-lab03-starter
DB host/database= localhost dss150p
Configured source= data/source

[+] Building 3.3s (13/13) FINISHED                                                                                           
 => [internal] load local bake definitions                                                                              0.0s
 => => reading from stdin 571B                                                                                          0.0s
 => [internal] load build definition from Dockerfile                                                                    0.0s
 => => transferring dockerfile: 283B                                                                                    0.0s
 => [internal] load metadata for docker.io/library/python:3.11-slim                                                     2.0s
 => [auth] library/python:pull token for registry-1.docker.io                                                           0.0s
 => [internal] load .dockerignore                                                                                       0.0s
 => => transferring context: 2B                                                                                         0.0s
 => [1/5] FROM docker.io/library/python:3.11-slim@sha256:da047cb8f9d1d98e5c070f5300ba9f7274e33b8fc0e5be5ed88740aed1b95  0.1s
 => => resolve docker.io/library/python:3.11-slim@sha256:da047cb8f9d1d98e5c070f5300ba9f7274e33b8fc0e5be5ed88740aed1b95  0.1s
 => [internal] load build context                                                                                       0.2s
 => => transferring context: 102.50kB                                                                                   0.2s
 => CACHED [2/5] WORKDIR /app                                                                                           0.0s
 => CACHED [3/5] COPY requirements.txt /app/requirements.txt                                                            0.0s
 => CACHED [4/5] RUN pip install --no-cache-dir -r /app/requirements.txt                                                0.0s
 => CACHED [5/5] COPY . /app                                                                                            0.0s
 => exporting to image                                                                                                  0.2s
 => => exporting layers                                                                                                 0.0s
 => => exporting manifest sha256:87eda9fa62d31f21ae7d876004ac9d74f4a700be4ab0c3b45909aadbd3caf4c6                       0.0s
 => => exporting config sha256:5eda2849d9398f2ead9d5f6babe181952833168dd2bbbdd4d18966627c336dfa                         0.0s
 => => exporting attestation manifest sha256:ce8a03c28c56195e928daafe749a8ffdb123169ba41bb1c13c91bedf5cee5481           0.0s
 => => exporting manifest list sha256:96c78c3a3a09030d3721a4a0947a798eb7e9866add2a9c2e36bdce5b5f9eb0a2                  0.0s
 => => naming to docker.io/library/dss150p-lab03-starter-pipeline:latest                                                0.0s
 => => unpacking to docker.io/library/dss150p-lab03-starter-pipeline:latest                                             0.0s
 => resolving provenance for metadata file                                                                              0.0s
[+] Building 1/1
 ✔ dss150p-lab03-starter-pipeline  Built                                                                                0.0s 
v
docker exec -it dss150p-postgres psql -U dss150p -d dss150p -c "\dn"
       List of schemas
  Name   |       Owner       
---------+-------------------
 audit   | dss150p
 curated | dss150p
 public  | pg_database_owner
 staging | dss150p
(4 rows)

docker exec -it dss150p-postgres psql -U dss150p -d dss150p -c "\d curated.*"
                       Table "curated.sales_order_lines"
      Column       |           Type           | Collation | Nullable | Default 
-------------------+--------------------------+-----------+----------+---------
 order_id          | text                     |           | not null | 
 customer_id       | text                     |           | not null | 
 product_id        | text                     |           | not null | 
 order_timestamp   | timestamp with time zone |           | not null | 
 customer_city     | text                     |           |          | 
 customer_tier     | text                     |           |          | 
 product_name      | text                     |           |          | 
 category          | text                     |           |          | 
 brand             | text                     |           |          | 
 quantity          | integer                  |           | not null | 
 unit_price        | numeric(14,2)            |           | not null | 
 discount_pct      | numeric(6,4)             |           | not null | 
 gross_amount      | numeric(16,2)            |           | not null | 
 discount_amount   | numeric(16,2)            |           | not null | 
 net_amount        | numeric(16,2)            |           | not null | 
 status            | text                     |           | not null | 
 source_updated_at | timestamp with time zone |           | not null | 
 pipeline_run_id   | text                     |           | not null | 
 processed_at_utc  | timestamp with time zone |           | not null | 
 record_hash       | text                     |           | not null | 
Indexes:
    "sales_order_lines_pkey" PRIMARY KEY, btree (order_id)

Index "curated.sales_order_lines_pkey"
  Column  | Type | Key? | Definition 
----------+------+------+------------
 order_id | text | yes  | order_id
primary key, btree, for table "curated.sales_order_lines"

git log --oneline --decorate -5
fae7a0d (HEAD -> goal1-reproducible-environment) feat: add reproducible pipeline environment
3f0efc0 (origin/main, origin/HEAD, main) Update staging.py
366f71f Update curated.py
0ecc06d Update postgres.py
0ff7730 Update TODO comments for clarity and goals

python -m src.cli run-all
run_id=run_20260923T105608Z_39017d58
raw_dir=/Users/urielle.zach/dss150p-lab03-starter/data/raw/run_id=run_20260923T105608Z_39017d58
staging[customers] rows=3000
staging[products] rows=599
staging[orders] rows=49998
curated rows=49897
quarantine rows=104
upserted_rows=49897

python -m src.cli load
upserted_rows=49897

python -m src.cli load
upserted_rows=49897

docker exec -it dss150p-postgres psql -U dss150p -d dss150p -c "SELECT COUNT(*) total, COUNT(DISTINCT order_id)
distinct_orders FROM curated.sales_order_lines;"
 total | distinct_orders 
-------+-----------------
 49897 |           49897
(1 row)

python -m src.cli benchmark
    format  size_bytes  write_time_s  full_read_median_s  full_read_row_count  filtered_read_median_s  filtered_read_row_count  repeats                  measured_at_utc                       platform python_version  cpu_count
       csv    18170725      1.422150            0.437969                49897                0.342399                     8355        5 2026-09-23T11:21:57.873714+00:00 macOS-13.7.4-x86_64-i386-64bit        3.11.14          4
     jsonl    35248095      1.367786            1.723388                49897                1.120481                     8355        5 2026-09-23T11:21:57.873714+00:00 macOS-13.7.4-x86_64-i386-64bit        3.11.14          4
   parquet     5915493      0.184070            0.125067                49897                0.033575                     8355        5 2026-09-23T11:21:57.873714+00:00 macOS-13.7.4-x86_64-i386-64bit        3.11.14          4
postgresql    16564224           NaN            0.786810                49897                0.107911                     8355        5 2026-09-23T11:21:57.873714+00:00 macOS-13.7.4-x86_64-i386-64bit        3.11.14          4
partitioned dataset written to /Users/urielle.zach/dss150p-lab03-starter/data/partitioned

cat data/benchmarks/benchmark_results.csv
format,size_bytes,write_time_s,full_read_median_s,full_read_row_count,filtered_read_median_s,filtered_read_row_count,repeats,measured_at_utc,platform,python_version,cpu_count
csv,18170725,1.422149519999948,0.4379693250002674,49897,0.3423992179996276,8355,5,2026-09-23T11:21:57.873714+00:00,macOS-13.7.4-x86_64-i386-64bit,3.11.14,4
jsonl,35248095,1.367786318999606,1.7233880750000026,49897,1.1204808989996309,8355,5,2026-09-23T11:21:57.873714+00:00,macOS-13.7.4-x86_64-i386-64bit,3.11.14,4
parquet,5915493,0.1840699530002894,0.12506658599977527,49897,0.033574597000551876,8355,5,2026-09-23T11:21:57.873714+00:00,macOS-13.7.4-x86_64-i386-64bit,3.11.14,4
postgresql,16564224,,0.7868100969999432,49897,0.1079109830006928,8355,5,2026-09-23T11:21:57.873714+00:00,macOS-13.7.4-x86_64-i386-64bit,3.11.14,4

find data/partitioned -maxdepth 2 -type d | sort
data/partitioned
data/partitioned/order_year=2025
data/partitioned/order_year=2025/order_month=1
data/partitioned/order_year=2025/order_month=10
data/partitioned/order_year=2025/order_month=11
data/partitioned/order_year=2025/order_month=12
data/partitioned/order_year=2025/order_month=2
data/partitioned/order_year=2025/order_month=3
data/partitioned/order_year=2025/order_month=4
data/partitioned/order_year=2025/order_month=5
data/partitioned/order_year=2025/order_month=6
data/partitioned/order_year=2025/order_month=7
data/partitioned/order_year=2025/order_month=8
data/partitioned/order_year=2025/order_month=9
data/partitioned/order_year=2026
data/partitioned/order_year=2026/order_month=1
data/partitioned/order_year=2026/order_month=2
data/partitioned/order_year=2026/order_month=3
data/partitioned/order_year=2026/order_month=4
data/partitioned/order_year=2026/order_month=5
data/partitioned/order_year=2026/order_month=6
data/partitioned/order_year=2026/order_month=7
data/partitioned/order_year=2026/order_month=8
data/partitioned/order_year=2026/order_month=9

python -m src.cli load-partition --year 2026 --month 5
partition_rows_loaded=2500

 partition_key |         loaded_at_utc         | row_count |        pipeline_run_id        
---------------+-------------------------------+-----------+-------------------------------
 2026-05       | 2026-09-23 11:23:38.717807+00 |      2500 | run_20260923T112337Z_e2b7a477
(1 row)

python -m src.cli load-partition --year 2026 --month 5
partition_rows_loaded=2500

docker exec -it dss150p-postgres psql -U dss150p -d dss150p -c "SELECT * FROM audit.partition_loads;"
docker exec -it dss150p-postgres psql -U dss150p -d dss150p -c "SELECT COUNT(*) FROM curated.sales_order_lines;"
 partition_key |         loaded_at_utc         | row_count |        pipeline_run_id        
---------------+-------------------------------+-----------+-------------------------------
 2026-05       | 2026-09-23 11:24:04.094617+00 |      2500 | run_20260923T112403Z_e983f323
(1 row)

 count 
-------
 49897
(1 row)






-----------------------------------------------------------------------------------------------------------------------
python --version
Python 3.14.6

python -m src.cli validate-env
Validating environment...
Environment loaded successfully. Ready for execution.

docker compose build pipeline && docker compose ps
[+] Building 114.2s (13/13) FINISHED                                                                                                                                   
 => [internal] load local bake definitions                                                                                                                        0.0s
 => => reading from stdin 571B                                                                                                                                    0.0s
 => [internal] load build definition from Dockerfile                                                                                                              0.1s
 => => transferring dockerfile: 283B                                                                                                                              0.0s
 => [internal] load metadata for docker.io/library/python:3.11-slim                                                                                               3.8s
 => [auth] library/python:pull token for registry-1.docker.io                                                                                                     0.0s
 => [internal] load .dockerignore                                                                                                                                 0.0s
 => => transferring context: 2B                                                                                                                                   0.0s
 => [1/5] FROM docker.io/library/python:3.11-slim@sha256:da047cb8f9d1d98e5c070f5300ba9f7274e33b8fc0e5be5ed88740aed1b95ba9                                         0.1s
 => => resolve docker.io/library/python:3.11-slim@sha256:da047cb8f9d1d98e5c070f5300ba9f7274e33b8fc0e5be5ed88740aed1b95ba9                                         0.1s
 => [internal] load build context                                                                                                                                22.2s
 => => transferring context: 355.17MB                                                                                                                            22.2s
 => CACHED [2/5] WORKDIR /app                                                                                                                                     0.0s
 => [3/5] COPY requirements.txt /app/requirements.txt                                                                                                             2.9s
 => [4/5] RUN pip install --no-cache-dir -r /app/requirements.txt                                                                                                32.6s
 => [5/5] COPY . /app                                                                                                                                             4.5s 
 => exporting to image                                                                                                                                           46.2s 
 => => exporting layers                                                                                                                                          30.4s 
 => => exporting manifest sha256:d86f111aee2d8dd7387443fe6763532d507c40da0dfc8c30f5dba7c49be463a8                                                                 0.2s 
 => => exporting config sha256:c443572c1b3f6f3e5c9efcee7f24f8be915e125cf549e3ca5e275864814f6a74                                                                   0.0s 
 => => exporting attestation manifest sha256:2fdaeb7560254dc9413400a19cafd34062cbd8fdb9ad30ed143f44c5448153d3                                                     0.0s 
 => => exporting manifest list sha256:705c469dede51826c066b604cf06b1e16926bd328c922a437a680b38f3e3598d                                                            0.0s
 => => naming to docker.io/library/dss150p-lab03-starter-pipeline:latest                                                                                          0.0s
 => => unpacking to docker.io/library/dss150p-lab03-starter-pipeline:latest                                                                                      15.3s
 => resolving provenance for metadata file                                                                                                                        0.2s
[+] Building 1/1
 ✔ dss150p-lab03-starter-pipeline  Built                                                                                                                          0.0s 
NAME                        IMAGE                                     COMMAND                  SERVICE             CREATED        STATUS                    PORTS
dss150p-airflow-scheduler   dss150p-lab03-starter-airflow-scheduler   "/usr/bin/dumb-init …"   airflow-scheduler   27 hours ago   Up 14 minutes             8080/tcp
dss150p-airflow-webserver   dss150p-lab03-starter-airflow-webserver   "/usr/bin/dumb-init …"   airflow-webserver   27 hours ago   Up 14 minutes (healthy)   0.0.0.0:8080->8080/tcp, [::]:8080->8080/tcp
dss150p-postgres            postgres:16                               "docker-entrypoint.s…"   postgres            27 hours ago   Up 23 hours (healthy)     0.0.0.0:5432->5432/tcp, [::]:5432->5432/tcp

python -m src.cli run-all
Running full pipeline. Run ID: manual_run
Extracting data from source... Run ID: manual_run
Transforming data... Run ID: manual_run
Loading curated data into PostgreSQL...
Full pipeline complete. Run 'validate' to check the data.

python -m src.cli load
Starting load phase...
Loading curated data into PostgreSQL...

python -m src.cli load
Starting load phase...
Loading curated data into PostgreSQL...

docker exec -it dss150p-postgres psql -U dss150p -d dss150p -c \
  "SELECT COUNT(*) total, COUNT(DISTINCT order_id) distinct_orders FROM curated.sales_order_lines;"
 total | distinct_orders 
-------+-----------------
 49897 |           49897
(1 row)

docker exec -it dss150p-postgres psql -U dss150p -d dss150p -c \
  "SELECT DISTINCT pipeline_run_id FROM curated.sales_order_lines WHERE pipeline_run_id LIKE 'manual__%' OR pipeline_run_id LIKE 'scheduled__%' ORDER BY 1 DESC LIMIT 5;"
           pipeline_run_id            
--------------------------------------
 scheduled__2026-09-22T02:00:00+00:00
(1 row)


