# DMS Task Troubleshooter — diagnostic commands (moved from SKILL.md)

Loaded on demand — content moved verbatim from SKILL.md (progressive disclosure; nothing deleted).

## Pre-flight: account-wide commands (moved from SKILL.md)


```bash
# 1. Task config (status, migration type, table mappings, settings)
aws dms describe-replication-tasks \
  --filters Name=replication-task-id,Values=<task-id> --output json

# 2. Replication instance (class, engine version, multi-AZ, storage)
aws dms describe-replication-instances \
  --filters Name=replication-instance-id,Values=<inst-id> --output json

# 3. Endpoints (source and target engine type, server, port, SSL)
aws dms describe-endpoints \
  --filters Name=endpoint-arn,Values=<source-arn>,Values=<target-arn> --output json

# 4. Table statistics (per-table FullLoadRowCount, Insert/Delete/Update)
aws dms describe-table-statistics --replication-task-arn <task-arn> --output json

# 5. CloudWatch Logs for the task (the highest-signal source for errors)
aws logs filter-log-events \
  --log-group-name dms-task-<task-id> \
  --start-time $(date -u -d '-1 hour' +%s)000 \
  --filter-pattern "ERROR" --output json

# 6. CloudWatch metrics — CDC latency + instance capacity
aws cloudwatch get-metric-statistics --namespace AWS/DMS \
  --metric-name CDCLatencySource \
  --dimensions Name=ReplicationTaskIdentifier,Value=<task-id> \
  --start-time $(date -u -d '-1 hour' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Average,Maximum --output json
# (repeat for FreeableMemory, SwapUsage with ReplicationInstanceIdentifier)

# 7. IAM roles (dms-vpc-role, dms-cloudwatch-logs-role)
aws iam get-role --role-name dms-vpc-role --output json
aws iam get-role --role-name dms-cloudwatch-logs-role --output json

# 8. Source and target security groups (ingress rules)
aws ec2 describe-security-groups --group-ids <source-sg> <target-sg> --output json
```

