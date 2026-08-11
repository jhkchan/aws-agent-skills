# Baseline (no-skill) — missing-execution-role

> This is the response a model produces **without** the skill definition.
> It proceeds with deployment without flagging the missing execution role.
> The application is created but the first job run fails with
> `AccessDeniedException` because there is no role for the application
> to assume at runtime.

---

Here are the commands to deploy your EMR Serverless Spark application:

```bash
aws emr-serverless create-application \
  --name report-spark-prod \
  --release-label emr-7.2.0 \
  --type SPARK

aws emr-serverless start-job-run \
  --application-id <app-id> \
  --job-driver '{
    "sparkSubmit": {
      "entryPoint": "s3://etl-scripts/report.py"
    }
  }'
```

You can add the execution role later if needed.
