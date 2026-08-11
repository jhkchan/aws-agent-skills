# Eval: small-public-webserver

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — mw1.small, PUBLIC_ONLY webserver, 2 private subnets in different AZs, S3 VPC endpoint, requirements.txt, startup/stop scheduling

## Prompt

Create an MWAA environment named dev-airflow. Airflow 2.9.2,
execution class mw1.small, min 1 max 5 workers. Webserver
access PUBLIC_ONLY. VPC vpc-aaa11122 with subnets subnet-aaa
(us-east-1a) and subnet-bbb (us-east-1b), both private. Security
group sg-mwaa123. S3 DAG bucket s3://my-mwaa-bucket with
requirements.txt (3 exact-pinned packages) and 5 DAGs in /dags/.
IAM role arn:aws:iam::123456789012:role/MwaaExecutionRole.
Startup time 08:00, shutdown 20:00. Region us-east-1. Tags:
Environment=dev, Team=data-platform.
