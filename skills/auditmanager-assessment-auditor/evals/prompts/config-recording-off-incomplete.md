# Eval prompt: config-recording-off-incomplete

Audit the following Audit Manager assessment configuration for evidence
completeness and compliance posture. Emit the standard VERDICT block
(ASSESSMENT, FRAMEWORK, VERDICT, REASON, CONTROL BREAKDOWN, FINDINGS,
REMEDIATION).

Assessment name: PCI-DSS-annual-config-recording-off-incomplete
Assessment id: arn:aws:auditmanager:us-east-1:111111111111:assessment/a-config-recording-off-incomplete
Framework: PCI DSS
Status: ACTIVE
Creation time: 2026-01-01
Last updated: 2026-08-04
Scope:
  awsAccounts: [111111111111, 222222222222, 333333333333]
  awsServices: [ec2, s3, iam, kms, rds, vpc, config]

Control statistics:
  total: 220
  PASS: 80
  FAIL: 22
  NOT_ASSESSED: 99
  MANUAL: 12
  UNDER_REVIEW: 7

Settings:
  kmsKey: arn:aws:kms:us-east-1:111111111111:key/pci-audit-key
  snsTopic: arn:aws:sns:us-east-1:111111111111:pci-audit-notify
  defaultAssessmentReportsDestination: s3://pci-audit-reports/2026/
  defaultProcessOwners: [arn:aws:iam::111111111111:role/pci-reviewer]

Data sources:
  AWS Config recorder: OFF in account 222222222222 (recording: false), ON in others
  CloudTrail management events: logging in all in-scope accounts

Delegations: all COMPLETE
