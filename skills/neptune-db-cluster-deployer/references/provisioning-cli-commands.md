# Provisioning CLI Commands — Neptune DB Cluster Deployer

Full copy-pasteable CLI command sequence for provisioning an Amazon
Neptune DB cluster with Multi-AZ, TLS, IAM auth, customer CMK,
snapshots, and Streams. Variables to substitute: `<cluster>`,
`<region>`, `<account-id>`, KMS key ARNs, subnet IDs, security group
IDs, instance class, engine version.

## Step 0: Prerequisites check

```bash
# Confirm caller identity
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "Account: $ACCOUNT_ID"

# Confirm region
REGION=$(aws configure get region)
echo "Region: $REGION"

# Confirm cluster name is available
aws neptune describe-db-clusters --db-cluster-identifier <cluster> 2>&1 | head -3

# Confirm CMK exists and is enabled (if encryption with customer CMK)
aws kms describe-key --key-id alias/<alias-name> \
  --query 'KeyMetadata.[KeyId,KeyState,Enabled]' --output text

# Confirm subnet group spans >=2 AZs (required for Multi-AZ Neptune)
aws ec2 describe-subnets --subnet-ids subnet-0aaa subnet-0bbb subnet-0ccc \
  --query 'Subnets[*].AvailabilityZone' --output text
# Expect at least 2 distinct AZ values
```

## Step 1: Create the subnet group (must span >=2 AZs for Multi-AZ)

```bash
aws neptune create-db-subnet-group \
  --db-subnet-group-name <subnet-group> \
  --db-subnet-group-description "Multi-AZ subnet group for prod Neptune" \
  --subnet-ids subnet-0aaa subnet-0bbb subnet-0ccc \
  --tags Key=Environment,Value=production
```

## Step 2: Create the cluster parameter group

```bash
aws neptune create-db-cluster-parameter-group \
  --db-cluster-parameter-group-name <pg-name> \
  --db-parameter-group-family neptune1 \
  --description "Production Neptune cluster parameter group"

# Set neptune_enforce_ssl, neptune_query_timeout, neptune_streams
aws neptune modify-db-cluster-parameter-group \
  --db-cluster-parameter-group-name <pg-name> \
  --parameters \
    ParameterName=neptune_enforce_ssl,ParameterValue=1,ApplyMethod=immediate \
    ParameterName=neptune_query_timeout,ParameterValue=30000,ApplyMethod=immediate \
    ParameterName=neptune_streams,ParameterValue=1,ApplyMethod=pending-reboot
```

## Step 3: Create the DB cluster (writer + storage + config)

Encryption at rest is immutable — set `--storage-encrypted` and
`--kms-key-id` here, NOT later.

```bash
aws neptune create-db-cluster \
  --db-cluster-identifier <cluster> \
  --engine neptune \
  --engine-version 1.3.2.0 \
  --db-cluster-parameter-group-name <pg-name> \
  --db-subnet-group-name <subnet-group> \
  --vpc-security-group-ids sg-neptune123 \
  --storage-encrypted \
  --kms-key-id arn:aws:kms:<region>:<account-id>:alias/<alias-name> \
  --enable-iam-database-authentication \
  --backup-retention-period 7 \
  --deletion-protection \
  --tags Key=Environment,Value=production Key=Workload,Value=graph
```

## Step 4: Create the writer instance

```bash
aws neptune create-db-instance \
  --db-instance-identifier <cluster>-instance-1 \
  --db-instance-class db.r6g.8xlarge \
  --engine neptune \
  --db-cluster-identifier <cluster> \
  --availability-zone <region>a
```

## Step 5: Create reader instances (across different AZs for Multi-AZ)

```bash
# Reader 1
aws neptune create-db-instance \
  --db-instance-identifier <cluster>-instance-2 \
  --db-instance-class db.r6g.8xlarge \
  --engine neptune \
  --db-cluster-identifier <cluster> \
  --availability-zone <region>b

# Reader 2
aws neptune create-db-instance \
  --db-instance-identifier <cluster>-instance-3 \
  --db-instance-class db.r6g.8xlarge \
  --engine neptune \
  --db-cluster-identifier <cluster> \
  --availability-zone <region>c
```

Wait for instances to become available:

```bash
aws neptune wait db-instance-available --db-instance-identifier <cluster>-instance-1
```

## Step 6: Bulk load initial data from S3 (same region as the cluster)

Prerequisites: S3 bucket in the same region; IAM role with
`s3:GetObject` on the bucket and trust policy allowing `rds.amazonaws.com`.

```bash
# IAM role for the Neptune Loader
cat > /tmp/trust-policy.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "rds.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
EOF

aws iam create-role \
  --role-name NeptuneLoadRole \
  --assume-role-policy-document file:///tmp/trust-policy.json

aws iam attach-role-policy \
  --role-name NeptuneLoadRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess

# Trigger the load via the loader HTTP endpoint
curl -X POST \
  -H 'Content-Type: application/json' \
  https://<cluster>.cluster-xxxxxxxxxxxx.<region>.neptune.amazonaws.com:8182/loader \
  -d '{
    "source": "s3://prod-graph-bucket/initial-load/",
    "format": "csv",
    "iamRoleArn": "arn:aws:iam::<account-id>:role/NeptuneLoadRole",
    "mode": "NEW",
    "region": "<region>",
    "failOnError": "TRUE",
    "parallelism": "MEDIUM"
  }'

# Poll the load status
LOAD_ID="<load-id-from-response>"
curl -X GET \
  "https://<cluster>.cluster-xxxxxxxxxxxx.<region>.neptune.amazonaws.com:8182/loader/<LOAD_ID>?details=true"
```

Load modes:
- `NEW` — error on duplicate vertices/edges (initial load)
- `AUTO` — overwrite duplicates (idempotent reload)
- `RESUME` — continue an interrupted load

## Step 7: Manual snapshot (pre-upgrade checkpoint)

```bash
aws neptune create-db-cluster-snapshot \
  --db-cluster-identifier <cluster> \
  --db-cluster-snapshot-name <cluster>-$(date +%Y-%m-%d)-preupgrade

# Restore from snapshot (creates a NEW cluster)
aws neptune restore-db-cluster-from-snapshot \
  --db-cluster-identifier <cluster>-restored \
  --snapshot-identifier <cluster>-2026-08-05-preupgrade \
  --engine neptune
```

## Step 8: Modify an existing cluster (mutable settings)

```bash
# Change instance class (rolling reboot per instance)
aws neptune modify-db-instance \
  --db-instance-identifier <cluster>-instance-1 \
  --db-instance-class db.r6g.12xlarge \
  --apply-immediately

# Change parameter group (applies on next reboot)
aws neptune modify-db-cluster \
  --db-cluster-identifier <cluster> \
  --db-cluster-parameter-group-name <new-pg> \
  --apply-immediately

# Scale read capacity by adding a reader
aws neptune create-db-instance \
  --db-instance-identifier <cluster>-instance-4 \
  --db-instance-class db.r6g.8xlarge \
  --engine neptune \
  --db-cluster-identifier <cluster> \
  --availability-zone <region>a
```

Note: the following CANNOT be modified post-creation:
- Engine (Neptune is single-engine; cannot become Analytics)
- Storage encryption (off → on requires snapshot/restore)
- VPC / DB subnet group placement (requires new cluster)

## Step 9: Query language endpoints

Neptune supports three query languages on the same cluster:

```bash
# Gremlin (property graph; Apache TinkerPop-compatible)
# Endpoint: https://<cluster>:8182/gremlin
# Example: add a vertex
curl -X POST -H 'Content-Type: application/json' \
  -d '{"gremlin": "g.addV(\"person\").property(\"name\",\"alice\")"}' \
  https://<cluster>:8182/gremlin

# SPARQL (RDF / semantic web; triple-store)
# Endpoint: https://<cluster>:8182/sparql
curl -X POST -H 'Content-Type: application/sparql-query' \
  -d 'SELECT * WHERE { ?s ?p ?o } LIMIT 10' \
  https://<cluster>:8182/sparql

# openCypher (property graph; Neo4j-compatible)
# Endpoint: https://<cluster>:8182/opencypher
curl -X POST \
  -d 'query=MATCH (n) RETURN n LIMIT 10' \
  https://<cluster>:8182/opencypher
```

## Step 10: Neptune Streams (change data capture)

Enable in the parameter group via `neptune_streams=1` + reboot, then
poll the stream endpoint:

```bash
# Poll the stream for change records
curl -X GET \
  "https://<cluster>:8182/streams?limit=100"

# Response includes commitNum and change records:
#   { "records": [ { "commitNum":..., "op":"add|remove", "data":{...} } ] }

# Typical consumer pattern: Kinesis Data Streams + Lambda poller that
# replicates changes to downstream stores (Elasticsearch, S3, etc.)
```

Stream records are retained for ~24 hours.

## Verification

```bash
# Cluster config — Status, MultiAZ, StorageEncrypted, KmsKeyId,
# BackupRetentionPeriod, DeletionProtection, IamDatabaseAuthEnabled
aws neptune describe-db-clusters --db-cluster-identifier <cluster>

# Instance info — DBInstanceClass, DBInstanceStatus, AvailabilityZone
aws neptune describe-db-instances --db-instance-identifier <cluster>-instance-1

# Parameter group — neptune_enforce_ssl, neptune_query_timeout, neptune_streams
aws neptune describe-db-cluster-parameters --db-cluster-parameter-group-name <pg>

# Subnet group
aws neptune describe-db-subnet-groups --db-subnet-group-name <subnet-group>

# KMS key — KeyState: Enabled, Enabled: true
aws kms describe-key --key-id alias/<alias-name>

# Snapshots
aws neptune describe-db-cluster-snapshots --db-cluster-identifier <cluster>
```

## Terraform equivalent (aws_neptune_cluster + aws_neptune_cluster_instance)

```hcl
resource "aws_neptune_cluster" "graph" {
  cluster_identifier                  = "<cluster>"
  engine                              = "neptune"
  engine_version                      = "1.3.2.0"
  db_cluster_parameter_group_name     = aws_neptune_cluster_parameter_group.graph.name
  db_subnet_group_name                = aws_neptune_subnet_group.graph.name
  vpc_security_group_ids              = [aws_security_group.graph.id]
  storage_encrypted                   = true
  kms_key_id                          = aws_kms_key.graph.arn
  iam_database_authentication_enabled = true
  backup_retention_period             = 7
  deletion_protection                 = true

  tags = {
    Environment = "production"
    Workload    = "graph"
  }
}

resource "aws_neptune_cluster_instance" "writer" {
  identifier           = "<cluster>-instance-1"
  cluster_identifier   = aws_neptune_cluster.graph.id
  instance_class       = "db.r6g.8xlarge"
  engine               = "neptune"
  availability_zone    = "${data.aws_region.current.name}a"
}

resource "aws_neptune_cluster_instance" "readers" {
  count              = 2
  identifier         = "<cluster>-instance-${count.index + 2}"
  cluster_identifier = aws_neptune_cluster.graph.id
  instance_class     = "db.r6g.8xlarge"
  engine             = "neptune"
  availability_zone  = "${data.aws_region.current.name}${count.index == 0 ? "b" : "c"}"
}

resource "aws_neptune_subnet_group" "graph" {
  name        = "<subnet-group>"
  description = "Multi-AZ subnet group for prod Neptune"
  subnet_ids  = [aws_subnet.graph_a.id, aws_subnet.graph_b.id, aws_subnet.graph_c.id]
}

resource "aws_neptune_cluster_parameter_group" "graph" {
  name        = "<pg>"
  family      = "neptune1"
  description = "Production Neptune cluster parameter group"

  parameter {
    name         = "neptune_enforce_ssl"
    value        = "1"
    apply_method = "immediate"
  }
  parameter {
    name         = "neptune_query_timeout"
    value        = "30000"
    apply_method = "immediate"
  }
  parameter {
    name         = "neptune_streams"
    value        = "1"
    apply_method = "pending-reboot"
  }
}

resource "aws_kms_key" "graph" {
  description             = "Customer CMK for Neptune <cluster>"
  deletion_window_in_days = 30
  enable_key_rotation     = true
}

resource "aws_kms_alias" "graph" {
  name          = "alias/<alias-name>"
  target_key_id = aws_kms_key.graph.key_id
}
```

## AWS CLI quick reference

| Operation | Command |
|---|---|
| Create subnet group | `aws neptune create-db-subnet-group` |
| Create cluster parameter group | `aws neptune create-db-cluster-parameter-group` |
| Modify cluster parameter group | `aws neptune modify-db-cluster-parameter-group` |
| Create DB cluster | `aws neptune create-db-cluster` |
| Create DB instance | `aws neptune create-db-instance` |
| Modify DB instance | `aws neptune modify-db-instance` |
| Modify DB cluster | `aws neptune modify-db-cluster` |
| Create cluster snapshot | `aws neptune create-db-cluster-snapshot` |
| Restore from snapshot | `aws neptune restore-db-cluster-from-snapshot` |
| Describe cluster | `aws neptune describe-db-clusters` |
| Describe instance | `aws neptune describe-db-instances` |
| Describe parameters | `aws neptune describe-db-cluster-parameters` |
| Wait for instance available | `aws neptune wait db-instance-available` |
| Delete instance | `aws neptune delete-db-instance` |
| Delete cluster | `aws neptune delete-db-cluster` |
| Bulk load (HTTP) | `curl -X POST https://<cluster>:8182/loader -d '{...}'` |
| Streams poll (HTTP) | `curl https://<cluster>:8182/streams?limit=N` |

## Step 4 — subnet group and security group CLI (moved from SKILL.md)

**DB subnet group creation:**

```bash
aws neptune create-db-subnet-group \
  --db-subnet-group-name prod-neptune-subnet \
  --db-subnet-group-description "Multi-AZ subnet group for prod Neptune" \
  --subnet-ids subnet-0aaa subnet-0bbb subnet-0ccc \
  --tags Key=Environment,Value=production
```

Verify the subnets span >=2 AZs (3+ preferred):

```bash
aws ec2 describe-subnets --subnet-ids subnet-0aaa subnet-0bbb subnet-0ccc \
  --query 'Subnets[*].AvailabilityZone' --output text
# Expect at least 2 distinct AZs for Multi-AZ
```

**Security group rules:**

```bash
# Inbound: allow the application's SG to reach Neptune on port 8182
aws ec2 authorize-security-group-ingress \
  --group-id sg-neptune123 \
  --protocol tcp \
  --port 8182 \
  --source-security-group-id sg-app456
```

## Step 6 — parameter group creation and apply (moved from SKILL.md)

**Applying a parameter group:**

```bash
aws neptune create-db-cluster-parameter-group \
  --db-cluster-parameter-group-name prod-neptune-pg \
  --db-parameter-group-family neptune1 \
  --description "Production Neptune cluster parameter group"

aws neptune modify-db-cluster-parameter-group \
  --db-cluster-parameter-group-name prod-neptune-pg \
  --parameters \
    ParameterName=neptune_enforce_ssl,ParameterValue=1,ApplyMethod=immediate \
    ParameterName=neptune_query_timeout,ParameterValue=30000,ApplyMethod=immediate
```

Attach the parameter group at `create-db-cluster` via
`--db-cluster-parameter-group-name`.

## Step 7 — IAM database auth (moved from SKILL.md)

**Enable at creation:**

```bash
aws neptune create-db-cluster ... \
  --enable-iam-database-authentication
```

**IAM policy for Neptune access:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["neptune-db:Connect"],
      "Resource": "arn:aws:neptune:<region>:<account>:cluster/<cluster-name>"
    }
  ]
}
```

## Step 8 — Neptune Loader bulk load (moved from SKILL.md)

**Load:**

```bash
curl -X POST \
  -H 'Content-Type: application/json' \
  https://<cluster-endpoint>:8182/loader \
  -d '{
    "source": "s3://prod-graph-bucket/initial-load/",
    "format": "csv",
    "iamRoleArn": "arn:aws:iam::<account>:role/NeptuneLoadRole",
    "mode": "NEW",
    "region": "us-east-1",
    "failOnError": "TRUE",
    "parallelism": "MEDIUM"
  }'
```
