# Provisioning CLI Commands

See SKILL.md for full command reference.

## Key Creation Commands

Refer to SKILL.md Quick Navigation and Configuration Dependency Graph.

## Step 2 — Cluster creation (primary + read replicas) (moved from SKILL.md)

```bash
# Create the cluster (with parameter group, encryption, IAM auth)
aws neptune create-db-cluster \
  --db-cluster-identifier my-neptune-cluster \
  --engine neptune \
  --engine-version 1.3.2.1 \
  --master-username neptuneadmin \
  --master-user-password "SecureP@ssw0rd!2026" \
  --db-subnet-group-name my-neptune-subnet-group \
  --vpc-security-group-ids sg-aaa11122 \
  --db-cluster-parameter-group-name my-neptune-params \
  --storage-encrypted \
  --kms-key-id arn:aws:kms:us-east-1:123456789012:key/aaa11122 \
  --enable-iam-database-authentication \
  --backup-retention-period 7 \
  --preferred-backup-window "03:00-04:00" \
  --preferred-maintenance-window "mon:05:00-mon:06:00"

# Create the primary instance
aws neptune create-db-instance \
  --db-instance-identifier my-neptune-primary \
  --db-instance-type db.r5.4xlarge \
  --engine neptune \
  --db-cluster-identifier my-neptune-cluster

# Create a read replica in a different AZ
aws neptune create-db-instance \
  --db-instance-identifier my-neptune-replica-1 \
  --db-instance-type db.r5.4xlarge \
  --engine neptune \
  --db-cluster-identifier my-neptune-cluster \
  --availability-zone us-east-1b
```

## Step 3 — Instance options enumeration (moved from SKILL.md)

```bash
# List available instance options for Neptune
aws neptune describe-orderable-db-instance-options \
  --engine neptune \
  --query 'OrderableDBInstanceOptions[*].DBInstanceClass' --output text | sort -u
```

## Step 4 — Subnet group and security group (moved from SKILL.md)

**Create a DB subnet group (requires >= 2 AZs):**

```bash
aws neptune create-db-subnet-group \
  --db-subnet-group-name my-neptune-subnet-group \
  --db-subnet-group-description "Neptune subnet group" \
  --subnet-ids subnet-aaa11122 subnet-bbb22233 subnet-ccc33344
```

**Security group (Neptune port 8182):**

```bash
SG_ID=$(aws ec2 create-security-group \
  --group-name neptune-cluster-sg --description "Neptune SG" \
  --vpc-id vpc-aaa11122 --query 'GroupId' --output text)

aws ec2 authorize-security-group-ingress \
  --group-id "$SG_ID" --protocol tcp --port 8182 \
  --source-security-group-id sg-app11122
```

## Step 5 — Parameter group create/modify (moved from SKILL.md)

```bash
aws neptune create-db-cluster-parameter-group \
  --db-cluster-parameter-group-name my-neptune-params \
  --db-parameter-group-family neptune1.3 \
  --description "Custom Neptune parameters"

aws neptune modify-db-cluster-parameter-group \
  --db-cluster-parameter-group-name my-neptune-params \
  --parameters \
    ParameterName=neptune_enforce_ssl,ParameterValue=1,ApplyMethod=pending-reboot \
    ParameterName=neptune_query_timeout,ParameterValue=120000,ApplyMethod=immediate \
    ParameterName=neptune_streams,ParameterValue=1,ApplyMethod=pending-reboot
```

## Step 6 — IAM database authentication (moved from SKILL.md)

```bash
aws neptune create-db-cluster \
  --db-cluster-identifier my-neptune-iam \
  --engine neptune \
  --enable-iam-database-authentication \
  --db-subnet-group-name my-neptune-subnet-group \
  --vpc-security-group-ids sg-aaa11122 \
  --db-cluster-parameter-group-name my-neptune-params
```

**IAM policy for Neptune access:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["neptune-db:connect"],
      "Resource": "arn:aws:neptune:us-east-1:123456789012:cluster/my-neptune-iam/*"
    }
  ]
}
```

## Step 7 — Encrypted cluster creation (moved from SKILL.md)

```bash
aws neptune create-db-cluster \
  --db-cluster-identifier my-neptune-encrypted \
  --engine neptune \
  --storage-encrypted \
  --kms-key-id arn:aws:kms:us-east-1:123456789012:key/aaa11122 \
  --db-subnet-group-name my-neptune-subnet-group \
  --vpc-security-group-ids sg-aaa11122
```

## Step 8 — Neptune Streams enable, consumer, filter patterns (moved from SKILL.md)

```bash
# Enable Streams (static parameter — requires reboot)
aws neptune modify-db-cluster-parameter-group \
  --db-cluster-parameter-group-name my-neptune-params \
  --parameters ParameterName=neptune_streams,ParameterValue=1,ApplyMethod=pending-reboot

# Reboot the primary instance to apply
aws neptune reboot-db-instance \
  --db-instance-identifier my-neptune-primary
```

**Stream consumer pattern (polling the stream):**

```bash
# Query the stream for recent changes
curl -s "https://my-neptune-cluster.cluster-aaa11122.us-east-1.neptune.amazonaws.com:8182/streams" \
  -H "Content-Type: application/json" \
  -d '{
    "lastEventId": {"commitNum": 1, "opNum": 1},
    "limit": 100
  }'
```

**Stream filter patterns:**

```json
{"op": "ADD"}              // only insertions
{"op": "REMOVE"}           // only deletions
{"op": ["ADD","UPDATE"]}   // insertions and updates
{}                          // all changes (no filter)
```

## Step 9 — Neptune ML training job (moved from SKILL.md)

```bash
# Export graph data for ML training
aws neptune start-ml-model-training-job \
  --job-id my-neptune-ml-job \
  --s3-url s3://my-neptune-ml-bucket/training/ \
  --role-arn arn:aws:iam::123456789012:role/NeptuneMLRole \
  --model-type NODE_CLASSIFICATION \
  --db-instance-identifier my-neptune-primary
```

## Step 10 — Global Database (moved from SKILL.md)

```bash
# Create the global cluster
aws neptune create-global-cluster \
  --global-cluster-identifier my-neptune-global \
  --source-db-cluster-identifier arn:aws:neptune:us-east-1:123456789012:cluster:my-neptune-cluster

# Add a secondary cluster in another region
aws neptune create-db-cluster \
  --db-cluster-identifier my-neptune-secondary \
  --global-cluster-identifier my-neptune-global \
  --engine neptune \
  --db-subnet-group-name my-neptune-subnet-euwest \
  --vpc-security-group-ids sg-euwest111 \
  --region eu-west-1

# Create a read replica in the secondary region
aws neptune create-db-instance \
  --db-instance-identifier my-neptune-secondary-replica \
  --db-instance-type db.r5.4xlarge \
  --engine neptune \
  --db-cluster-identifier my-neptune-secondary \
  --region eu-west-1
```

## Step 11 — Auto-scaling read replicas (moved from SKILL.md)

```bash
# Register scalable target
aws application-autoscaling register-scalable-target \
  --service-namespace neptune \
  --resource-id cluster:my-neptune-cluster \
  --scalable-dimension neptune:cluster:ReadReplicaCount \
  --min-capacity 1 --max-capacity 15

# Target tracking policy
aws application-autoscaling put-scaling-policy \
  --service-namespace neptune \
  --resource-id cluster:my-neptune-cluster \
  --scalable-dimension neptune:cluster:ReadReplicaCount \
  --policy-name my-scaling-policy --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{"PredefinedMetricSpecification":{"PredefinedMetricType":"NeptuneReadReplicaLag"},"TargetValue":60.0,"ScaleOutCooldown":300,"ScaleInCooldown":300}'
```

## Step 12 — Bulk loader (moved from SKILL.md)

```bash
# Load data from S3 (Gremlin CSV format)
curl -s -X POST \
  "https://my-neptune-cluster.cluster-aaa11122.us-east-1.neptune.amazonaws.com:8182/loader" \
  -H "Content-Type: application/json" \
  -d '{
    "source": "s3://my-neptune-data-bucket/nodes/",
    "format": "csv",
    "iamRoleArn": "arn:aws:iam::123456789012:role/NeptuneBulkLoadRole",
    "mode": "NEW",
    "region": "us-east-1",
    "failOnError": true,
    "parallelism": "HIGH"
  }'
```

**Best practice:** use mode `NEW` for initial loads (fails if data
exists), mode `RESUME` for retrying partial loads. Set `parallelism`
to `HIGH` for large datasets.

## Step 14 — Snapshot create/restore (moved from SKILL.md)

```bash
# Create manual snapshot
aws neptune create-db-cluster-snapshot \
  --db-cluster-snapshot-identifier my-neptune-snapshot-20260805 \
  --db-cluster-identifier my-neptune-cluster

# Restore from snapshot
aws neptune restore-db-cluster-from-snapshot \
  --db-cluster-identifier my-neptune-restored \
  --snapshot-identifier my-neptune-snapshot-20260805 \
  --engine neptune \
  --db-subnet-group-name my-neptune-subnet-group \
  --vpc-security-group-ids sg-aaa11122
```
