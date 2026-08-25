# ECR Replication Deployer — error handling (moved from SKILL.md)

Loaded on demand — content moved verbatim from SKILL.md (progressive disclosure; nothing deleted).
## Error handling (moved from SKILL.md)

### Replication not working (images not appearing in destination)
- Verify the destination registry ID is correct (12-digit account ID).
- For cross-account, verify the destination has not disabled
  replication (check registry settings).
- Check CloudWatch `ImageReplicationStatus` for `FAILED` status.

### Pull-through cache pull fails
- Verify the upstream registry URL is one of the supported types.
- Verify the ECR repository prefix matches the cache rule.
- Check network connectivity to the upstream registry.

### Batch delete fails on a replicated image
- Replicated images are read-only. Delete the image at the source
  first, then delete the orphaned replica in the destination.

### Storage costs higher than expected
- Each destination region adds storage cost. Apply lifecycle policies
  in BOTH source and destinations to prune old images.
- Check for orphaned replicas (source image deleted but replica
  remains). These still incur storage cost.
