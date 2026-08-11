# Baseline (no-skill) — missing-source-stream

> This is the response a model produces **without** the skill definition.
> It proceeds with deployment without verifying that the source Kinesis
> Data Stream exists. The application is created and started but reads
> zero records because the source stream does not exist. The operator
> is unaware of the silent failure.

---

Here are the commands to deploy your Kinesis Data Analytics Flink
application:

```bash
aws kinesisanalyticsv2 create-application \
  --application-name etl-flink-prod \
  --runtime-environment FLINK-1_19 \
  --service-execution-role arn:aws:iam::123456789012:role/KDAExecutionRole \
  --application-configuration '{
    "ApplicationCodeConfiguration": {
      "CodeContent": {
        "S3ContentLocation": {
          "BucketARN": "arn:aws:s3:::kda-apps",
          "FileKey": "etl-1.0.0.jar"
        }
      },
      "EnvironmentProperties": {
        "PropertyGroups": [
          {"PropertyGroupId": "ConsumerConfig", "PropertyMap": {"STREAM_NAME": "ingestion-events"}}
        ]
      }
    }
  }'

aws kinesisanalyticsv2 start-application --application-name etl-flink-prod
```

Your application should run once started.
