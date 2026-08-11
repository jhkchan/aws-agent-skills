# Eval: efs-ap-with-posix-identity

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — AP with PosixUser + RootDirectory + CreationInfo + TLS mount

## Prompt

Create an EFS access point for file system fs-0abc123def
(account 123456789012, region us-east-1). AP name:
"team-a-ap". Root directory path: /data/team-a with auto-creation
(owner uid 1000, gid 1000, permissions 0750). POSIX user
identity: uid 1000, gid 1000, secondary gids 2000. The file
system has encryption at rest, bursting throughput, mount
targets in use1-az1, use1-az2, use1-az3, and Intelligent-Tiering
lifecycle (IA after 30 days). amazon-efs-utils is installed on
the EC2 ASG. Include TLS encryption in transit.
