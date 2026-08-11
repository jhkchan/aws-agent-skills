# Baseline (no-skill) — flink-production-streaming

> This is the response a model produces **without** the skill definition.
> It creates the application and starts it but omits the service execution
> role trust principal check, skips checkpointing configuration (uses
> DEFAULT), sets parallelism to 1 regardless of source shard count, omits
> CloudWatch logging, and references unversioned S3 code (`latest`). The
> application deploys but fails on the first Kinesis GetRecords call and
> failures are invisible.

---

Here are the commands to deploy your Kinesis Data Analytics Flink
application:

```bash
aws kinesisanalyticsv2 create-application \
  --application-name fraud-detection-flink \
  --runtime-environment FLINK-1_19 \
  --service-execution-role arn:aws:iam::123456789012:role/KDAExecutionRole \
  --application-configuration '{
    "ApplicationCodeConfiguration": {
      "CodeContent": {
        "S3ContentLocation": {
          "BucketARN": "arn:aws:s3:::kda-apps",
          "FileKey": "fraud-detection-latest.jar"
        }
      }
    }
  }'

aws kinesisanalyticsv2 start-application --application-name fraud-detection-flink
```

Your application should run once started.
