# Eval: cross-region-backup-copy

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — CopyBackupToRegion to us-west-2; one-way copy; restore creates a new cluster, not a hot replica

## Prompt

Configure cross-region backup copy for CloudHSM cluster
cluster-abc123def from us-east-1 to us-west-2. Destination region
is enabled for CloudHSM. Restore in us-west-2 should create a new
cluster from the copied backup.
