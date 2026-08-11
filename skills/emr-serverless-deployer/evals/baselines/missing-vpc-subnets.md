# Baseline (no-skill) — missing-vpc-subnets

> This is the response a model produces **without** the skill definition.
> It creates the application and submits the job without configuring VPC
> access. The Spark job attempts to connect to the private Aurora
> PostgreSQL cluster and fails with `ConnectionTimeoutException` after
> the 60-second socket timeout. This is a silent failure — the job
> appears to start but the JDBC read hangs indefinitely.

---

Here are the commands to deploy your EMR Serverless Spark application:

```bash
aws emr-serverless create-application \
  --name db-spark-prod \
  --release-label emr-7.2.0 \
  --type SPARK

aws emr-serverless start-job-run \
  --application-id <app-id> \
  --execution-role-arn arn:aws:iam::123456789012:role/EMRDbExecRole \
  --job-driver '{
    "sparkSubmit": {
      "entryPoint": "s3://etl-scripts/db_read.py",
      "entryPointArguments": ["--jdbc-url", "jdbc:postgresql://db.cluster-xxx.us-east-1.rds.amazonaws.com:5432/analytics"]
    }
  }'
```

Your Spark job should be able to connect to the Aurora cluster
since it is in the same region.
