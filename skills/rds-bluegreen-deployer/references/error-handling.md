# RDS Blue/Green Deployer — error handling (moved from SKILL.md)

Loaded on demand — content moved verbatim from SKILL.md (progressive disclosure; nothing deleted).

## Error handling (moved from SKILL.md)

### Green creation fails (unsupported upgrade path)
- The major version upgrade path is not supported (e.g., skipping two
  major versions). Check AWS docs for supported upgrade paths. Upgrade
  incrementally.

### Green creation fails (RDS Custom)
- RDS Custom does NOT support Blue/Green. Use standard
  `modify-db-instance` for RDS Custom databases.

### Replication lag is high
- Large transactions or heavy write load on blue can cause lag. Wait
  for lag to decrease before switchover. If lag persists, reduce write
  load on blue temporarily.

### Switchover fails (timeout)
- The switchover exceeded the timeout. It rolls back — blue remains
  production. Increase the switchover timeout and retry. Check for
  long-running transactions blocking the switchover.

### Application errors after switchover
- Applications without retry logic see connection errors. Implement
  connection retry logic. For DNS caching issues, flush the DNS cache
  on application servers.

### Blue/Green left running (2x billing)
- After switchover, the former blue (new green) continues running.
  Delete it with `delete-blue-green-deployment --delete-target` to
  stop the 2x cost.

