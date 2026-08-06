# Baseline (no-skill) response: no-kms-customer-key

This file captures what a generic assistant produces WITHOUT the
bedrock-model-access-inventory skill loaded.

---

The account has logging configured to S3 and CloudWatch with text and
image delivery enabled, which is good. However, there's no customer-managed
KMS key — it's using AWS-managed encryption only.

AWS-managed encryption does encrypt data at rest, but you don't have
control over the key. For compliance requirements like SOC2 or HIPAA, you
might need a customer-managed key so you can audit key usage and revoke
access if needed.

The models are all Amazon (Nova and Titan), no Anthropic models, so there's
no geo-block concern.
