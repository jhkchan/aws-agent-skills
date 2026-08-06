# Eval prompt: invitation-pending-incomplete

Audit the following Amazon Detective investigation coverage posture for the
target region. Emit the standard VERDICT block (GRAPH, VERDICT, REASON,
FINDINGS, REMEDIATION).

Region: us-east-1
Account: 111111111111 (Organization admin, 5 total accounts)

Detective graph state:
  GraphArn: arn:aws:detective:us-east-1:111111111111:graph:invitation-pending-incomplete
  CreatedTime: 2025-06-15T10:00:00Z

Member accounts (list-members):
  - AccountId: 111111111111, Status: ENABLED
  - AccountId: 222222222222, Status: ENABLED, DETECTIVE_CORE: COLLECTING
  - AccountId: 333333333333, Status: ENABLED, DETECTIVE_CORE: COLLECTING
  - AccountId: 444444444444, Status: INVITED, InvitedTime: 2026-07-15T10:00:00Z (21 days ago)
  - AccountId: 555555555555, Status: INVITED, InvitedTime: 2026-05-20T10:00:00Z (77 days ago — likely expired)

Data-source package states (batch-get-graph-member-datasources):
  222222222222: DETECTIVE_CORE: COLLECTING
  333333333333: DETECTIVE_CORE: COLLECTING

GuardDuty detector status:
  DetectorId: 12abc34d567e, Status: ENABLED

Organization configuration:
  DelegatedAdminAccountId: 111111111111
  AutoEnable: true
