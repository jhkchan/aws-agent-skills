---
description: Audit an AWS Audit Manager assessment for evidence-collection integrity, control compliance rate, delegation wiring, and account-level settings posture.
nl_triggers:
  - "audit Audit Manager assessment"
  - "check assessment evidence"
  - "is evidence collection complete"
  - "assessment compliance check"
  - "stopped assessment stale"
  - "Audit Manager settings"
  - "NOT_ASSESSED controls"
  - "assessment scope gap"
  - "delegation pending"
  - "compliance report readiness"
  - "Audit Manager config gap"
  - "assessment INACTIVE"
  - "defaultProcessOwners"
  - "Audit Manager KMS key"
  - "SOC 2 assessment"
  - "PCI DSS assessment"
  - "HIPAA assessment"
  - "evidence integrity"
routes_to: auditmanager-assessment-auditor
---

# /aws:audit-auditmanager-assessment

Activate the `auditmanager-assessment-auditor` skill and audit one or more
Audit Manager assessments for evidence-collection integrity, compliance,
and configuration posture.

## What it does

Reads an Audit Manager assessment snapshot (assessment metadata + control
statistics + settings + data-source status) and applies the ordered
classification logic:

1. Pre-flight account-status gate — short-circuit if Audit Manager is not
   enabled or has zero assessments.
2. Evidence-collection integrity (Step 1) — INACTIVE assessment,
   NOT_ASSESSED > 30% (data-source break via Config/CloudTrail),
   outstanding delegations, scope-coverage gap → INCOMPLETE_EVIDENCE.
3. Compliance evaluation (Step 2) — PASS% < 60% or FAIL% > 25% with
   evidence sufficiently complete → LOW_COMPLIANCE.
4. Configuration evaluation (Step 3) — missing kmsKey, snsTopic,
   assessment-reports destination, or defaultProcessOwners → CONFIG_GAP.
5. Aggregation — worst verdict wins (INCOMPLETE_EVIDENCE >
   LOW_COMPLIANCE > CONFIG_GAP > OK).

Emits a deterministic verdict per assessment:

```text
ASSESSMENT: <assessment-id>
FRAMEWORK: <framework>
VERDICT: INCOMPLETE_EVIDENCE | LOW_COMPLIANCE | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and step number>
CONTROL BREAKDOWN:
  total: <N>, PASS: <n>, FAIL: <n>, NOT_ASSESSED: <n>, ...
FINDINGS:
  - [<severity note>] <finding description (Step Na)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

Paste an Audit Manager assessment snapshot and ask any of:

- "audit this Audit Manager assessment"
- "is my evidence collection complete?"
- "is this assessment's compliance score trustworthy?"
- "check assessment settings"
- "stopped assessment — is the compliance data stale?"
- "NOT_ASSESSED controls — data-source problem?"

An assessment id/ARN plus any audit verb ("audit this assessment", "check
evidence completeness") also routes here.

## Inputs

- An Audit Manager assessment snapshot: assessment metadata (name, id,
  status, framework, scope, creationTime, lastUpdated), control statistics
  (total, PASS, FAIL, NOT_ASSESSED, MANUAL, UNDER_REVIEW), settings
  (kmsKey, snsTopic, defaultAssessmentReportsDestination,
  defaultProcessOwners), and data-source status (Config recorder,
  CloudTrail management events) per in-scope account.
- For live-account audits: provide an assessment id/ARN; the skill will
  guide the operator through `aws auditmanager get-assessment`,
  `get-settings`, `get-account-status`, `list-delegations`.

## Outputs

- One VERDICT block per assessment (multiple findings aggregate to the
  worst verdict).
- CONTROL BREAKDOWN with per-response counts and computed compliance%.
- Enumerated FINDINGS list with step citations.
- Specific remediation: reactivate assessments, repair Config/CloudTrail,
  set missing KMS/SNS/reports-destination/process-owners, scope to full
  org.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for Audit Manager governance and compliance).
- `/aws:audit-kms-key-policy` for KMS key policy analysis of the key used
  by Audit Manager settings (`settings.kmsKey`).
- `/aws:audit-securityhub-control-compliance` for Security Hub control
  finding lifecycle (complementary governance view).
