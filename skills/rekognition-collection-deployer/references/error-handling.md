# Error Handling — Rekognition Collection Deployer

Error-handling deep dives moved out of the SKILL.md body. Loaded on demand.


### Rate limiting (TPS)

Rekognition has per-account, per-region TPS limits. When exceeded,
returns `ThrottlingException`. Implement exponential backoff. Index and
search share the same TPS quota — heavy indexing throttles search.


## Error handling

### Collection already exists
- Use `describe-collection` to verify. Choose a different ID or delete
  the existing one with `delete-collection` (removes all faces).

### KMS access denied
- The KMS key policy must allow `rekognition.amazonaws.com` to call
  `kms:Decrypt` and `kms:GenerateDataKey`.

### Stream processor fails to start
- Verify the IAM role has all three permissions. Check both Kinesis
  streams are ACTIVE.

### ThrottlingException
- TPS limit exceeded. Implement exponential backoff. Schedule indexing
  off-peak or request quota increase.

### Low face match quality
- Increase threshold to 85-90%. Verify image quality. Partition if
  collection exceeds 1M faces.

### Custom labels model too expensive
- Stop model when not in use. Schedule inference windows via
  EventBridge auto-start/stop.
