# End-to-end usage scenario: auditmanager-assessment-auditor

A walkthrough showing the skill auditing an Audit Manager assessment that
has a stopped state (INACTIVE), a high NOT_ASSESSED burden from a Config
data-source break, and correct settings — demonstrating the INCOMPLETE_EVIDENCE
verdict, the evidence-integrity-over-compliance-number principle, and the
data-source-repair remediation workflow.

## Input (user prompt)

> Review this Audit Manager assessment before we generate the SOC 2
> compliance report. The compliance score says 31% but I want to know
> if that number is even trustworthy.

Assessment name: SOC2-Q1-2026-stopped-assessment-incomplete
Assessment id: arn:aws:auditmanager:us-east-1:111111111111:assessment/a-stopped-assessment-incomplete
Framework: SOC 2
Status: INACTIVE
Creation time: 2025-10-01
Last updated: 2026-02-14
Scope:
  awsAccounts: [111111111111, 222222222222]
  awsServices: [ec2, s3, iam, kms, rds, lambda, cloudtrail, config]

Control statistics:
  total: 312
  PASS: 98
  FAIL: 41
  NOT_ASSESSED: 131
  MANUAL: 30
  UNDER_REVIEW: 12

Settings:
  kmsKey: arn:aws:kms:us-east-1:111111111111:key/audit-encryption
  snsTopic: arn:aws:sns:us-east-1:111111111111:audit-notify
  defaultAssessmentReportsDestination: s3://audit-reports/soc2/
  defaultProcessOwners: [arn:aws:iam::111111111111:role/audit-reviewer]

Data sources:
  AWS Config recorder: ON (111111111111), OFF (222222222222)
  CloudTrail management events: logging

## Skill output

```text
ASSESSMENT: arn:aws:auditmanager:us-east-1:111111111111:assessment/a-stopped-assessment-incomplete
FRAMEWORK: SOC 2
VERDICT: INCOMPLETE_EVIDENCE
REASON: Assessment status is INACTIVE (stopped) since 2026-02-14 — no new
evidence collected for ~6 months; the 31.4% compliance score is frozen and
untrustworthy. Additionally, 42% of controls are NOT_ASSESSED, indicating
the Config data source was broken in account 222222222222 before the
assessment was stopped (Steps 1a, 1b).
CONTROL BREAKDOWN:
  total: 312, PASS: 98, FAIL: 41, NOT_ASSESSED: 131, MANUAL: 30, UNDER_REVIEW: 12
  compliance%: 31.4
FINDINGS:
  - [STALE] Assessment status INACTIVE since 2026-02-14; compliance score frozen (Step 1a)
  - [COLLECTION BREAK] NOT_ASSESSED 131/312 (42%) — Config recorder OFF in 222222222222 (Step 1b)
  - [CONFIG] 30 MANUAL + 12 UNDER_REVIEW controls need human attestation
REMEDIATION:
  1. Repair Config in account 222222222222:
     `aws configservice start-configuration-recorder --configuration-recorder-name default`
  2. Reactivate the assessment:
     `aws auditmanager update-assessment-status --assessment-id <id> --status ACTIVE --region us-east-1`
  3. Wait one full collection cycle (~24h) for Audit Manager to re-evaluate
     the 131 NOT_ASSESSED controls.
  4. Re-baseline the compliance % — do NOT generate the SOC 2 report until
     the re-evaluated number is available.
```

## What the skill caught that a generic response misses

1. **The 31% is not a LOW_COMPLIANCE finding.** A generic assistant sees
   "31% compliance" and says "you have low compliance, fix your failing
   controls." The skill distinguishes that 42% of controls are
   NOT_ASSESSED (a data-source problem) from the 13% that are FAIL
   (a control-failure problem). The verdict is INCOMPLETE_EVIDENCE, not
   LOW_COMPLIANCE — the remediation is to repair Config first, then
   re-read the number.

2. **The frozen-dashboard trap.** The assessment has been INACTIVE for
   ~6 months. The compliance score shown in the console is frozen at
   the stop-time value. Reporting against it in a SOC 2 audit would be
   a material misrepresentation.

3. **The data-source root cause.** Config is OFF in account 222222222222.
   This is why NOT_ASSESSED accumulated — not because controls are
   failing, but because Audit Manager has no configuration snapshots to
   evaluate against. The remediation chain (repair Config → reactivate →
   wait → re-baseline) addresses the root cause before any compliance
   number is trusted.
