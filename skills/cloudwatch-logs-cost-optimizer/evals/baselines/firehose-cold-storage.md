# Baseline (no-skill) response: firehose-cold-storage

This file captures what a generic assistant produces WITHOUT the
cloudwatch-logs-cost-optimizer skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, Firehose + S3 lifecycle
cost math, Athena query workflow, CONFIRM gate).

---

Your audit log group has 2-year retention and is storing 12,000 GB in
CloudWatch Logs. At $0.03/GB/month that's $360/month in storage alone,
plus $250/month in ingestion. That's expensive for logs you rarely
query.

You could set up a Kinesis Firehose delivery stream to send these logs
to S3 instead, where storage is much cheaper. With S3 lifecycle policies
you could transition to Glacier after 90 days for even more savings.

Create a Firehose stream that delivers to an S3 bucket:

```
aws firehose create-delivery-stream --delivery-stream-name audit-archive --s3-destination-configuration ...
```

Then reduce the CloudWatch Logs retention to 30 days (or whatever your
operational window requires). The compliance archive stays in S3.

This should save you several hundred dollars per month.
