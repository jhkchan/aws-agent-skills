# Baseline (no-skill) — spark-production-etl

> This is the response a model produces **without** the skill definition.
> It creates the application and submits the job but misses the execution
> role trust principal (uses `elasticmapreduce.amazonaws.com` instead of
> `emr-serverless.amazonaws.com`), omits pre-initialized capacity, skips
> VPC access, and does not configure CloudWatch logging. The job deploys
> but fails on the first S3 operation and failures are invisible.

---

Here are the commands to deploy your EMR Serverless Spark application:

```bash
aws emr-serverless create-application \
  --name etl-spark-prod \
  --release-label emr-7.2.0 \
  --type SPARK

aws emr-serverless start-job-run \
  --application-id <app-id> \
  --execution-role-arn arn:aws:iam::123456789012:role/EMRServerlessExecRole \
  --job-driver '{
    "sparkSubmit": {
      "entryPoint": "s3://etl-scripts/daily_transform.py"
    }
  }'
```

Your job should run once the application is started.
