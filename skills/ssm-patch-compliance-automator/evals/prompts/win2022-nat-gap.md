# Eval prompt: win2022-nat-gap

Design a patch-compliance automation workflow for the following Windows
Server fleet. Emit the standard PATCH block.

Design reference: win2022-nat-gap
Account: 111111111111
Region: us-east-1

Fleet: 45 Windows Server 2022 instances (prod, private VPC)
VPC has no NAT gateway, no WSUS server, no VPC endpoints for Windows Update.
Instances tagged: "Patch Group" = "win2022-prod"
SSM agent: all Online
Desired baseline: win2022-prod-baseline
  - MSRC Critical/Important: ApproveAfterDays 3
Maintenance window: weekly Sunday 02:00 UTC, 6 hours
