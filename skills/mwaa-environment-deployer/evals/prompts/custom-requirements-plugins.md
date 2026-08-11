# Eval: custom-requirements-plugins

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — mw1.medium, exact-pinned requirements.txt with pandas/snowflake/psycopg2-binary, plugins ZIP, 20 DAGs

## Prompt

Create an MWAA environment named etl-airflow. Airflow 2.9.2,
execution class mw1.medium, min 1 max 20 workers. Webserver
PUBLIC_ONLY. VPC vpc-etl222 with subnets subnet-etl-a
(us-east-1a) and subnet-etl-b (us-east-1b), both private.
Security group sg-etl-mwaa. S3 DAG bucket
s3://etl-mwaa-bucket. requirements.txt at
s3://etl-mwaa-bucket/requirements.txt with packages:
pandas==1.5.3, snowflake-connector-python==3.2.0,
psycopg2-binary==2.9.7, requests==2.31.0. Plugins ZIP at
s3://etl-mwaa-bucket/plugins/plugins.zip. 20 DAGs in /dags/.
IAM role arn:aws:iam::123456789012:role/MwaaEtlRole. Region
us-east-1. Tags: Environment=production, Pipeline=etl.
