# Error Handling (load on demand) — CloudWatch Metric Stream Deployer

Silent-failure and cost-surprise error handling moved verbatim from SKILL.md. Load on demand when a deployed stream misbehaves.


---

## Error handling (moved from SKILL.md)

- **Stream shows "running" but no data in S3:** the IAM role trust
  policy does not include `cloudwatch.amazonaws.com`, or the role
  lacks `firehose:PutRecord` permission. Verify the trust policy and
  permissions. Check CloudTrail for `AccessDenied` from
  `cloudwatch.amazonaws.com`.
- **Data delayed by >5 minutes:** Firehose buffer interval is set too
  high (e.g., 900 seconds), or the metric stream is low-traffic (buffer
  size not reached, so interval dominates). Reduce buffer interval.
- **Stream cost higher than expected:** no namespace filter (streaming
  ALL metrics), or too many statistics requested. Add an include
  filter and reduce the statistics list.
- **Firehose not delivering to S3:** Firehose role lacks
  `s3:PutObject` on the bucket, or KMS key policy lacks
  `kms:GenerateDataKey` for the Firehose role. Check Firehose
  CloudWatch metrics (`DeliveryToS3.Success`).
- **GetMetricData throttling when migrating:** if migrating from
  GetMetricData polling, the old polling may still be running. Disable
  the old polling jobs after the metric stream is verified.
