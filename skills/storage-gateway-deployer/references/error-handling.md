# Error Handling — Storage Gateway Deployer

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Error handling

### Gateway activation fails — invalid activation key
- The activation key expires shortly after generation. Reconnect to
  the gateway VM activation endpoint to generate a new key, then
  retry `activate-gateway` immediately.

### File share creation fails — IAM role missing S3 permissions
- The IAM role must have `s3:GetObject`, `s3:PutObject`,
  `s3:DeleteObject`, and `s3:ListBucket` on the target bucket. Add
  the required policy and retry.

### SMB AD join fails — domain unreachable
- Verify DNS resolution of the domain controller, network ports
  53/88/389/445/464/3268, and service account domain-join perms.

### Volume Gateway iSCSI connection fails
- Verify the iSCSI initiator can reach the gateway IP on port 3260.
  Run `iscsiadm --mode discovery` to verify target visibility.

### CacheHitPercent alarm fires
- The cache is too small for the working set. Double the cache size
  via `add-cache` and re-evaluate after 24 hours.

### Upload buffer full — writes blocked
- The upload buffer is undersized. Add more disks via
  `add-upload-buffer`. Check if bandwidth limits are throttling uploads.
