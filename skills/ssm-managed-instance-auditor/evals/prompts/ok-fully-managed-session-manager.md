# Eval prompt: ok-fully-managed-session-manager

Audit the following SSM managed-instance configuration for coverage,
association compliance, patch baseline adherence, Session Manager vs SSH
exposure, and inventory collection. Emit the standard VERDICT block
(INSTANCE, VERDICT, REASON, FINDINGS, REMEDIATION).

Instance id: i-0okfullymanagedsessma
describe-instance-information:
  InstanceId: i-0okfullymanagedsessma
  ResourceType: EC2Instance
  PingStatus: Active
  LastPingDateTime: 2026-08-05T04:16:00Z
  PlatformType: Linux
  IamRoleARN: arn:aws:iam::111111111111:role/AmazonSSMManagedInstanceCore-Role
  AgentVersion: 3.1.161.0
  IsLatestVersion: true

Associations:
  AWS-ApplyPatchBaseline (Operation=Scan): Success, last run 2026-08-05T03:00:00Z
  AWS-UpdateSSMAgent: Success, last run 2026-08-05T02:00:00Z
  AWS-GatherSoftwareInventory: Success, last run 2026-08-05T02:30:00Z

Patch state: COMPLIANT, MissingCount: 0.
Session Manager (describe-sessions --state Active): one active session,
started 2026-08-05T03:45:00Z.
Session Manager preferences: S3 logging to
ssm-session-audit-111111111111, CloudWatch Logs group
/ssm/session-logs, KMS key alias/ssm-session-encryption.
Security group: no inbound TCP/22 from 0.0.0.0/0 (Session Manager is
the sole access path).
