# Inspector2 Automation Automator — worked examples (moved verbatim from SKILL.md)

> Progressive-disclosure split: this content was moved verbatim from SKILL.md; nothing was rewritten.

## Worked example — REVIEW_REQUIRED, missing delegated admin

```text
FINDING: multiaccount-finding-triage
SEVERITY: HIGH
DETECTION:
  - Source: aws.inspector2 in management account
  - Resource: AWS_ECR_CONTAINER_IMAGE across 15 member accounts
  - CVE: CVE-2026-5678 on log4j in shared service image
RESPONSE:
  - Action: notify + rebuild trigger
  - SLA: 7 days
  - Automation: blocked (delegated admin not configured)
SSM_RUNBOOK: n/a (container finding — CodeBuild rebuild)
VERIFICATION: blocked
MULTI_ACCOUNT: REVIEW_REQUIRED — delegated admin not yet configured
VERDICT: REVIEW_REQUIRED
GAP: Inspector delegated admin not configured. Without delegated admin, findings must be queried per-member-account individually. Configure via aws organizations register-delegated-administrator --account-id 111111111111 --service-principal inspector2.amazonaws.com before enabling fleet-wide automation.
TEMPLATE: (blocked until delegated admin configured)
```
