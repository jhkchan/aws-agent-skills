# Eval: missing-mount-target-az

**Difficulty:** medium
**Branch:** PREREQUISITES_MISSING — mount target absent in us-west-2c

## Prompt

Create an EFS access point "internal-logs-ap" for file system
fs-998877 in account 123456789012 region us-west-2. Compute
runs in us-west-2a, us-west-2b, and us-west-2c, but I just
checked and mount targets exist only in 2a and 2b. File system
has encryption at rest. POSIX uid 1001, gid 1001, root path
/logs. Add the IAM file-system policy that forces
access-point-only mounts.
