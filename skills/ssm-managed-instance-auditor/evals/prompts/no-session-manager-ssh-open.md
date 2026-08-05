# Eval prompt: no-session-manager-ssh-open

Audit the following SSM managed-instance configuration for coverage,
association compliance, patch baseline adherence, Session Manager vs SSH
exposure, and inventory collection. Emit the standard VERDICT block
(INSTANCE, VERDICT, REASON, FINDINGS, REMEDIATION).

Instance id: i-0nossessionmanagersshopen
describe-instance-information:
  InstanceId: i-0nossessionmanagersshopen
  ResourceType: EC2Instance
  PingStatus: Active
  LastPingDateTime: 2026-08-05T04:14:00Z
  PlatformType: Linux
  IamRoleARN: arn:aws:iam::111111111111:role/AmazonSSMManagedInstanceCore-Role
  IsLatestVersion: true

Association status: all Success.
Patch state:
  ComplianceStatus: COMPLIANT
  MissingCount: 0
Inventory: AWS-GatherSoftwareInventory present, last run fresh.

Security group (describe-security-groups):
  GroupId: sg-0sshexposed
  IpPermissions:
    - FromPort: 22
      ToPort: 22
      IpProtocol: tcp
      IpRanges:
        - CidrIp: 0.0.0.0/0

Session Manager (describe-sessions --state Active): no sessions.
Session Manager (describe-sessions history, last 30 days): no sessions.
