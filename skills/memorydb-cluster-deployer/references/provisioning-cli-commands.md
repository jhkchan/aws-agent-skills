# Provisioning CLI Commands — MemoryDB Cluster Deployer

Full copy-pasteable CLI command sequence for provisioning an Amazon
MemoryDB for Redis cluster with Multi-AZ, TLS (on by default), ACLs,
data tiering, snapshots, and optional Multi-Region. Variables to
substitute: `<cluster>`, `<region>`, `<account-id>`, subnet IDs,
security group IDs, node type, shard count, replica count.

## Step 0: Prerequisites check

```bash
# Confirm caller identity
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "Account: $ACCOUNT_ID"

# Confirm region
REGION=$(aws configure get region)
echo "Region: $REGION"

# Confirm cluster name is available
aws memorydb describe-clusters --cluster-name <cluster> 2>&1 | head -3

# Confirm subnet group spans >=2 AZs (required for Multi-AZ)
aws ec2 describe-subnets --subnet-ids subnet-0aaa subnet-0bbb subnet-0ccc \
  --query 'Subnets[*].AvailabilityZone' --output text
# Expect at least 2 distinct AZ values
```

## Step 1: Create the subnet group (must span >=2 AZs for Multi-AZ)

```bash
aws memorydb create-subnet-group \
  --subnet-group-name <subnet-group> \
  --description "Multi-AZ subnet group for prod MemoryDB" \
  --subnet-ids subnet-0aaa subnet-0bbb subnet-0ccc \
  --tags Key=Environment,Value=production
```

## Step 2: Create users and an ACL (REQUIRED — no open mode in production)

```bash
# Read-write user for the application
aws memorydb create-user \
  --user-name app-rw \
  --authentication-mode Type=password,Passwords='["SecurePassword123!"]' \
  --access-string "on ~* +@all"

# Read-only user for analytics
aws memorydb create-user \
  --user-name analytics-ro \
  --authentication-mode Type=password,Passwords='["AnalyticsPassword456!"]' \
  --access-string "on ~* -@all +@read"

# Create an ACL and add the users
aws memorydb create-acl \
  --acl-name <acl-name> \
  --user-names app-rw analytics-ro
```

Access-string reference:
- `on` — enable the user
- `~*` — allow access to all keys (use `~prefix:*` to scope)
- `+@all` — all commands; `-@all +@read` — read-only

## Step 3: Create the cluster (TLS on by default, encryption at rest on by default)

The canonical production MemoryDB topology: cluster mode (always on),
Multi-AZ, TLS, ACL, snapshots.

```bash
aws memorydb create-cluster \
  --cluster-name <cluster> \
  --description "Production MemoryDB cluster" \
  --node-type db.r6g.24xlarge \
  --acl-name <acl-name> \
  --subnet-group-name <subnet-group> \
  --security-group-ids sg-memorydb123 \
  --num-shards 3 \
  --num-replicas-per-shard 1 \
  --auto-failover-enabled \
  --snapshot-retention-limit 7 \
  --snapshot-window "03:00-05:00" \
  --maintenance-window "sun:05:00-sun:07:00" \
  --parameter-group-name default.memorydb-redis7 \
  --tags Key=Environment,Value=production Key=Workload,Value=in-memory-db
```

Wait for available:

```bash
aws memorydb wait cluster-available --cluster-name <cluster>
```

Note: TLS at-rest + in-transit are ON by default. To use a customer
CMK, add `--kms-key-id arn:aws:kms:<region>:<account-id>:alias/<alias>`.

## Step 3 alt: Cluster with data tiering (db.r6gd family)

Data tiering is a one-way door — set at creation only.

```bash
aws memorydb create-cluster \
  --cluster-name <cluster> \
  --node-type db.r6gd.24xlarge \
  --data-tiering \
  --acl-name <acl-name> \
  --subnet-group-name <subnet-group> \
  --security-group-ids sg-memorydb123 \
  --num-shards 3 \
  --num-replicas-per-shard 1 \
  --auto-failover-enabled \
  --snapshot-retention-limit 7 \
  --snapshot-window "03:00-05:00" \
  --tags Key=Environment,Value=production
```

Note: `--data-tiering` requires `db.r6gd.<size>` node type. It
CANNOT be enabled or disabled post-creation.

## Step 4: Manual snapshot (pre-upgrade checkpoint)

```bash
aws memorydb create-snapshot \
  --cluster-name <cluster> \
  --snapshot-name <cluster>-$(date +%Y-%m-%d)-preupgrade

# Restore from snapshot (creates a NEW cluster)
aws memorydb create-cluster \
  --cluster-name <cluster>-restored \
  --snapshot-arn arn:aws:memorydb:<region>:<account-id>:snapshot:<snapshot-name> \
  --acl-name <acl-name> \
  --subnet-group-name <subnet-group>
```

## Step 5: Modify an existing cluster (mutable settings)

```bash
# Scale out shards (online resharding — non-trivial; plan a window)
aws memorydb update-cluster \
  --cluster-name <cluster> \
  --shard-configuration \
    DesiredShards=5 \
  --apply-immediately

# Scale up node type (rolling shard replacement)
aws memorydb update-cluster \
  --cluster-name <cluster> \
  --node-type db.r6g.24xlarge \
  --apply-immediately

# Change parameter group (applies on next reboot)
aws memorydb update-cluster \
  --cluster-name <cluster> \
  --parameter-group-name <new-pg> \
  --apply-immediately

# Change ACL (applies to all connections immediately)
aws memorydb update-cluster \
  --cluster-name <cluster> \
  --acl-name <new-acl> \
  --apply-immediately
```

Note: the following CANNOT be modified post-creation:
- Data tiering (on → off or off → on requires a new cluster)
- VPC / subnet group placement (requires new cluster)
- TLS at-rest (if disabled at creation, cannot be cleanly re-enabled)

## Step 6: Multi-Region (cross-region replication)

Prerequisites: primary cluster exists in region 1; Multi-Region
engine enabled on the cluster.

```bash
# Enable Multi-Region on the primary cluster
aws memorydb update-cluster \
  --cluster-name <cluster> \
  --multi-region-enabled \
  --apply-immediately

# Create a secondary cluster in region 2 (must mirror topology)
aws memorydb create-cluster \
  --cluster-name <cluster>-eu-west-1 \
  --node-type db.r6g.24xlarge \
  --acl-name <acl-name>-eu \
  --subnet-group-name <subnet-group>-eu-west-1 \
  --security-group-ids sg-memorydb-eu \
  --num-shards 3 \
  --num-replicas-per-shard 1 \
  --multi-region-enabled \
  --region eu-west-1

# Promote secondary to primary (for DR failover)
aws memorydb failover-region \
  --cluster-name <cluster> \
  --primary-region eu-west-1
```

## Verification

```bash
# Cluster config — Status, NumberOfShards, ReplicaCount,
# AutomaticFailover, TLSAuthentication, SnapshotRetentionLimit,
# ACLName, DataTiering
aws memorydb describe-clusters --cluster-name <cluster> --show-shard-node-info

# ACL — users, access strings
aws memorydb describe-acls --acl-name <acl-name>

# Subnet group
aws memorydb describe-subnet-groups --subnet-group-name <subnet-group>

# Parameter group
aws memorydb describe-parameters --parameter-group-name default.memorydb-redis7

# Snapshots
aws memorydb describe-snapshots --cluster-name <cluster>

# Multi-Region members
aws memorydb describe-clusters --cluster-name <cluster> --show-multi-region-info
```

## Terraform equivalent (aws_memorydb_cluster)

```hcl
resource "aws_memorydb_cluster" "db" {
  name              = "<cluster>"
  description       = "Production MemoryDB cluster"
  node_type         = "db.r6g.24xlarge"
  acl_name          = aws_memorydb_acl.app.name
  subnet_group_name = aws_memorydb_subnet_group.db.name
  security_group_ids = [aws_security_group.db.id]

  # Cluster mode (always on for MemoryDB)
  num_shards             = 3
  num_replicas_per_shard = 1
  auto_failover_enabled  = true

  # Snapshots
  snapshot_retention_limit = 7
  snapshot_window          = "03:00-05:00"
  maintenance_window       = "sun:05:00-sun:07:00"

  parameter_group_name = "default.memorydb-redis7"

  tags = {
    Environment = "production"
    Workload    = "in-memory-db"
  }
}

# Data tiering variant (one-way door at creation)
resource "aws_memorydb_cluster" "db_tiered" {
  name           = "<cluster>-tiered"
  node_type      = "db.r6gd.24xlarge"
  data_tiering   = true
  acl_name       = aws_memorydb_acl.app.name
  subnet_group_name = aws_memorydb_subnet_group.db.name
  num_shards             = 3
  num_replicas_per_shard = 1
  auto_failover_enabled  = true
}

resource "aws_memorydb_subnet_group" "db" {
  name        = "<subnet-group>"
  description = "Multi-AZ subnet group for prod MemoryDB"
  subnet_ids  = [aws_subnet.db_a.id, aws_subnet.db_b.id, aws_subnet.db_c.id]
}

resource "aws_memorydb_acl" "app" {
  name = "<acl-name>"
  user_names = [aws_memorydb_user.app_rw.name, aws_memorydb_user.analytics_ro.name]
}

resource "aws_memorydb_user" "app_rw" {
  user_name      = "app-rw"
  access_string  = "on ~* +@all"
  authentication_mode {
    type      = "password"
    passwords = [data.aws_secretsmanager_secret_version.app_rw.secret_string]
  }
}

resource "aws_memorydb_user" "analytics_ro" {
  user_name      = "analytics-ro"
  access_string  = "on ~* -@all +@read"
  authentication_mode {
    type      = "password"
    passwords = [data.aws_secretsmanager_secret_version.analytics_ro.secret_string]
  }
}
```

## AWS CLI quick reference

| Operation | Command |
|---|---|
| Create subnet group | `aws memorydb create-subnet-group` |
| Create user | `aws memorydb create-user` |
| Create ACL | `aws memorydb create-acl` |
| Update ACL | `aws memorydb update-acl` |
| Create cluster | `aws memorydb create-cluster` |
| Update cluster | `aws memorydb update-cluster` |
| Create snapshot | `aws memorydb create-snapshot` |
| Describe cluster | `aws memorydb describe-clusters` |
| Describe ACL | `aws memorydb describe-acls` |
| Describe subnet group | `aws memorydb describe-subnet-groups` |
| Describe parameters | `aws memorydb describe-parameters` |
| Wait for cluster available | `aws memorydb wait cluster-available` |
| Delete cluster | `aws memorydb delete-cluster` |
| Failover Multi-Region | `aws memorydb failover-region` |
