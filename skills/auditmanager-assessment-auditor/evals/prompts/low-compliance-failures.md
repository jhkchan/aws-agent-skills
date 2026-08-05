# Eval prompt: low-compliance-failures

Audit the following Audit Manager assessment configuration for evidence
completeness and compliance posture. Emit the standard VERDICT block
(ASSESSMENT, FRAMEWORK, VERDICT, REASON, CONTROL BREAKDOWN, FINDINGS,
REMEDIATION).

Assessment name: HIPAA-security-low-compliance-failures
Assessment id: arn:aws:auditmanager:us-east-1:111111111111:assessment/a-low-compliance-failures
Framework: HIPAA
Status: ACTIVE
Creation time: 2026-03-01
Last updated: 2026-08-04
Scope:
  awsAccounts: [111111111111, 222222222222]
  awsServices: [ec2, s3, iam, kms, rds, lambda]

Control statistics:
  total: 180
  PASS: 86
  FAIL: 79
  NOT_ASSESSED: 15
  MANUAL: 0
  UNDER_REVIEW: 0

Settings:
  kmsKey: arn:aws:kms:us-east-1:111111111111:key/hipaa-key
  snsTopic: arn:aws:sns:us-east-1:111111111111:hipaa-notify
  defaultAssessmentReportsDestination: s3://hipaa-reports/2026/
  defaultProcessOwners: [arn:aws:iam::111111111111:role/hipaa-reviewer]

Data sources:
  AWS Config recorder: ON in all in-scope accounts
  CloudTrail management events: logging in all in-scope accounts

Delegations: all COMPLETE
