# Baseline (no-skill) response: s3-archive-pipeline

This file captures what a generic assistant produces WITHOUT the
log-retention-automator skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, tier validation,
EventBridge automation, Firehose archival, cost estimation, expert
CloudWatch Logs knowledge).

---

For long-term log storage, you can use Kinesis Firehose to send
CloudWatch Logs to S3. Set up a subscription filter on the log
group that points to a Firehose delivery stream.

```
aws firehose create-delivery-stream --s3-destination-configuration ...
aws logs put-subscription-filter --destination-arn <firehose> ...
```

Set CloudWatch retention to 90 days for the hot window and let
S3 handle the cold storage. You can add lifecycle rules to move
data to Glacier after some time.

7 years is a lot of data so make sure your S3 bucket is set up
correctly. GZIP compression will help reduce storage costs.
