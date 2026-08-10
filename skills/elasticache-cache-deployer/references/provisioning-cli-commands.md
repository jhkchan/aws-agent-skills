# Provisioning CLI Commands — ElastiCache Cache Deployer

Full copy-pasteable CLI command sequence for all 10 provisioning steps.
Variables to substitute: `<cluster>`, `<region>`, `<account-id>`, KMS
key ARNs, subnet IDs, security group IDs, AUTH token, shard count,
replica count.

## Step 0: Prerequisites check

```bash
# Confirm caller identity
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "Account: $ACCOUNT_ID"

# Confirm region
REGION=$(aws configure get region)
echo "Region: $REGION"

# Confirm cluster name is available
aws elasticache describe-replication-groups --replication-group-id <cluster> 2>&1 | head -3

# Confirm CMK exists and is enabled (if encryption at rest with customer CMK)
aws kms describe-key --key-id alias/<alias-name> \
  --query 'KeyMetadata.[KeyId,KeyState,Enabled]' --output text

# Confirm subnet group spans >=2 AZs (required for Multi-AZ Redis)
aws ec2 describe-subnets --subnet-ids subnet-0aaa subnet-0bbb subnet-0ccc \
  --query 'Subnets[*].AvailabilityZone' --output text
# Expect at least 2 distinct AZ values
```

## Step 1: Create the subnet group (must span >=2 AZs for Multi-AZ)

```bash
aws elasticache create-cache-subnet-group \
  --cache-subnet-group-name <subnet-group> \
  --cache-subnet-group-description "Subnet group for prod cache" \
  --subnet-ids subnet-0aaa subnet-0bbb subnet-0ccc \
  --tags Key=Environment,Value=production
```

## Step 2: Create the parameter group

```bash
# Redis 6.x family (use redis7.x for Redis 7.x)
aws elasticache create-cache-parameter-group \
  --cache-parameter-group-name <pg-name> \
  --cache-parameter-group-family redis6.x \
  --description "Production Redis parameter group"

# Set maxmemory-policy, timeout, tcp-keepalive
aws elasticache modify-cache-parameter-group \
  --cache-parameter-group-name <pg-name> \
  --parameter-name-values \
    ParameterName=maxmemory-policy,ParameterValue=allkeys-lru \
    ParameterName=timeout,ParameterValue=300 \
    ParameterName=tcp-keepalive,ParameterValue=60
```

For Memcached:

```bash
aws elasticache create-cache-parameter-group \
  --cache-parameter-group-name <pg-name> \
  --cache-parameter-group-family memcached1.6 \
  --description "Production Memcached parameter group"

aws elasticache modify-cache-parameter-group \
  --cache-parameter-group-name <pg-name> \
  --parameter-name-values \
    ParameterName=max-item-size,ParameterValue=4194304
```

## Step 3: Generate and store AUTH token (Redis with TLS only)

```bash
AUTH_TOKEN=$(openssl rand -base64 24)
echo "AUTH token length: ${#AUTH_TOKEN}"   # must be 16-128 chars

aws secretsmanager create-secret \
  --name <cluster>-auth-token \
  --secret-string "$AUTH_TOKEN"
```

## Step 4: Create the replication group (Redis cluster mode ENABLED)

The canonical production Redis topology: cluster mode enabled, Multi-AZ,
TLS + AUTH, customer CMK, snapshots.

```bash
aws elasticache create-replication-group \
  --replication-group-id <cluster> \
  --replication-group-description "Production Redis cluster" \
  --engine redis \
  --engine-version 6.x \
  --cache-node-type cache.r6g.2xlarge \
  --cache-parameter-group-name <pg-name> \
  --cache-subnet-group-name <subnet-group> \
  --security-group-ids sg-cache123 \
  --num-node-groups 3 \
  --replicas-per-node-group 1 \
  --automatic-failover-enabled \
  --multi-az-enabled \
  --transit-encryption-enabled \
  --at-rest-encryption-enabled \
  --kms-key-id arn:aws:kms:<region>:<account-id>:alias/<alias-name> \
  --auth-token "$AUTH_TOKEN" \
  --snapshot-retention-limit 7 \
  --snapshot-window "03:00-05:00" \
  --maintenance-window "sun:05:00-sun:07:00" \
  --notification-topic-arn arn:aws:sns:<region>:<account-id>:cache-alerts \
  --tags Key=Environment,Value=production Key=Workload,Value=cache
```

Wait for available:

```bash
aws elasticache wait replication-group-available --replication-group-id <cluster>
```

## Step 4 alt A: Redis cluster mode DISABLED (single primary + replicas)

For workloads that fit on a single primary (writes < 50k/sec).

```bash
aws elasticache create-replication-group \
  --replication-group-id <cluster> \
  --replication-group-description "Redis replication group (cluster mode disabled)" \
  --engine redis \
  --cache-node-type cache.r6g.large \
  --cache-parameter-group-name <pg-name> \
  --cache-subnet-group-name <subnet-group> \
  --security-group-ids sg-cache123 \
  --num-cache-clusters 2 \
  --automatic-failover-enabled \
  --multi-az-enabled \
  --transit-encryption-enabled \
  --at-rest-encryption-enabled \
  --auth-token "$AUTH_TOKEN" \
  --snapshot-retention-limit 7 \
  --snapshot-window "03:00-05:00"
```

Note: cluster mode DISABLED uses `--num-cache-clusters` (NOT
`--num-node-groups` / `--replicas-per-node-group`).

## Step 4 alt B: Memcached cluster

```bash
aws elasticache create-cache-cluster \
  --cache-cluster-id <cluster> \
  --engine memcached \
  --engine-version 1.6.22 \
  --cache-node-type cache.r6g.2xlarge \
  --num-cache-nodes 3 \
  --cache-parameter-group-name <pg-name> \
  --cache-subnet-group-name <subnet-group> \
  --security-group-ids sg-cache123 \
  --az-mode cross-az \
  --preferred-maintenance-window "sun:05:00-sun:07:00" \
  --tags Key=Environment,Value=production

# Note: Memcached does NOT support:
#   --automatic-failover-enabled, --multi-az-enabled
#   --transit-encryption-enabled, --at-rest-encryption-enabled
#   --auth-token, --snapshot-retention-limit
#   --num-node-groups, --replicas-per-node-group
```

Wait for available:

```bash
aws elasticache wait cache-cluster-available --cache-cluster-id <cluster>
```

## Step 5: ElastiCache Serverless (2023-2024)

```bash
aws elasticache create-serverless-cache \
  --serverless-cache-name <cluster> \
  --engine redis \
  --description "Serverless Redis cache" \
  --security-group-ids sg-cache123 \
  --subnet-ids subnet-0aaa subnet-0bbb subnet-0ccc \
  --user-group-id default \
  --data-storage Maximum=5000 \
  --daily-storage-retention-period 7 \
  --tags Key=Environment,Value=production

# Note: Serverless has separate API endpoints:
#   create-serverless-cache, describe-serverless-caches, etc.
# It does NOT use replication-group or cache-cluster APIs.
```

## Step 6: Global Datastore (cross-region replication)

Prerequisites: primary cluster must be cluster-mode-enabled in
region 1. Secondary clusters must already exist in each target region.

```bash
# Create the Global Datastore (primary must exist first)
aws elasticache create-global-replication-group \
  --global-replication-group-id-suffix <global-name> \
  --global-replication-group-description "Global Redis cache" \
  --primary-replication-group-id <cluster>-<primary-region>

# The Global Replication Group ID will be of the form:
#   <global-id>:<primary-region>
# e.g., fgid:prod-global-cache:us-east-1

# Create a secondary cluster in region 2 (must be cluster-mode-enabled)
aws elasticache create-replication-group \
  --replication-group-id <cluster>-eu-west-1 \
  --replication-group-description "Secondary region cluster" \
  --engine redis \
  --cache-node-type cache.r6g.2xlarge \
  --num-node-groups 3 --replicas-per-node-group 1 \
  --automatic-failover-enabled \
  --multi-az-enabled \
  --transit-encryption-enabled \
  --at-rest-encryption-enabled \
  --kms-key-id arn:aws:kms:eu-west-1:<account-id>:alias/<alias-name> \
  --cache-subnet-group-name <subnet-group>-eu-west-1 \
  --security-group-ids sg-cache-eu-west-1

# Add the secondary cluster to the Global Datastore
aws elasticache create-global-replication-group-member \
  --global-replication-group-id <global-id>:<global-name>:<primary-region> \
  --replication-group-id <cluster>-eu-west-1 \
  --replication-group-region eu-west-1

# Promote secondary to primary (for DR failover)
aws elasticache failover-global-replication-group \
  --global-replication-group-id <global-id>:<global-name>:<primary-region> \
  --primary-region eu-west-1 \
  --primary-replication-group-id <cluster>-eu-west-1
```

## Step 7: Manual snapshot (pre-upgrade checkpoint)

```bash
aws elasticache create-snapshot \
  --cache-cluster-id <cluster>-0001 \
  --snapshot-name <cluster>-$(date +%Y-%m-%d)-preupgrade \
  --replication-group-id <cluster>

# Restore from snapshot (creates NEW cluster)
aws elasticache create-replication-group \
  --replication-group-id <cluster>-restored \
  --replication-group-description "Restored from snapshot" \
  --engine redis \
  --cache-node-type cache.r6g.2xlarge \
  --num-node-groups 3 --replicas-per-node-group 1 \
  --snapshot-arns arn:aws:elasticache:<region>:<account-id>:snapshot:<snapshot-name> \
  --transit-encryption-enabled \
  --at-rest-encryption-enabled \
  --kms-key-id arn:aws:kms:<region>:<account-id>:alias/<alias-name>
```

## Step 8: Modify an existing replication group (mutable settings)

```bash
# Change parameter group (applies on next reboot)
aws elasticache modify-replication-group \
  --replication-group-id <cluster> \
  --cache-parameter-group-name <new-pg> \
  --apply-immediately

# Scale up node type (rolling replacement)
aws elasticache modify-replication-group \
  --replication-group-id <cluster> \
  --cache-node-type cache.r6g.4xlarge \
  --apply-immediately

# Scale out shards (cluster mode enabled only)
aws elasticache modify-replication-group-shard-configuration \
  --replication-group-id <cluster> \
  --node-group-count 5 \
  --apply-immediately

# Enable TLS post-creation (rolling replacement, ~60s/node disconnect)
aws elasticache modify-replication-group \
  --replication-group-id <cluster> \
  --transit-encryption-enabled true \
  --apply-immediately
```

Note: the following CANNOT be modified post-creation:
- Engine (Redis ↔ Memcached)
- Cluster mode (disabled ↔ enabled)
- At-rest encryption (off → on requires new cluster + dump/restore)

## Step 9: CloudWatch alarms

```bash
# CPU > 90% for 5 min
aws cloudwatch put-metric-alarm \
  --alarm-name "<cluster>-cpu-high" \
  --namespace AWS/ElastiCache \
  --metric-name CPUUtilization \
  --dimensions Name=CacheClusterId,Value=<cluster>-0001 \
  --statistic Average --period 60 --threshold 90 \
  --comparison-operator GreaterThan --evaluation-periods 5 \
  --alarm-actions <sns-arn>

# Swap usage > 0 (Redis should NEVER swap)
aws cloudwatch put-metric-alarm \
  --alarm-name "<cluster>-swap" \
  --namespace AWS/ElastiCache \
  --metric-name SwapUsage \
  --dimensions Name=CacheClusterId,Value=<cluster>-0001 \
  --statistic Average --period 60 --threshold 0 \
  --comparison-operator GreaterThan --evaluation-periods 1 \
  --alarm-actions <sns-arn>

# Evictions > 1000 in 5 min (capacity issue)
aws cloudwatch put-metric-alarm \
  --alarm-name "<cluster>-evictions" \
  --namespace AWS/ElastiCache \
  --metric-name Evictions \
  --dimensions Name=CacheClusterId,Value=<cluster>-0001 \
  --statistic Sum --period 60 --threshold 1000 \
  --comparison-operator GreaterThan --evaluation-periods 5 \
  --alarm-actions <sns-arn>

# Replication lag > 30s (Redis replication groups)
aws cloudwatch put-metric-alarm \
  --alarm-name "<cluster>-repl-lag" \
  --namespace AWS/ElastiCache \
  --metric-name ReplicationLag \
  --dimensions Name=CacheClusterId,Value=<cluster>-0001 \
  --statistic Average --period 60 --threshold 30 \
  --comparison-operator GreaterThan --evaluation-periods 3 \
  --alarm-actions <sns-arn>

# DatabaseMemoryUsagePercentage > 90% (memory pressure)
aws cloudwatch put-metric-alarm \
  --alarm-name "<cluster>-memory-high" \
  --namespace AWS/ElastiCache \
  --metric-name DatabaseMemoryUsagePercentage \
  --dimensions Name=CacheClusterId,Value=<cluster>-0001 \
  --statistic Average --period 60 --threshold 90 \
  --comparison-operator GreaterThan --evaluation-periods 3 \
  --alarm-actions <sns-arn>
```

## Verification

```bash
# Replication group config
aws elasticache describe-replication-groups --replication-group-id <cluster>

# Per-shard cluster info (cluster mode enabled)
aws elasticache describe-cache-clusters \
  --cache-cluster-id <cluster>-0001 --show-cache-node-info

# Parameter group
aws elasticache describe-cache-parameter-groups --cache-parameter-group-name <pg>

# Subnet group
aws elasticache describe-cache-subnet-groups --cache-subnet-group-name <subnet-group>

# KMS key
aws kms describe-key --key-id alias/<alias-name>

# Snapshots
aws elasticache describe-snapshots --replication-group-id <cluster>

# Global Datastore
aws elasticache describe-global-replication-groups \
  --global-replication-group-id <global-id>:<global-name>:<primary-region> \
  --show-member-info
```

## Terraform equivalent (aws_elasticache_replication_group)

```hcl
resource "aws_elasticache_replication_group" "cache" {
  replication_group_id          = "<cluster>"
  replication_group_description = "Production Redis cluster"
  engine                        = "redis"
  engine_version                = "6.x"
  node_type                     = "cache.r6g.2xlarge"
  parameter_group_name          = aws_elasticache_parameter_group.cache.name
  subnet_group_name             = aws_elasticache_subnet_group.cache.name
  security_group_ids            = [aws_security_group.cache.id]

  # Cluster mode
  num_node_groups           = 3
  replicas_per_node_group   = 1
  automatic_failover_enabled = true
  multi_az_enabled          = true

  # Security
  transit_encryption_enabled = true
  at_rest_encryption_enabled = true
  kms_key_id                = aws_kms_key.cache.arn
  auth_token                = data.aws_secretsmanager_secret_version.auth.secret_string

  # Snapshots
  snapshot_retention_limit = 7
  snapshot_window          = "03:00-05:00"
  maintenance_window       = "sun:05:00-sun:07:00"

  tags = {
    Environment = "production"
    Workload    = "cache"
  }
}

resource "aws_elasticache_subnet_group" "cache" {
  name        = "<subnet-group>"
  description = "Multi-AZ subnet group"
  subnet_ids  = [aws_subnet.cache_a.id, aws_subnet.cache_b.id, aws_subnet.cache_c.id]
}

resource "aws_elasticache_parameter_group" "cache" {
  name        = "<pg>"
  family      = "redis6.x"
  description = "Production Redis parameter group"

  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"
  }
  parameter {
    name  = "timeout"
    value = "300"
  }
  parameter {
    name  = "tcp-keepalive"
    value = "60"
  }
}

resource "aws_kms_key" "cache" {
  description             = "Customer CMK for ElastiCache <cluster>"
  deletion_window_in_days = 30
  enable_key_rotation     = true
}

resource "aws_kms_alias" "cache" {
  name          = "alias/<alias-name>"
  target_key_id = aws_kms_key.cache.key_id
}
```

## AWS CLI quick reference

| Operation | Command |
|---|---|
| Create subnet group | `aws elasticache create-cache-subnet-group` |
| Create parameter group | `aws elasticache create-cache-parameter-group` |
| Modify parameter group | `aws elasticache modify-cache-parameter-group` |
| Create Redis replication group | `aws elasticache create-replication-group` |
| Create Memcached cluster | `aws elasticache create-cache-cluster` |
| Create Serverless cache | `aws elasticache create-serverless-cache` |
| Modify replication group | `aws elasticache modify-replication-group` |
| Scale shards | `aws elasticache modify-replication-group-shard-configuration` |
| Create snapshot | `aws elasticache create-snapshot` |
| Create Global Datastore | `aws elasticache create-global-replication-group` |
| Add Global member | `aws elasticache create-global-replication-group-member` |
| Failover Global | `aws elasticache failover-global-replication-group` |
| Describe replication group | `aws elasticache describe-replication-groups` |
| Describe cache cluster | `aws elasticache describe-cache-clusters` |
| Wait for available | `aws elasticache wait replication-group-available` |
| Delete replication group | `aws elasticache delete-replication-group` |
| Delete cache cluster | `aws elasticache delete-cache-cluster` |
