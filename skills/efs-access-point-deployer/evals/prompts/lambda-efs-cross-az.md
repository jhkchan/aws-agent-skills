# Eval: lambda-efs-cross-az

**Difficulty:** hard
**Branch:** PREREQUISITES_MISSING — Lambda subnet in use1-az2 has no corresponding mount target

## Prompt

Configure Lambda function "file-processor" to mount EFS file
system fs-eeeeffff0000 (account 123456789012, region
us-east-1) via access point fsap-9999aaaa2222 at
/mnt/efs. The function's VPC config has subnets in use1-az1
(subnet-aaa) and use1-az2 (subnet-bbb). I just checked and the
EFS has a mount target only in use1-az1. The function execution
role has ClientMount + ClientWrite + ClientRootAccess. Make
sure the mount works in both AZs.
