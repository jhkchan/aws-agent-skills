# Eval prompt: missing-kms-sns-config-gap

Audit the following Audit Manager assessment configuration for evidence
completeness and compliance posture. Emit the standard VERDICT block
(ASSESSMENT, FRAMEWORK, VERDICT, REASON, CONTROL BREAKDOWN, FINDINGS,
REMEDIATION).

Assessment name: SOC2-annual-missing-kms-sns-config-gap
Assessment id: arn:aws:auditmanager:us-east-1:111111111111:assessment/a-missing-kms-sns-config-gap
Framework: SOC 2
Status: ACTIVE
Creation time: 2026-01-15
Last updated: 2026-08-04
Scope:
  awsAccounts: [111111111111, 222222222222]
  awsServices: [ec2, s3, iam, kms, rds]

Control statistics:
  total: 150
  PASS: 132
  FAIL: 10
  NOT_ASSESSED: 8
  MANUAL: 0
  UNDER_REVIEW: 0

Settings:
  kmsKey: ""
  snsTopic: ""
  defaultAssessmentReportsDestination: s3://audit-reports/soc2-2026/
  defaultProcessOwners: [arn:aws:iam::111111111111:role/audit-reviewer]

Data sources:
  AWS Config recorder: ON in all in-scope accounts
  CloudTrail management events: logging in all in-scope accounts

Delegations: all COMPLETE
