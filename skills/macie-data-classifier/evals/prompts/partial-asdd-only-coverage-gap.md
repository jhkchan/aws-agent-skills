# Eval: partial-asdd-only-coverage-gap

**Difficulty:** hard
**Branch:** PARTIALLY_CLASSIFIED — Macie enabled and ASDD on, but only one-time jobs, 7/12 high-sensitivity buckets ASDD-only, custom identifier with bad regex, Security Hub export disabled, no EventBridge rule

## Prompt

Audit the Macie data classification posture for account
123456789012 in us-east-1. Macie is enabled with FIFTEEN_MINUTES
frequency. ASDD is enabled but autoEnableOrganizationMembers is
false. There are 2 classification jobs — both one-time, zero
scheduled. Job scoping: 10 buckets included, 0 excluded.
Coverage: 120 total buckets, 85 ASDD, 10 deep-scan, 35
unmonitored. Managed identifiers RECOMMENDED. 1 custom
identifier with regex \d{1,19} (no word boundaries, no
ignore-words). Only 5/12 high-sensitivity buckets have
full-scan. Security Hub export is DISABLED. No EventBridge rule.
