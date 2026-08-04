# Baseline (no-skill) response: confused-deputy-with-source-arn

This file captures what a generic assistant produces WITHOUT the
sts-cross-account-role-auditor skill loaded. Note: the baseline recognizes
the SourceArn condition is good but does not classify the verdict
deterministically (CONDITIONAL vs OK) and misses the residual risk.

---

This trust policy allows Lambda to assume the role with a SourceArn and
SourceAccount condition. That's a good security practice because it
restricts which Lambda functions can use the role.

The conditions look well-configured. This is a secure setup for a
Lambda-based cross-service role assumption.
