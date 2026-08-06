# Eval prompt: no-process-owners-config-gap

Audit the following Audit Manager assessment configuration for evidence
completeness and compliance posture. Emit the standard VERDICT block
(ASSESSMENT, FRAMEWORK, VERDICT, REASON, CONTROL BREAKDOWN, FINDINGS,
REMEDIATION).

Assessment name: ISO27001-annual-no-process-owners-config-gap
Assessment id: arn:aws:auditmanager:us-east-1:111111111111:assessment/a-no-process-owners-config-gap
Framework: ISO 27001
Status: ACTIVE
Creation time: 2026-02-01
Last updated: 2026-08-04
Scope:
  awsAccounts: [111111111111, 222222222222]
  awsServices: [ec2, s3, iam, kms, rds, lambda]

Control statistics:
  total: 100
  PASS: 92
  FAIL: 3
  NOT_ASSESSED: 5
  MANUAL: 0
  UNDER_REVIEW: 0

Settings:
  kmsKey: arn:aws:kms:us-east-1:111111111111:key/iso-audit-key
  snsTopic: arn:aws:sns:us-east-1:111111111111:iso-audit-notify
  defaultAssessmentReportsDestination: s3://iso-reports/2026/
  defaultProcessOwners: []

Data sources:
  AWS Config recorder: ON in all in-scope accounts
  CloudTrail management events: logging in all in-scope accounts

Delegations: all COMPLETE
