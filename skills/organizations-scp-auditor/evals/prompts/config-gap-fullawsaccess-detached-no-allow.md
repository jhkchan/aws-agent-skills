# Eval prompt: config-gap-fullawsaccess-detached-no-allow

Audit the following Organizations SCP configuration for effective permission
exposure. Emit the standard VERDICT block (TARGET, VERDICT, REASON,
FINDINGS, REMEDIATION).

Organization structure for audit:

Root (r-config-gap-fullawsaccess-detached-no-allow):
  Attached SCPs:
    - (FullAWSAccess DETACHED — not present)
    - DenyLeaveOrg (p-config-gap-fullawsaccess-detached-no-allow-leave):
      {"Version":"2012-10-17","Statement":[{"Sid":"DenyLeave","Effect":"Deny","Action":"organizations:LeaveOrganization","Resource":"*"}]}

OU "Workloads" (ou-wkld-config-gap-fullawsaccess-detached-no-allow):
  Parent: Root
  Attached SCPs:
    - (FullAWSAccess DETACHED — not present at OU level)
    - DenyLeaveOrg: inherited from Root

Account 444444444444 "config-gap-fullawsaccess-detached-no-allow-app":
  Parent: OU "Workloads"
  Attached SCPs:
    - (FullAWSAccess DETACHED — not present at account level)
    - DenyLeaveOrg: inherited

Effective SCP evaluation for account 444444444444:
  - FullAWSAccess: NOT PRESENT in entire chain (detached at root, not inherited)
  - No Allow SCP (Allow * or otherwise) present anywhere in the chain
  - DenyLeaveOrg (Deny organizations:LeaveOrganization) — present, inherited
  - Result: NO Allow SCP in effective set. Every action is implicitly denied at SCP layer.
  - All IAM permissions filtered out -> uniform AccessDenied across all services.

Target being audited: Account 444444444444 (config-gap-fullawsaccess-detached-no-allow-app)
