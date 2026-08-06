# Baseline (no-skill) response: anthropic-claude-apac-geoblock

This file captures what a generic assistant produces WITHOUT the
bedrock-model-access-inventory skill loaded.

---

The account is in ap-southeast-1 and has Claude models enabled. Logging is
configured to S3 and CloudWatch with all modalities enabled, and there's a
customer-managed KMS key. Guardrails are attached to the Claude model.

One thing to be aware of is that Anthropic Claude models may have
availability restrictions in certain regions. You should verify that the
models can actually be invoked from your region.

The Nova model should work fine. Everything else looks well-configured from
a security perspective.
