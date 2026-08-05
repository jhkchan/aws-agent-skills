# Eval prompt: config-gap-stale-agent-no-inventory

Audit the following SSM managed-instance configuration for coverage,
association compliance, patch baseline adherence, Session Manager vs SSH
exposure, and inventory collection. Emit the standard VERDICT block
(INSTANCE, VERDICT, REASON, FINDINGS, REMEDIATION).

Instance id: i-0configgapstaleagentnoinv
describe-instance-information:
  InstanceId: i-0configgapstaleagentnoinv
  ResourceType: EC2Instance
  PingStatus: Active
  LastPingDateTime: 2026-08-05T04:15:00Z
  PlatformType: Linux
  IamRoleARN: arn:aws:iam::111111111111:role/AmazonSSMManagedInstanceCore-Role
  AgentVersion: 3.0.225.0
  IsLatestVersion: false

Association status:
  AWS-ApplyPatchBaseline (Operation=Scan): Success
  AWS-UpdateSSMAgent: NOT PRESENT (no auto-update association)
  AWS-GatherSoftwareInventory: NOT PRESENT

Patch state: COMPLIANT, MissingCount: 0.
Session Manager: most recent session 2026-08-04 (active within 30 days).
No inbound 0.0.0.0/0 on TCP/22.
