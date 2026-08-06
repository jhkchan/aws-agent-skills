# Eval prompt: hybrid-mi-connection-lost-unmanaged

Audit the following SSM managed-instance configuration for coverage,
association compliance, patch baseline adherence, Session Manager vs SSH
exposure, and inventory collection. Emit the standard VERDICT block
(INSTANCE, VERDICT, REASON, FINDINGS, REMEDIATION).

Instance id: mi-hybridconnectionlostu
describe-instance-information:
  InstanceId: mi-hybridconnectionlostu
  ResourceType: ManagedInstance
  PingStatus: ConnectionLost
  LastPingDateTime: 2026-07-27T03:14:22Z
  PlatformType: Linux
  IamRoleARN: arn:aws:iam::111111111111:role/AmazonSSMManagedInstanceCore-Role
  IsLatestVersion: true

Snapshot date: 2026-08-05. (LastPingDateTime is ~9 days stale.)
