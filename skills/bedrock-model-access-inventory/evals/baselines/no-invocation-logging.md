# Baseline (no-skill) response: no-invocation-logging

This file captures what a generic assistant produces WITHOUT the
bedrock-model-access-inventory skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, enumerated FINDINGS, specific
remediation, forensic-trail reasoning).

---

This Bedrock account has several models enabled (Claude, Nova, and Titan)
but doesn't have any invocation logging configured. This means there's no
record of what prompts are being sent to the models or what responses come
back. If you need to investigate a security incident or comply with audit
requirements, you won't have the data.

There's also no customer-managed KMS key, so everything uses the default
AWS-managed encryption. And no guardrails are set up either.

You should enable invocation logging and consider adding a KMS key for
better control over your encryption.
