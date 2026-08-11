# Baseline (no-skill) — missing-execution-role

> This is the response a model produces **without** the skill definition.
> It proceeds with deployment without flagging the missing service
> execution role. The application is created but fails to start with
> `AccessDeniedException` because KDA cannot assume a role for runtime
> AWS API calls.

---

Here are the commands to deploy your Kinesis Data Analytics Flink
application:

```bash
aws kinesisanalyticsv2 create-application \
  --application-name report-flink-prod \
  --runtime-environment FLINK-1_19 \
  --application-configuration '{
    "ApplicationCodeConfiguration": {
      "CodeContent": {
        "S3ContentLocation": {
          "BucketARN": "arn:aws:s3:::kda-apps",
          "FileKey": "report-1.0.0.jar"
        }
      }
    }
  }'

aws kinesisanalyticsv2 start-application --application-name report-flink-prod
```

You can add the execution role later if needed.
