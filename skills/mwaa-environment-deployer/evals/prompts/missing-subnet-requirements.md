# Eval: missing-subnet-requirements

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — only 1 private subnet provided; MWAA requires 2 private subnets in different AZs

## Prompt

Create an MWAA environment named test-airflow. Airflow 2.9.2,
execution class mw1.small, min 1 max 5 workers. VPC vpc-test444
with subnet subnet-single (us-east-1a) — only 1 private subnet
available. Security group sg-test-mwaa. S3 DAG bucket
s3://test-mwaa-bucket with 3 DAGs. IAM role
arn:aws:iam::123456789012:role/MwaaTestRole. Region us-east-1.
