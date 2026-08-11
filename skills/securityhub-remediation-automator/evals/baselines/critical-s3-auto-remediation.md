# Baseline (no-skill) response: critical-s3-auto-remediation

This file captures what a generic assistant produces WITHOUT the
securityhub-remediation-automator skill loaded — the contrast that
proves the skill adds structure (deterministic VERDICT, severity
routing, EventBridge pattern, Lambda dispatcher, finding closure).

---

For a critical S3 public access finding in Security Hub, you can set up
an EventBridge rule to trigger a Lambda function that calls SSM to
disable the public access. The Lambda should also update the finding
status.

You need to make sure FSBP is enabled and the S3 control is active.
Use AWS-DisableS3BucketPublicAccess as the SSM runbook.

Something like:

```
aws events put-rule --name securityhub-remediation --event-pattern '...'
```

You'll need to configure the Lambda to extract the bucket name from the
finding and pass it to SSM. Make sure the IAM roles are set up correctly.
