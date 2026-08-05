# Eval prompt: noncompliant-critical-patches-missing

Audit the following SSM managed-instance configuration for coverage,
association compliance, patch baseline adherence, Session Manager vs SSH
exposure, and inventory collection. Emit the standard VERDICT block
(INSTANCE, VERDICT, REASON, FINDINGS, REMEDIATION).

Instance id: i-0noncompliantcriticalpatches
describe-instance-information:
  InstanceId: i-0noncompliantcriticalpatches
  ResourceType: EC2Instance
  PingStatus: Active
  LastPingDateTime: 2026-08-05T04:12:00Z
  PlatformType: Linux
  IamRoleARN: arn:aws:iam::111111111111:role/AmazonSSMManagedInstanceCore-Role
  IsLatestVersion: true

Association status (AWS-ApplyPatchBaseline Operation=Scan):
  Status: Success
  ExecutionTime: 2026-08-05T03:00:00Z

Patch state (list-compliance-items):
  ComplianceStatus: NON_COMPLIANT
  PatchBaselineId: pb-0prodlinuxsecurity
  MissingCount: 14
  InstalledCount: 312
  InstalledRejectedCount: 2
  Severity of missing patches: CRITICAL

Session Manager: sg-0internalonly (no inbound 0.0.0.0/0 on TCP/22);
recent active Session Manager session on 2026-08-04.
Inventory: AWS-GatherSoftwareInventory association present, last run
2026-08-05T02:00:00Z.
