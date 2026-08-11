# Eval: iam-policy-access-point-enforcement

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — Allow with AP ARN condition + Deny on Null:AccessPointArn

## Prompt

Create an EFS access point "prod-app-ap" on fs-aaaabbbbcccc
(account 123456789012, region us-east-1). POSIX identity uid
2000, gid 2000, root /app, perms 0750. Attach a file-system
policy that enforces access-point-only mounts: allow
ClientMount + ClientWrite + ClientRootAccess through the AP
ARN condition, AND deny any mount that did NOT come through an
access point. All three AZs have mount targets;
amazon-efs-utils is installed on the EC2 hosts.
