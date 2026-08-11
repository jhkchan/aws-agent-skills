# Eval: healthy-classified-posture

**Difficulty:** hard
**Branch:** CLASSIFIED — Macie enabled, ASDD on with auto-enable, daily scheduled jobs for high-sensitivity buckets, custom identifiers with healthy regex, narrow suppression rules, Security Hub export enabled, full multi-account coverage

## Prompt

Audit the Macie data classification posture for account
123456789012 in us-east-1. Macie is enabled with FIFTEEN_MINUTES
frequency. ASDD is enabled with auto-enable for org members.
There are 4 classification jobs (1 one-time, 3 scheduled daily)
scoping 28 sensitive S3 buckets with 12 non-sensitive excluded.
Coverage: 120 total buckets, 108 ASDD, 28 deep-scan, 12
unmonitored (low-risk logs). Managed identifiers set to ALL.
3 custom identifiers (employee ID, internal API key, proprietary
format) — all with word boundaries and ignore-words. 12/12
high-sensitivity buckets have full-scan daily jobs. Findings
last 30d: 2 High (triaged), 8 Medium, 15 Low (archived). 4
suppression rules (1 SUPPRESS for known-public-bucket, 3
ARCHIVE). 148/150 org accounts enrolled. Security Hub export
enabled. EventBridge rule active with Lambda remediation target.
