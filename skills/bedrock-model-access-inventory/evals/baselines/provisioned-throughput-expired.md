# Baseline (no-skill) response: provisioned-throughput-expired

This file captures what a generic assistant produces WITHOUT the
bedrock-model-access-inventory skill loaded.

---

The account looks well-configured overall. Logging goes to S3, CloudWatch,
and Firehose with all modalities enabled. There's a customer-managed KMS key
and guardrails are attached to both models.

However, the provisioned throughput for Claude has expired (it ended on
2026-03-15). This means the model is now billing at on-demand rates, which
is probably more expensive. You should either renew the commitment or
switch to a model with active provisioned throughput if cost is a concern.
