# Eval prompt: healthy-assessment-ok

Audit the following Audit Manager assessment configuration for evidence
completeness and compliance posture. Emit the standard VERDICT block
(ASSESSMENT, FRAMEWORK, VERDICT, REASON, CONTROL BREAKDOWN, FINDINGS,
REMEDIATION).

Assessment name: SOC2-2026-healthy-assessment-ok
Assessment id: arn:aws:auditmanager:us-east-1:111111111111:assessment/a-healthy-assessment-ok
Framework: SOC 2
Status: ACTIVE
Creation time: 2026-01-01
Last updated: 2026-08-04
Scope:
  awsAccounts: [111111111111, 222222222222]
  awsServices: [ec2, s3, iam, kms, rds, lambda, cloudtrail, config]

Control statistics:
  total: 200
  PASS: 188
  FAIL: 6
  NOT_ASSESSED: 4
  MANUAL: 2
  UNDER_REVIEW: 0

Settings:
  kmsKey: arn:aws:kms:us-east-1:111111111111:key/audit-encryption-key
  snsTopic: arn:aws:sns:us-east-1:111111111111:audit-alerts
  defaultAssessmentReportsDestination: s3://audit-reports/soc2-2026/
  defaultProcessOwners: [arn:aws:iam::111111111111:role/audit-reviewer, arn:aws:iam::111111111111:role/compliance-lead]

Data sources:
  AWS Config recorder: ON in all in-scope accounts
  CloudTrail management events: logging in all in-scope accounts

Delegations: all COMPLETE

Org member accounts: [111111111111, 222222222222] (scope matches org — no gap)
