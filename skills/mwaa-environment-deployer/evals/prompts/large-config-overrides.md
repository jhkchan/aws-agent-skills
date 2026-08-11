# Eval: large-config-overrides

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — mw1.large, Airflow config overrides (parallelism=64, dag_concurrency=32), PRIVATE_ONLY, KMS, all logs

## Prompt

Create an MWAA environment named enterprise-airflow. Airflow
2.9.2, execution class mw1.large, min 2 max 50 workers. Webserver
PRIVATE_ONLY. VPC vpc-ent333 with subnets subnet-ent-a
(us-east-1a) and subnet-ent-b (us-east-1b), both private with S3
VPC endpoint. Security group sg-ent-mwaa. S3 DAG bucket
s3://ent-mwaa-bucket with 50 DAGs. Airflow config overrides:
core.parallelism=64, core.dag_concurrency=32,
scheduler.dag_dir_list_interval=30. KMS key
arn:aws:kms:us-east-1:123456789012:key/efgh5678. All CloudWatch
Logs enabled. IAM role
arn:aws:iam::123456789012:role/MwaaEntRole. Region us-east-1.
Tags: Environment=enterprise, Scale=large.
