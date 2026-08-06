# Eval prompt: healthy-org-admin-ok

Audit the following Amazon Detective investigation coverage posture for the
target region. Emit the standard VERDICT block (GRAPH, VERDICT, REASON,
FINDINGS, REMEDIATION).

Region: us-east-1
Account: 111111111111 (Organization admin, 4 total accounts)

Detective graph state:
  GraphArn: arn:aws:detective:us-east-1:111111111111:graph:healthy-org-admin-ok
  CreatedTime: 2024-09-01T10:00:00Z

Member accounts (list-members):
  - AccountId: 111111111111, Status: ENABLED
  - AccountId: 222222222222, Status: ENABLED
  - AccountId: 333333333333, Status: ENABLED
  - AccountId: 444444444444, Status: ENABLED

Data-source package states (batch-get-graph-member-datasources):
  111111111111: DETECTIVE_CORE: COLLECTING
  222222222222: DETECTIVE_CORE: COLLECTING, EKS_AUDIT: COLLECTING
  333333333333: DETECTIVE_CORE: COLLECTING
  444444444444: DETECTIVE_CORE: COLLECTING

Data freshness:
  111111111111: lastDataReceived: 2026-08-05T06:00:00Z (2 hours ago)
  222222222222: lastDataReceived: 2026-08-05T05:30:00Z (2.5 hours ago)
  333333333333: lastDataReceived: 2026-08-05T04:00:00Z (4 hours ago)
  444444444444: lastDataReceived: 2026-08-05T05:00:00Z (3 hours ago)

GuardDuty detector status:
  DetectorId: 12ab34cd56ef, Status: ENABLED

Organization configuration:
  DelegatedAdminAccountId: 111111111111
  AutoEnable: true
