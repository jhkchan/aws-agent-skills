# Baseline (no-skill) response: cw-logging-disabled-with-lambda

This file captures what a generic assistant produces WITHOUT the
firehose-delivery-stream-auditor skill loaded.

---

The stream has a Lambda transformation processor configured with a
backup bucket, which is good practice. Encryption is set with a KMS CMK.

I notice LoggingConfig is set to enabled: false. You might want to
enable it for visibility, but the Firehose metrics in CloudWatch should
still give you delivery success rates.
