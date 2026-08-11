# Baseline (no-skill) response: delivery-to-s3-kms-gap

This file captures what a generic assistant produces WITHOUT the
kinesis-firehose-troubleshooter skill loaded - the contrast that
proves the skill adds structure (5-layer health check,
deterministic VERDICT, fix CLI, verification step).

---

The Firehose delivery stream is failing to write to S3 because
of a KMS key permission error. CloudTrail shows an
`AccessDenied` on `kms:GenerateDataKey`. You need to update
the KMS key policy to allow the Firehose service to use the
key.

Add a statement to the key policy that grants
`kms:GenerateDataKey` and `kms:Decrypt` to
`firehose.amazonaws.com`.
