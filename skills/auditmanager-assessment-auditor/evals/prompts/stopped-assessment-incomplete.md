# Eval prompt: stopped-assessment-incomplete

Audit the following Audit Manager assessment configuration for evidence
completeness and compliance posture. Emit the standard VERDICT block
(ASSESSMENT, FRAMEWORK, VERDICT, REASON, CONTROL BREAKDOWN, FINDINGS,
REMEDIATION).

Assessment name: SOC2-Q1-2026-stopped-assessment-incomplete
Assessment id: arn:aws:auditmanager:us-east-1:111111111111:assessment/a-stopped-assessment-incomplete
Framework: SOC 2
Status: INACTIVE
Creation time: 2025-10-01
Last updated: 2026-02-14
Scope:
  awsAccounts: [111111111111, 222222222222]
  awsServices: [ec2, s3, iam, kms, rds, lambda, cloudtrail, config]

Control statistics (across all control sets):
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

Data sources (at last collection):
  AWS Config recorder: ON (account 111111111111), OFF (account 222222222222)
  CloudTrail management events: logging
