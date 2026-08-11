# Eval: medium-private-logs

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — mw1.medium, PRIVATE_ONLY webserver, 4 CloudWatch log types, KMS encryption, S3 VPC endpoint

## Prompt

Create an MWAA environment named prod-airflow. Airflow 2.9.2,
execution class mw1.medium, min 1 max 25 workers. Webserver
access PRIVATE_ONLY. VPC vpc-prod111 with subnets subnet-prov-a
(us-east-1a) and subnet-prov-b (us-east-1b), both private.
Security group sg-prod-mwaa. S3 VPC endpoint for S3 access.
S3 DAG bucket s3://prod-mwaa-dags with 15 DAGs in /dags/.
requirements.txt at root with 7 exact-pinned packages. Enable
all CloudWatch Logs (DagProcessing INFO, Scheduler INFO,
Webserver WARNING, Worker INFO). KMS key
arn:aws:kms:us-east-1:123456789012:key/abcd1234. IAM role
arn:aws:iam::123456789012:role/MwaaProdRole. Region us-east-1.
Tags: Environment=production, Compliance=HIPAA.
