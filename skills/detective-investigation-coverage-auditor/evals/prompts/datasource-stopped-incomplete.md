# Eval prompt: datasource-stopped-incomplete

Audit the following Amazon Detective investigation coverage posture for the
target region. Emit the standard VERDICT block (GRAPH, VERDICT, REASON,
FINDINGS, REMEDIATION).

Region: us-east-1
Account: 111111111111 (Organization admin, 3 total accounts)

Detective graph state:
  GraphArn: arn:aws:detective:us-east-1:111111111111:graph:datasource-stopped-incomplete
  CreatedTime: 2025-03-10T08:00:00Z

Member accounts (list-members):
  - AccountId: 111111111111, Status: ENABLED
  - AccountId: 222222222222, Status: ENABLED
  - AccountId: 333333333333, Status: ENABLED

Data-source package states (batch-get-graph-member-datasources):
  111111111111: DETECTIVE_CORE: COLLECTING
  222222222222: DETECTIVE_CORE: COLLECTING
  333333333333: DETECTIVE_CORE: STOPPED

Data freshness:
  111111111111: lastDataReceived: 2026-08-05T06:00:00Z (2 hours ago)
  222222222222: lastDataReceived: 2026-08-05T05:30:00Z (2.5 hours ago)
  333333333333: lastDataReceived: 2026-07-28T12:00:00Z (8 days ago)

GuardDuty detector status:
  DetectorId: ab12cd34, Status: ENABLED

Organization configuration:
  DelegatedAdminAccountId: 111111111111
  AutoEnable: true
