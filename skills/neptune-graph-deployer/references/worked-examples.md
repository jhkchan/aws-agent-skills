# Neptune Graph Deployer — Worked Examples

Secondary worked examples moved verbatim from SKILL.md. The primary
Perfect example lives in SKILL.md under the STRICT output contract.

## Worked example — Neptune cluster with Gremlin, encryption, IAM auth, Streams, and read replicas

```text
NEPTUNE: my-neptune-prod (db.r5.4xlarge, 1.3.2.1)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Query language: Gremlin (primary), SPARQL (available)
  [✓] Topology: Primary + 2 read replicas (across 3 AZs)
  [✓] Instance type: db.r5.4xlarge (128 GB, 8000 baseline IOPS)
  [✓] Subnet group: my-neptune-subnet-group (3 AZs)
  [✓] Security group: sg-aaa11122 (port 8182)
  [✓] Parameter group: my-neptune-params (neptune_enforce_ssl=1, neptune_query_timeout=120000, neptune_streams=1)
  [✓] IAM database authentication: Enabled
  [✓] At-rest encryption (KMS): Enabled (key arn:aws:kms:us-east-1:...:key/aaa11122)
  [✓] Neptune Streams: Enabled (filter: {"op": ["ADD","UPDATE","REMOVE"]})
  [✓] Neptune ML: Not configured
  [✓] Global Database: Not configured
  [✓] Auto-scaling: Target tracking (EngineCPUUtilization, target 60%, min 1, max 5)
  [✓] Backup: Automated (retention 7 days, window 03:00-04:00 UTC)
  [✓] Snapshot window: 03:00-04:00 UTC (no overlap with maintenance mon:05:00-mon:06:00)
  [✓] Bulk loader: Ready (S3 s3://my-neptune-data/, IAM role arn:aws:iam::...:role/NeptuneBulkLoadRole)
  [✓] Tags: Environment=production, Application=fraud-detection
VERIFICATION_COMMANDS:
  aws neptune describe-db-clusters --db-cluster-identifier my-neptune-prod --region us-east-1
  aws neptune describe-db-instances --db-instance-identifier my-neptune-primary --region us-east-1
  aws cloudwatch get-metric-statistics --namespace AWS/Neptune --metric-name EngineCPUUtilization --dimensions Name=DBInstanceIdentifier,Value=my-neptune-primary --region us-east-1
```
