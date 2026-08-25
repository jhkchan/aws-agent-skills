# Error Handling — S3 Outposts Deployer

Error-handling deep dives moved from SKILL.md. Load on demand.

## Error handling

### Cannot access Outpost S3 bucket (connection timeout)
- Missing or unavailable endpoint. Verify the endpoint exists and is
  in `Available` state. Verify the security group allows port 443
  from the client.

### InsufficientStorageCapacity
- Outpost storage is full. Free space by deleting objects (via
  lifecycle expiration) or replicating to cloud and deleting local
  copies. Outpost storage cannot be elastically expanded.

### KMS encryption fails
- SSE-KMS is NOT supported on Outposts. Use SSE-S3 (default). For KMS,
  replicate to cloud S3.

### Object lock cannot be enabled
- Object lock must be enabled at bucket creation. If the bucket
  already exists without it, create a new bucket with
  `--object-lock-enabled-for-bucket` and migrate objects.

### Replication not working
- Verify the replication IAM role has permissions on both source
  (Outpost bucket) and destination (cloud bucket). Verify the role
  trust policy allows `s3-outposts.amazonaws.com` to assume it.

