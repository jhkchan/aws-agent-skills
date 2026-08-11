# Baseline (no-skill) — studio-notebook-zeppelin

> This is the response a model produces **without** the skill definition.
> It creates the notebook with the wrong runtime (FLINK-1_19 instead of
> ZEPPELIN-FLINK-1_0), omits the Glue Data Catalog configuration, skips
> the deploy-as-application flag, and does not configure CloudWatch
> logging. The notebook deploys but interactive analysis cannot resolve
> Glue tables.

---

Here are the commands to deploy your Kinesis Data Analytics Studio
notebook:

```bash
aws kinesisanalyticsv2 create-application \
  --application-name fraud-explore-notebook \
  --runtime-environment FLINK-1_19 \
  --service-execution-role arn:aws:iam::123456789012:role/KDAExecutionRole \
  --application-configuration '{
    "ApplicationCodeConfiguration": {
      "CodeContent": {
        "S3ContentLocation": {
          "BucketARN": "arn:aws:s3:::kda-apps",
          "FileKey": "custom-udf-1.0.0.jar"
        }
      }
    }
  }'

aws kinesisanalyticsv2 start-application --application-name fraud-explore-notebook
```

Your notebook should run once started.
