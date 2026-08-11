# Eval: macie-not-enabled-blocked

**Difficulty:** easy
**Branch:** BLOCKED — Macie session not enabled in target account; pre-flight gate catches missing enablement

## Prompt

Create a Macie classification job named "pii-scan-2026-08" on the
bucket sensitive-data-prod. Account: 123456789012. One-time scan for
USA_SOCIAL_SECURITY_NUMBER and CREDIT_CARD_NUMBER. We think Macie is
enabled but aren't sure. Region: us-east-1.
