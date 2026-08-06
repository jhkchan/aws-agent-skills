# Eval prompt: config-gap-guardduty-disabled

Audit the following Amazon Detective investigation coverage posture for the
target region. Emit the standard VERDICT block (GRAPH, VERDICT, REASON,
FINDINGS, REMEDIATION).

Region: us-east-1
Account: 111111111111 (Organization admin, 2 total accounts)

Detective graph state:
  GraphArn: arn:aws:detective:us-east-1:111111111111:graph:config-gap-guardduty-disabled
  CreatedTime: 2025-01-15T10:00:00Z

Member accounts (list-members):
  - AccountId: 111111111111, Status: ENABLED
  - AccountId: 222222222222, Status: ENABLED

Data-source package states (batch-get-graph-member-datasources):
  111111111111: DETECTIVE_CORE: COLLECTING
  222222222222: DETECTIVE_CORE: COLLECTING

Data freshness:
  111111111111: lastDataReceived: 2026-08-05T06:00:00Z (2 hours ago)
  222222222222: lastDataReceived: 2026-08-05T05:00:00Z (3 hours ago)

GuardDuty detector status:
  DetectorId: ef56gh78, Status: DISABLED

Organization configuration:
  DelegatedAdminAccountId: 111111111111
  AutoEnable: true
