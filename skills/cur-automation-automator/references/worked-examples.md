# Worked examples - CUR Automation Automator

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

### Perfect example output — MANUAL_STEP_REQUIRED

```text
OPERATION: create
VERDICT: MANUAL_STEP_REQUIRED
TARGET: linked-account-cur-stack
REQUIREMENTS:
  - [FAIL] Caller is linked account 222222222222, not payer 111111111111
  - [PASS] S3 bucket exists
IAC_TEMPLATE: (held in draft — apply after closing the gap below)
MANUAL_GAPS:
  - GAP: CUR is being created from a linked account.
    REMEDIATION:
      aws cur put-report-definition --report-definition file://cur.json --profile payer
    REASON: CUR API is payer-only; cross-account requires payer IAM role + Glue policy.
NOTES:
  - Run this skill from the payer account for organization-wide FinOps.
```
