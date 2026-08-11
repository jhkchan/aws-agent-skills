# Eval: fargate-job-queue-definition

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — Fargate compute environment, job queue, job definition with container image and Fargate platform LATEST

## Prompt

Create an AWS Batch Fargate compute environment named
batch-fargate-prod in us-east-1. Max vCPUs 128. Subnets
subnet-aaa11122, subnet-bbb22233. Security group sg-batch-fargate.
Create a job queue fargate-queue with priority 300. Register a job
definition data-etl-v1 with image
123456789012.dkr.ecr.us-east-1.amazonaws.com/data-etl:latest,
vCPUs 2, memory 4096 MB. Environment variables: S3_BUCKET=etl-data,
LOG_LEVEL=INFO. Fargate platform version LATEST. Tags:
Environment=production, Workload=etl.
