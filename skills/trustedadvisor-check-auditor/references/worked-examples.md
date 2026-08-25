# Worked Examples — Trusted Advisor Check Auditor

Secondary worked examples moved out of the SKILL.md body. Loaded on demand.

## Worked example — service limits at 100%

```text
CHECK: VPC Limit (service-limit-vpc-at-100)
VERDICT: CRITICAL_CHECK
REASON: Service Limits check — usage computed at 100% of quota (5 / 5 VPCs,
Step 3). The check-level status says "error" but the severity is driven by
the percentage, not the label. New VPC creation will fail with
LimitExceededException.
FINDINGS:
  - [CRITICAL_CHECK] VPC usage at 100% of limit (5/5) — quota exhausted,
    new resource creation blocked (Step 3)
REMEDIATION:
  1. Request a quota increase: aws service-quotas request-service-quota-increase
     --service-code vpc --quota-code L-F678F1CE --desired-value 10
  2. Release unused VPCs to stay under the current limit while the increase
     is processed.
```
