# Worked Examples — ElastiCache Cache Deployer

Secondary worked examples moved verbatim from SKILL.md. Loaded on demand.

## Worked example — provisioned Redis cluster mode enabled with Multi-AZ (from SKILL.md)

A production 3-shard Redis cluster with 1 replica per shard, Multi-AZ,
TLS + AUTH, customer CMK, snapshots, and CloudWatch alarms. This is
the canonical production pattern.

```bash
# 1. Create the subnet group (must span >=2 AZs)
aws elasticache create-cache-subnet-group \
  --cache-subnet-group-name prod-cache-subnet \
  --cache-subnet-group-description "Multi-AZ subnet group for prod cache" \
  --subnet-ids subnet-0aaa subnet-0bbb subnet-0ccc

# 2. Create the parameter group
aws elasticache create-cache-parameter-group \
  --cache-parameter-group-name prod-redis-pg \
  --cache-parameter-group-family redis6.x \
  --description "Production Redis parameter group"

aws elasticache modify-cache-parameter-group \
  --cache-parameter-group-name prod-redis-pg \
  --parameter-name-values \
    ParameterName=maxmemory-policy,ParameterValue=allkeys-lru \
    ParameterName=timeout,ParameterValue=300 \
    ParameterName=tcp-keepalive,ParameterValue=60

# 3. Generate AUTH token and store in Secrets Manager
AUTH_TOKEN=$(openssl rand -base64 24)
aws secretsmanager create-secret \
  --name prod-cache-auth-token \
  --secret-string "$AUTH_TOKEN"

# 4. Create the replication group with cluster mode enabled + Multi-AZ + TLS + AUTH
aws elasticache create-replication-group \
  --replication-group-id prod-cache \
  --replication-group-description "Production Redis cluster" \
  --engine redis \
  --cache-node-type cache.r6g.2xlarge \
  --cache-parameter-group-name prod-redis-pg \
  --cache-subnet-group-name prod-cache-subnet \
  --security-group-ids sg-cache123 \
  --num-node-groups 3 \
  --replicas-per-node-group 1 \
  --automatic-failover-enabled \
  --multi-az-enabled \
  --transit-encryption-enabled \
  --at-rest-encryption-enabled \
  --kms-key-id arn:aws:kms:us-east-1:123456789012:alias/prod-cache-kms \
  --auth-token "$AUTH_TOKEN" \
  --snapshot-retention-limit 7 \
  --snapshot-window "03:00-05:00" \
  --maintenance-window "sun:05:00-sun:07:00" \
  --tags Key=Environment,Value=production Key=Workload,Value=cache

# 5. Wait for the replication group to become available
aws elasticache wait replication-group-available --replication-group-id prod-cache

# 6. Verify
aws elasticache describe-replication-groups --replication-group-id prod-cache
aws elasticache describe-cache-clusters --cache-cluster-id prod-cache-0001 --show-cache-node-info
aws kms describe-key --key-id alias/prod-cache-kms

# 7. CloudWatch alarms
aws cloudwatch put-metric-alarm \
  --alarm-name "prod-cache-cpu-high" \
  --namespace AWS/ElastiCache \
  --metric-name CPUUtilization \
  --dimensions Name=CacheClusterId,Value=prod-cache-0001 \
  --statistic Average --period 60 --threshold 90 \
  --comparison-operator GreaterThan --evaluation-periods 5 \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:cache-alerts

aws cloudwatch put-metric-alarm \
  --alarm-name "prod-cache-swap" \
  --namespace AWS/ElastiCache \
  --metric-name SwapUsage \
  --dimensions Name=CacheClusterId,Value=prod-cache-0001 \
  --statistic Average --period 60 --threshold 0 \
  --comparison-operator GreaterThan --evaluation-periods 1 \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:cache-alerts
```

The checklist for this cluster:

```text
CACHE: prod-cache
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Engine: redis
  [✓] Cluster mode: ENABLED (3 shards)
  [✓] Node type: cache.r6g.2xlarge (62.34 GiB nominal; 31.17 GiB usable per shard; 93.51 GiB total usable)
  [✓] Replicas: 1 per shard (3 total) — Multi-AZ failover
  [✓] Multi-AZ with automatic failover: Enabled
  [✓] Subnet group: prod-cache-subnet (3 AZs)
  [✓] Security group: sg-cache123 (inbound 6379 from sg-app456)
  [✓] Encryption at rest: Enabled (customer CMK alias/prod-cache-kms)
  [✓] Encryption in transit (TLS): Enabled
  [✓] AUTH token: Enabled (24-char base64 in Secrets Manager)
  [✓] Parameter group: prod-redis-pg (maxmemory-policy=allkeys-lru)
  [✓] Snapshot retention: 7 days (03:00-05:00 UTC)
  [✓] Maintenance window: sun:05:00-sun:07:00
  [✓] Global Datastore: Single-region
  [✓] ElastiCache Serverless: No
VERIFICATION_COMMANDS:
  aws elasticache describe-replication-groups --replication-group-id prod-cache
  aws elasticache describe-cache-clusters --cache-cluster-id prod-cache-0001 --show-cache-node-info
  aws elasticache describe-cache-parameter-groups --cache-parameter-group-name prod-redis-pg
  aws kms describe-key --key-id alias/prod-cache-kms
```
