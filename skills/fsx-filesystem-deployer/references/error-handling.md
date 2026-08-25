# Error Handling — FSx Filesystem Deployer

Error-handling deep dives moved verbatim from SKILL.md for progressive disclosure. Load on demand.

## Error handling (moved from SKILL.md)

### File system stuck in CREATING state
- File system creation can take 10-60 minutes depending on type and
  size. If it stays in CREATING beyond expected time, check subnet
  configuration, AD integration (for Windows), and IAM permissions.

### AD domain join failure (Windows)
- The directory may not be ACTIVE, or the security group may block
  required AD ports (53, 88, 389, 445). Verify the directory status
  and security group rules.

### S3 export/import not working (Lustre)
- The S3 bucket may not exist, or the IAM permissions may be
  incorrect. Verify the bucket is in the same region and the FSx
  service role has read/write access to the bucket.

### Multi-AZ failover not working
- The standby may not be in a different AZ, or the security group
  may block inter-AZ traffic. Verify both subnets are in different
  AZs and the security group allows traffic on required ports.

### Throughput capacity change failed
- The new throughput value may not be a valid step, or a maintenance
  window is required. Verify the throughput step is valid and
  schedule the change during a maintenance window.

