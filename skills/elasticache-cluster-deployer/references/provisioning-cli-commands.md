# Provisioning CLI Commands

See SKILL.md for full command reference.

## Key Creation Commands

Refer to SKILL.md Quick Navigation and Configuration Dependency Graph.

## Step 2 — non-cluster (self-designed) create command (from SKILL.md)

```bash
aws elasticache create-replication-group \
  --replication-group-id my-redis-non-cluster \
  --engine redis \
  --cache-node-type cache.r6g.large \
  --num-cache-clusters 2 \
  --cache-subnet-group-name my-subnet-group \
  --security-group-ids sg-aaa11122 \
  --automatic-failover-enabled --multi-az-enabled
```

## Step 2 — cluster mode enabled create command (from SKILL.md)

```bash
aws elasticache create-replication-group \
  --replication-group-id my-redis-cluster \
  --engine redis \
  --cache-node-type cache.r6g.large \
  --num-node-groups 3 --replicas-per-node-group 1 \
  --cache-subnet-group-name my-subnet-group \
  --security-group-ids sg-aaa11122 \
  --automatic-failover-enabled --multi-az-enabled \
  --cache-parameter-group-name my-param-group
```

## Step 3 — multi-AZ failover enable commands (from SKILL.md)

```bash
# At creation (recommended):
aws elasticache create-replication-group \
  --replication-group-id my-redis-ha \
  --engine redis --cache-node-type cache.r6g.large \
  --num-node-groups 3 --replicas-per-node-group 1 \
  --automatic-failover-enabled --multi-az-enabled \
  --cache-subnet-group-name my-subnet-group \
  --security-group-ids sg-aaa11122

# Modify existing:
aws elasticache modify-replication-group \
  --replication-group-id my-redis-ha \
  --automatic-failover-enabled --multi-az-enabled --apply-immediately
```

## Step 5 — create subnet group command (from SKILL.md)

```bash
aws elasticache create-cache-subnet-group \
  --cache-subnet-group-name my-cache-subnet-group \
  --cache-subnet-group-description "ElastiCache subnet group" \
  --subnet-ids subnet-aaa11122 subnet-bbb22233 subnet-ccc33344
```

## Step 5 — security group create + ingress commands (from SKILL.md)

```bash
SG_ID=$(aws ec2 create-security-group \
  --group-name elasticache-redis-sg --description "ElastiCache Redis SG" \
  --vpc-id vpc-aaa11122 --query 'GroupId' --output text)

aws ec2 authorize-security-group-ingress \
  --group-id "$SG_ID" --protocol tcp --port 6379 \
  --source-security-group-id sg-app11122
```

## Step 6 — parameter group create + modify commands (from SKILL.md)

```bash
aws elasticache create-cache-parameter-group \
  --cache-parameter-group-name my-redis-params \
  --cache-parameter-group-family redis6.x \
  --description "Custom Redis parameters"

aws elasticache modify-cache-parameter-group \
  --cache-parameter-group-name my-redis-params \
  --parameter-name-values ParameterName=maxmemory-policy,ParameterValue=allkeys-lru
```

## Step 7 — encrypted replication group create command (from SKILL.md)

```bash
aws elasticache create-replication-group \
  --replication-group-id my-redis-encrypted \
  --engine redis --cache-node-type cache.r6g.large \
  --num-node-groups 3 --replicas-per-node-group 1 \
  --at-rest-encryption-enabled \
  --kms-key-id arn:aws:kms:us-east-1:123456789012:key/aaa11122 \
  --transit-encryption-enabled \
  --cache-subnet-group-name my-subnet-group \
  --security-group-ids sg-aaa11122
```

## Step 8 — AUTH token create + Secrets Manager commands (from SKILL.md)

```bash
aws elasticache create-replication-group \
  --replication-group-id my-redis-auth \
  --engine redis --cache-node-type cache.r6g.large \
  --num-node-groups 3 --replicas-per-node-group 1 \
  --transit-encryption-enabled \
  --auth-token "MyStr0ngT0k3n!2026" \
  --cache-subnet-group-name my-subnet-group \
  --security-group-ids sg-aaa11122

# Store token in Secrets Manager for rotation
aws secretsmanager create-secret \
  --name elasticache/redis-auth-token \
  --secret-string "MyStr0ngT0k3n!2026"
```

## Step 9 — backup-enabled create + manual snapshot commands (from SKILL.md)

```bash
aws elasticache create-replication-group \
  --replication-group-id my-redis-backup \
  --engine redis --cache-node-type cache.r6g.large \
  --num-cache-clusters 2 \
  --snapshot-retention-limit 7 \
  --snapshot-window "03:00-05:00" \
  --cache-subnet-group-name my-subnet-group \
  --security-group-ids sg-aaa11122

# Manual snapshot
aws elasticache create-snapshot \
  --snapshot-name my-manual-snapshot-20260805 \
  --replication-group-id my-redis-backup
```

## Step 10 — Global Datastore three-region commands (from SKILL.md)

```bash
# Step 1: Create primary in region A with global suffix
aws elasticache create-replication-group \
  --replication-group-id my-redis-global-primary \
  --engine redis --cache-node-type cache.r6g.large \
  --num-node-groups 3 --replicas-per-node-group 1 \
  --global-replication-group-suffix-group-id my-global \
  --cache-subnet-group-name my-subnet-useast \
  --security-group-ids sg-useast111 --region us-east-1

# Step 2: Create the Global Datastore
aws elasticache create-global-replication-group \
  --global-replication-group-id my-global-datastore \
  --primary-replication-group-id my-redis-global-primary \
  --global-replication-group-description "Cross-region DR" \
  --region us-east-1

# Step 3: Add secondary in region B
aws elasticache create-replication-group \
  --replication-group-id my-redis-global-secondary \
  --global-replication-group-id <global-id-fqn> \
  --cache-subnet-group-name my-subnet-euwest \
  --security-group-ids sg-euwest111 --region eu-west-1
```

## Step 11 — auto-scaling register + target tracking commands (from SKILL.md)

```bash
# Register scalable target (shard count)
aws application-autoscaling register-scalable-target \
  --service-namespace elasticache \
  --resource-id replication-group/my-redis-cluster \
  --scalable-dimension elasticache:replication-group:NodeGroups \
  --min-capacity 3 --max-capacity 10

# Target tracking policy
aws application-autoscaling put-scaling-policy \
  --service-namespace elasticache \
  --resource-id replication-group/my-redis-cluster \
  --scalable-dimension elasticache:replication-group:NodeGroups \
  --policy-name my-scaling-policy --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{"PredefinedMetricSpecification":{"PredefinedMetricType":"ElastiCachePrimaryEngineCPUUtilization"},"TargetValue":60.0,"ScaleOutCooldown":300,"ScaleInCooldown":300}'
```

## Step 12 — online resharding scale out/in commands (from SKILL.md)

```bash
# Scale out (add shards)
aws elasticache modify-replication-group-shard-configuration \
  --replication-group-id my-redis-cluster \
  --node-group-count 5 --apply-immediately

# Scale in (remove specific shards)
aws elasticache modify-replication-group-shard-configuration \
  --replication-group-id my-redis-cluster \
  --node-group-count 2 \
  --node-groups-to-remove "0003" "0004" --apply-immediately

# Check resharding status (async operation)
aws elasticache describe-replication-groups \
  --replication-group-id my-redis-cluster \
  --query 'ReplicationGroups[0].Status'
# "modifying" = in progress; "available" = complete
```
