# DAGs, requirements.txt, and Plugins — MWAA Environment Deployer

Deep reference on S3 DAG bucket structure, requirements.txt version
constraints and Python compatibility, plugin ZIP management, DAG upload
lifecycle, startup scripts, and Airflow configuration overrides. Loaded
on demand by the skill — kept out of the main SKILL.md body so the
provisioning procedure stays scannable.

## S3 DAG bucket structure

```text
s3://my-mwaa-bucket/
  ├── dags/
  │     ├── etl_pipeline.py
  │     ├── daily_report.py
  │     └── data_quality_check.py
  ├── requirements.txt          (exact version-pinned packages)
  ├── plugins/
  │     └── plugins.zip         (custom Airflow plugins)
  └── startup_script.sh         (optional: runs at worker startup)
```

### DAGs folder

The `/dags` folder contains Python files with Airflow DAG definitions.
MWAA scans this folder periodically (every 30 seconds by default,
configurable via `scheduler.dag_dir_list_interval`).

```python
# Example DAG: etl_pipeline.py
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime

with DAG(
    dag_id="etl_pipeline",
    schedule="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
) as dag:
    extract = PythonOperator(
        task_id="extract",
        python_callable=extract_data,
    )
    transform = PythonOperator(
        task_id="transform",
        python_callable=transform_data,
    )
    load = PythonOperator(
        task_id="load",
        python_callable=load_data,
    )
    extract >> transform >> load
```

### Uploading DAGs

```bash
# Upload a single DAG
aws s3 cp etl_pipeline.py s3://my-mwaa-bucket/dags/etl_pipeline.py

# Upload all DAGs from a local directory
aws s3 sync ./dags/ s3://my-mwaa-bucket/dags/

# MWAA detects new DAGs within 30 seconds of upload
```

### Bucket versioning

Enable S3 bucket versioning for DAG rollback:

```bash
aws s3api put-bucket-versioning \
  --bucket my-mwaa-bucket \
  --versioning-configuration Status=Enabled
```

This lets you roll back to a previous DAG version if a new upload
breaks the environment.

## requirements.txt

### Exact version pinning

ALWAYS pin exact versions:

```text
# GOOD — exact pins
pandas==1.5.3
requests==2.31.0
psycopg2-binary==2.9.7
snowflake-connector-python==3.2.0

# BAD — loose constraints (non-reproducible)
pandas>=1.5
requests~=2.31
psycopg2-binary
```

Loose constraints cause non-reproducible builds. A package that worked
yesterday may break tomorrow when the maintainer releases a new version.
MWAA runs `pip install -r requirements.txt` at every environment update
and worker restart.

### Python compatibility

| MWAA Airflow version | Python version |
|---|---|
| Airflow 2.7.x | Python 3.10 |
| Airflow 2.8.x | Python 3.10 |
| Airflow 2.9.x | Python 3.11 |
| Airflow 2.10.x | Python 3.11 |

Verify packages are compiled for the correct Python version:

```bash
# Check package compatibility
pip index versions pandas --python-version 3.11
```

Packages compiled for CPython 3.8/3.9 may fail on 3.10/3.11 with
`ModuleNotFoundError` or `ImportError`.

### Packages to avoid

- `psycopg2` (needs `libpq-dev`) → use `psycopg2-binary`
- `lxml` (needs `libxml2`) → use pre-compiled wheel only
- `geopandas` (needs `libgdal`) → complex system dependencies
- `apache-airflow` → MWAA manages this; do NOT pin it
- `boto3`/`botocore` → MWAA provides these; do NOT pin below MWAA version

### Uploading requirements.txt

```bash
aws s3 cp requirements.txt s3://my-mwaa-bucket/requirements.txt
```

MWAA applies the new requirements at the next environment update or
worker restart. To force an update:

```bash
aws mwaa update-environment \
  --name my-environment \
  --requirements-s3-path requirements.txt \
  --region us-east-1
```

### Testing requirements.txt locally

Use the MWAA local runner Docker image to test before deploying:

```bash
# Clone the MWAA local runner
git clone https://github.com/aws/aws-mwaa-local-runner.git
cd aws-mwaa-local-runner

# Build the Docker image
./mwaa-local-env build

# Start a local Airflow instance
./mwaa-local-env start

# Test your requirements.txt
# The local runner installs from requirements.txt at startup
```

## Plugin ZIP

### Structure

The plugins ZIP must contain Python files at the top level:

```text
plugins.zip
  ├── __init__.py
  ├── my_plugin.py
  └── custom_operator.py
```

### Creating the ZIP

```bash
cd plugins/
zip -r plugins.zip ./*.py
cd ..

aws s3 cp plugins.zip s3://my-mwaa-bucket/plugins/plugins.zip
```

### Plugin example

```python
# plugins/custom_operator.py
from airflow.models import BaseOperator

class CustomOperator(BaseOperator):
    def __init__(self, param, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.param = param

    def execute(self, context):
        self.log.info(f"Executing with param: {self.param}")
        return self.param
```

Use the plugin in a DAG:

```python
from custom_operator import CustomOperator

task = CustomOperator(
    task_id="custom_task",
    param="hello",
)
```

## Startup script

The startup script runs at worker startup (bash script):

```bash
#!/bin/bash
# startup_script.sh — runs at MWAA worker startup

# Install system-level dependencies
yum install -y jq

# Set environment variables
export CUSTOM_VAR="value"

# Run initialization code
echo "Worker startup at $(date)"
```

```bash
aws s3 cp startup_script.sh s3://my-mwaa-bucket/startup_script.sh
```

Specify the path in create-environment:

```bash
aws mwaa create-environment \
  --startup-script-s3-path startup_script.sh \
  ...
```

## Airflow configuration overrides

### Common overrides

```json
{
  "core.parallelism": "32",
  "core.dag_concurrency": "16",
  "core.dagbag_import_timeout": "60",
  "scheduler.dag_dir_list_interval": "30",
  "scheduler.min_file_process_interval": "5",
  "scheduler.scheduler_heartbeat_sec": "5",
  "webserver.dag_default_view": "tree",
  "webserver.dag_orientation": "LR",
  "webserver.worker_refresh_interval": "60",
  "email.email_backend": "airflow.utils.email.send_email_smtp",
  "smtp.smtp_host": "email-smtp.us-east-1.amazonaws.com",
  "smtp.smtp_port": "587",
  "smtp.smtp_starttls": "True",
  "smtp.smtp_mail_from": "airflow@example.com"
}
```

### Sizing overrides by execution class

| Override | mw1.small | mw1.medium | mw1.large |
|---|---|---|---|
| core.parallelism | 10 | 32 | 64 |
| core.dag_concurrency | 5 | 16 | 32 |
| worker.concurrency | 8 | 16 | 32 |

**Do NOT exceed these values.** Setting `core.parallelism` higher than
the execution class supports causes indefinite task queuing — the
scheduler queues tasks but workers cannot process them fast enough.

## Terraform example

```hcl
resource "aws_mwaa_environment" "main" {
  name              = "production-airflow"
  airflow_version   = "2.9.2"
  environment_class = "mw1.medium"
  min_workers       = 1
  max_workers       = 25

  webserver_access_mode = "PRIVATE_ONLY"

  source_bucket_arn    = aws_s3_bucket.dags.arn
  dag_s3_path          = "dags/"
  requirements_s3_path = "requirements.txt"
  plugins_s3_path      = "plugins/plugins.zip"

  execution_role_arn = aws_iam_role.mwaa.arn
  kms_key            = aws_kms_key.mwaa.arn

  network_configuration {
    security_group_ids = [aws_security_group.mwaa.id]
    subnet_ids         = [aws_subnet.private_a.id, aws_subnet.private_b.id]
  }

  logging_configuration {
    dag_processing_logs {
      enabled  = true
      log_level = "INFO"
    }
    scheduler_logs {
      enabled  = true
      log_level = "INFO"
    }
    webserver_logs {
      enabled  = true
      log_level = "WARNING"
    }
    worker_logs {
      enabled  = true
      log_level = "INFO"
    }
  }

  airflow_configuration_options = {
    "core.parallelism"              = "32"
    "core.dag_concurrency"          = "16"
    "scheduler.dag_dir_list_interval" = "30"
  }

  tags = {
    Environment = "production"
  }
}
```
