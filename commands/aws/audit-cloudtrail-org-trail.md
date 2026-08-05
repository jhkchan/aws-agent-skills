---
description: Audit a CloudTrail organization trail for org coverage, multi-region logging, KMS encryption, log-file validation, CloudWatch Logs delivery, CloudTrail Insights, and log retention posture.
nl_triggers:
  - "audit this CloudTrail trail"
  - "check CloudTrail org trail"
  - "CloudTrail multi-region check"
  - "is CloudTrail encrypted with KMS"
  - "check CloudTrail log file validation"
  - "are CloudTrail Insights enabled"
  - "CloudTrail org trail coverage"
  - "verify CloudTrail forensic readiness"
  - "CloudTrail compliance check"
  - "is this an org trail"
  - "CloudTrail log retention"
  - "CloudTrail digest files"
  - "CloudTrail configuration gap"
  - "audit logging posture"
  - "CloudTrail SSE-KMS"
routes_to: cloudtrail-org-trail-auditor
---

# /aws:audit-cloudtrail-org-trail

Activate the `cloudtrail-org-trail-auditor` skill and audit one or more
CloudTrail trail configurations for org-wide audit-logging posture.

## What it does

Reads a CloudTrail trail configuration (describe-trails output) paired with
trail status (get-trail-status), insight selectors (get-insight-selectors),
and CloudWatch Logs retention metadata. Applies the ordered classification:

1. Org trail check — `IsOrganizationTrail: true` or NO_ORG_TRAIL.
2. KMS encryption — `KmsKeyId` present (SSE-KMS) or NO_ENCRYPTION.
3. Log file validation — `LogFileValidationEnabled: true` or NO_VALIDATION.
4. CloudTrail Insights — selectors configured or NO_INSIGHTS.
5. Config gap — multi-region, CloudWatch Logs, global events, retention
   (>= 90 days). Any fail → CONFIG_GAP.
6. All pass → OK.

Emits a deterministic VERDICT per trail:

```text
TRAIL: <trail-name>
VERDICT: NO_ORG_TRAIL | NO_ENCRYPTION | NO_VALIDATION | NO_INSIGHTS | CONFIG_GAP | OK
REASON: <1-2 sentences citing the first failing dimension and step number>
FINDINGS:
  - [CRITICAL] <finding description (Step N)>
  - [HIGH] <finding description (Step N)>
  - [OK] <dimension that passed>
REMEDIATION: <specific CLI per finding, or "None required" if OK>
```

## When to invoke

Paste a CloudTrail trail configuration and ask any of:

- "audit this CloudTrail trail"
- "is my org trail configured correctly"
- "check CloudTrail log file validation"
- "is CloudTrail encrypted with KMS"
- "are CloudTrail Insights enabled"
- "is this trail multi-region"
- "verify CloudTrail forensic readiness"

A bare trail name or ARN + any audit verb also routes here.

## Inputs

- Trail configuration from `aws cloudtrail describe-trails --trail-name-list
  <name> --output json` (key-value summary or JSON).
- Trail status from `aws cloudtrail get-trail-status --name <name>`.
- Insight selectors from `aws cloudtrail get-insight-selectors --trail-name
  <name>`.
- CloudWatch Logs retention from `aws logs describe-log-groups --log-group-
  name-prefix <group>`.

## Outputs

- One VERDICT block per trail (first-fail-wins ordering).
- Enumerated FINDINGS with per-dimension status and step citation.
- Specific remediation: update-trail CLI commands, KMS key policy guidance,
  CloudWatch Logs retention policy.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for CloudTrail governance and compliance).
- `/aws:audit-kms-key-policy` for auditing the KMS key used by the trail's
  SSE-KMS encryption.
