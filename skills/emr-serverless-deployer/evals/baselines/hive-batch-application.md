# Baseline (no-skill) — hive-batch-application

> This is the response a model produces **without** the skill definition.
> It creates the Hive application and submits the query but misses the
> S3 log bucket, CloudWatch logging, Glue catalog permissions in the
> execution role, and auto-stop configuration. Job failures are
> invisible.

---

Here are the commands to deploy your EMR Serverless Hive application:

```bash
aws emr-serverless create-application \
  --name hive-batch-prod \
  --release-label emr-7.2.0 \
  --type HIVE

aws emr-serverless start-job-run \
  --application-id <app-id> \
  --execution-role-arn arn:aws:iam::123456789012:role/EMRHiveExecRole \
  --job-driver '{
    "hive": {
      "query": "SELECT COUNT(*) FROM sales WHERE dt = '\''2026-08-11'\''"
    }
  }'
```

Your Hive job should run once the application is started.
