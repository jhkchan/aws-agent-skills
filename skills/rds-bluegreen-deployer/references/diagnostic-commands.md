# RDS Blue/Green Deployer — diagnostic commands (moved from SKILL.md)

Loaded on demand — content moved verbatim from SKILL.md (progressive disclosure; nothing deleted).

## Step 11 — Monitoring during green validation (moved from SKILL.md)

During green validation, monitor key CloudWatch metrics to ensure
green is healthy and replication is lag-free.

| Metric | What it tells you | Target |
|---|---|---|
| `DatabaseConnections` (green) | Green accepts connections | > 0 during validation |
| `ReplicaLag` | Replication lag from blue to green | < 1 second (near-zero) |
| `CPUUtilization` (green) | Green CPU after changes | Within normal range |
| `FreeableMemory` (green) | Green memory after changes | Within normal range |
| `ReadLatency` / `WriteLatency` (green) | Green query performance | No regression vs blue |
| `FreeStorageSpace` (green) | Green has enough storage | > 20% free |

**Monitor via CLI:**

```bash
# Check replication status
aws rds describe-blue-green-deployments \
  --blue-green-deployment-identifier "$BG_ID" \
  --query 'BlueGreenDeployments[0].{Status:Status,Source:Source,Target:Target}' \
  --region us-east-1 --output table

# Check green DB health
aws rds describe-db-instances \
  --db-instance-identifier "green-prod-mysql-db" \
  --query 'DBInstances[0].{Status:DBInstanceStatus,Engine:Engine,EngineVersion:EngineVersion,Class:DBInstanceClass}' \
  --region us-east-1 --output table
```

