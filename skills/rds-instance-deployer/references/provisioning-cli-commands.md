# Provisioning CLI Commands — RDS Instance Deployer

Full copy-pasteable CLI command sequence for all 10 provisioning steps.
Variables to substitute: `<instance>`, `<cluster>`, `<region>`,
`<account-id>`, `<vpc-id>`, `<subnet-ids>`, `<sg-id>`, `<app-sg-id>`,
KMS key ARNs, `<param-group>`, `<option-group>`.

## Step 0: Prerequisites check

```bash
# Confirm caller identity
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "Account: $ACCOUNT_ID"

# Confirm region
REGION=$(aws configure get region)
echo "Region: $REGION"

# Confirm VPC + subnets span at least 2 AZs (Multi-AZ requirement)
aws ec2 describe-subnets --subnet-ids <subnet-aaa> <subnet-bbb> <subnet-ccc> \
  --query 'Subnets[*].[SubnetId,AvailabilityZone]' --output text

# Confirm CMK exists and is enabled
aws kms describe-key --key-id alias/<rds-alias> \
  --query 'KeyMetadata.[KeyId,KeyState,Enabled]' --output text

# Confirm CMK key policy grants RDS
aws kms get-key-policy --key-id alias/<rds-alias> --policy-name default --output text

# Confirm Enhanced Monitoring IAM role exists
aws iam get-role --role-name rds-monitoring-role --query 'Role.Arn' --output text || \
  echo "MISSING rds-monitoring-role — create before provisioning"
```

## Step 1: DB subnet group

```bash
aws rds create-db-subnet-group \
  --db-subnet-group-name <name>-subnet-group \
  --db-subnet-group-description "Subnet group for <name>" \
  --subnet-ids <subnet-aaa> <subnet-bbb> <subnet-ccc>
```

## Step 2: Security group (scope to app SG on engine port)

```bash
# Create DB security group
DB_SG_ID=$(aws ec2 create-security-group \
  --group-name <name>-db-sg \
  --description "DB SG for <name>" \
  --vpc-id <vpc-id> --query 'GroupId' --output text)

# Scope inbound to app SG on engine port
# MySQL/Aurora MySQL: 3306
# PostgreSQL/Aurora PostgreSQL: 5432
# SQL Server: 1433
# Oracle: 1521
aws ec2 authorize-security-group-ingress \
  --group-id "$DB_SG_ID" \
  --protocol tcp \
  --port 5432 \
  --source-security-group-id <app-sg-id>
```

## Step 3: Custom parameter group

```bash
aws rds create-db-parameter-group \
  --db-parameter-group-name <name>-params \
  --db-parameter-group-family postgres14 \
  --description "Custom params for <name>"

aws rds modify-db-parameter-group \
  --db-parameter-group-name <name>-params \
  --parameters \
    "ParameterName=shared_buffers,ParameterValue={DBInstanceClassMemory/4},ApplyMethod=pending-reboot" \
    "ParameterName=rds.force_ssl,ParameterValue=1,ApplyMethod=immediate" \
    "ParameterName=log_statement,ParameterValue=ddl,ApplyMethod=immediate" \
    "ParameterName=max_connections,ParameterValue=200,ApplyMethod=pending-reboot"
```

For Aurora, use a DB cluster parameter group:

```bash
aws rds create-db-cluster-parameter-group \
  --db-cluster-parameter-group-name <name>-cluster-params \
  --db-parameter-group-family aurora-postgresql14 \
  --description "Cluster params for <name>"

aws rds modify-db-cluster-parameter-group \
  --db-cluster-parameter-group-name <name>-cluster-params \
  --parameters \
    "ParameterName=rds.force_ssl,ParameterValue=1,ApplyMethod=immediate"
```

## Step 4: Option group

```bash
aws rds create-option-group \
  --option-group-name <name>-options \
  --engine-name postgres \
  --major-engine-version 14 \
  --option-group-description "Options for <name>"

# Add options (example: pgaudit)
aws rds modify-option-group \
  --option-group-name <name>-options \
  --options "OptionName=pgaudit,OptionSettings=[{Name=pgaudit.log,Value=write,ddl}]" \
  --apply-immediately
```

## Step 5a: Create non-Aurora instance (MySQL/PostgreSQL/SQL Server/Oracle)

```bash
aws rds create-db-instance \
  --db-instance-identifier <instance> \
  --db-instance-class db.m7g.large \
  --engine postgres \
  --engine-version 14.10 \
  --master-username <admin-user> \
  --manage-master-user-password \
  --allocated-storage 100 \
  --storage-type gp3 \
  --storage-encrypted \
  --kms-key-id arn:aws:kms:<region>:<account-id>:alias/<rds-alias> \
  --multi-az \
  --db-subnet-group-name <name>-subnet-group \
  --vpc-security-group-ids "$DB_SG_ID" \
  --db-parameter-group-name <name>-params \
  --option-group-name <name>-options \
  --backup-retention-period 14 \
  --preferred-backup-window "03:00-04:00" \
  --preferred-maintenance-window "sun:04:00-sun:05:00" \
  --monitoring-interval 30 \
  --monitoring-role-arn arn:aws:iam::<account-id>:role/rds-monitoring-role \
  --enable-performance-insights \
  --performance-insights-retention-period 7 \
  --auto-minor-version-upgrade \
  --deletion-protection \
  --tags "[{Key=Environment,Value=production},{Key=Workload,Value=<name>}]"
```

## Step 5b: Create Aurora cluster (MySQL or PostgreSQL)

```bash
# Create the cluster first
aws rds create-db-cluster \
  --db-cluster-identifier <cluster> \
  --engine aurora-postgresql \
  --engine-version 16.3 \
  --master-username <admin-user> \
  --manage-master-user-password \
  --database-name <db> \
  --vpc-security-group-ids "$DB_SG_ID" \
  --db-subnet-group-name <name>-subnet-group \
  --db-cluster-parameter-group-name <name>-cluster-params \
  --storage-encrypted \
  --kms-key-id arn:aws:kms:<region>:<account-id>:alias/<rds-alias> \
  --backup-retention-period 14 \
  --preferred-backup-window "03:00-04:00" \
  --preferred-maintenance-window "sun:04:00-sun:05:00" \
  --enable-http-endpoint \
  --deletion-protection

# Create the writer instance
aws rds create-db-instance \
  --db-instance-identifier <cluster>-0 \
  --db-instance-class db.r7g.large \
  --engine aurora-postgresql \
  --db-cluster-identifier <cluster> \
  --auto-minor-version-upgrade \
  --enable-performance-insights \
  --performance-insights-retention-period 7 \
  --monitoring-interval 30 \
  --monitoring-role-arn arn:aws:iam::<account-id>:role/rds-monitoring-role \
  --tags "[{Key=Environment,Value=production},{Key=Workload,Value=<name>}]"

# Add a Reader in a different AZ for read-scaling + failover target
aws rds create-db-instance \
  --db-instance-identifier <cluster>-1 \
  --db-instance-class db.r7g.large \
  --engine aurora-postgresql \
  --db-cluster-identifier <cluster> \
  --availability-zone <region>b \
  --auto-minor-version-upgrade \
  --enable-performance-insights \
  --performance-insights-retention-period 7
```

## Step 5c: Aurora Serverless v2 cluster

```bash
aws rds create-db-cluster \
  --db-cluster-identifier <cluster> \
  --engine aurora-postgresql \
  --engine-version 16.3 \
  --master-username <admin-user> \
  --manage-master-user-password \
  --vpc-security-group-ids "$DB_SG_ID" \
  --db-subnet-group-name <name>-subnet-group \
  --db-cluster-parameter-group-name <name>-cluster-params \
  --storage-encrypted \
  --kms-key-id arn:aws:kms:<region>:<account-id>:alias/<rds-alias> \
  --backup-retention-period 14 \
  --serverless-v2-scaling-configuration MinCapacity=2,MaxCapacity=16,SecondsUntilAutoPause=0 \
  --deletion-protection

aws rds create-db-instance \
  --db-instance-identifier <cluster>-0 \
  --db-instance-class db.serverless \
  --engine aurora-postgresql \
  --db-cluster-identifier <cluster>
```

## Step 5d: Aurora MySQL with Backtrack

```bash
aws rds create-db-cluster \
  --db-cluster-identifier <cluster> \
  --engine aurora-mysql \
  --engine-version 8.0 \
  --master-username <admin-user> \
  --manage-master-user-password \
  --vpc-security-group-ids "$DB_SG_ID" \
  --db-subnet-group-name <name>-subnet-group \
  --storage-encrypted \
  --kms-key-id arn:aws:kms:<region>:<account-id>:alias/<rds-alias> \
  --backup-retention-period 14 \
  --backtrack-window 72 \
  --deletion-protection
```

## Step 6: Aurora Global Database

```bash
# Create the global cluster first
aws rds create-global-cluster \
  --global-cluster-identifier <global-name> \
  --engine aurora-mysql \
  --engine-version 8.0

# Create the primary cluster in region-1 (no engine — inherits from global)
aws rds create-db-cluster \
  --db-cluster-identifier <primary-cluster> \
  --global-cluster-identifier <global-name> \
  --region <primary-region> \
  --master-username <admin-user> \
  --manage-master-user-password \
  --vpc-security-group-ids "$DB_SG_ID" \
  --db-subnet-group-name <name>-subnet-group \
  --storage-encrypted \
  --kms-key-id arn:aws:kms:<primary-region>:<account-id>:alias/<rds-alias>

# Create secondary cluster in region-2 (read-only — no master credentials)
aws rds create-db-cluster \
  --db-cluster-identifier <secondary-cluster> \
  --global-cluster-identifier <global-name> \
  --region <secondary-region> \
  --vpc-security-group-ids "$DB_SG_ID_REGION2" \
  --db-subnet-group-name <name>-subnet-group-region2 \
  --storage-encrypted \
  --kms-key-id arn:aws:kms:<secondary-region>:<account-id>:alias/<rds-alias-region2>
```

## Step 7: Blue/Green deployment (for major-version upgrades)

```bash
aws rds create-blue-green-deployment \
  --blue-green-deployment-name <name>-bg \
  --source arn:aws:rds:<region>:<account-id>:cluster:<current-cluster> \
  --target-engine-version 8.0.mysql_aurora.3.05 \
  --target-db-parameter-group-name <new-params> \
  --target-db-cluster-parameter-group-name <new-cluster-params>
```

## Step 8: CloudWatch alarms (recommended)

```bash
# CPU utilization
aws cloudwatch put-metric-alarm \
  --alarm-name "<instance>-cpu-high" \
  --namespace AWS/RDS \
  --metric-name CPUUtilization \
  --dimensions Name=DBInstanceIdentifier,Value=<instance> \
  --statistic Average --period 300 --threshold 85 \
  --comparison-operator GreaterThanThreshold --evaluation-periods 2 \
  --alarm-actions <sns-arn>

# Free storage
aws cloudwatch put-metric-alarm \
  --alarm-name "<instance>-free-storage-low" \
  --namespace AWS/RDS \
  --metric-name FreeStorageSpace \
  --dimensions Name=DBInstanceIdentifier,Value=<instance> \
  --statistic Average --period 300 --threshold 5 \
  --unit Gigabytes \
  --comparison-operator LessThanThreshold --evaluation-periods 1 \
  --alarm-actions <sns-arn>

# Database connections
aws cloudwatch put-metric-alarm \
  --alarm-name "<instance>-connections-high" \
  --namespace AWS/RDS \
  --metric-name DatabaseConnections \
  --dimensions Name=DBInstanceIdentifier,Value=<instance> \
  --statistic Average --period 300 --threshold 180 \
  --comparison-operator GreaterThanThreshold --evaluation-periods 2 \
  --alarm-actions <sns-arn>

# CPU credit balance (burstable instances only)
aws cloudwatch put-metric-alarm \
  --alarm-name "<instance>-credit-low" \
  --namespace AWS/RDS \
  --metric-name CPUCreditBalance \
  --dimensions Name=DBInstanceIdentifier,Value=<instance> \
  --statistic Average --period 300 --threshold 10 \
  --comparison-operator LessThanThreshold --evaluation-periods 1 \
  --alarm-actions <sns-arn>
```

## Verification

```bash
aws rds describe-db-instances --db-instance-identifier <instance>
aws rds describe-db-clusters --db-cluster-identifier <cluster>   # Aurora
aws rds describe-db-parameter-groups --db-parameter-group-name <name>-params
aws rds describe-option-groups --option-group-name <name>-options
aws kms describe-key --key-id alias/<rds-alias>
aws ec2 describe-security-groups --group-ids <db-sg-id>
aws iam get-role --role-name rds-monitoring-role
aws rds describe-db-engine-versions --engine aurora-postgresql --query 'DBEngineVersions[*].EngineVersion'
```

## Terraform equivalent (aws_db_instance + aws_db_cluster)

```hcl
# Non-Aurora (MySQL/PostgreSQL)
resource "aws_db_instance" "db" {
  identifier                 = "<instance>"
  instance_class             = "db.m7g.large"
  engine                     = "postgres"
  engine_version             = "14.10"
  username                   = "<admin-user>"
  manage_master_user_password = true
  allocated_storage          = 100
  storage_type               = "gp3"
  storage_encrypted          = true
  kms_key_id                 = aws_kms_key.rds.arn
  multi_az                   = true
  db_subnet_group_name       = aws_db_subnet_group.db.name
  vpc_security_group_ids     = [aws_security_group.db.id]
  parameter_group_name       = aws_db_parameter_group.params.name
  option_group_name          = aws_db_option_group.options.name
  backup_retention_period    = 14
  preferred_backup_window    = "03:00-04:00"
  preferred_maintenance_window = "sun:04:00-sun:05:00"
  monitoring_interval        = 30
  monitoring_role_arn        = aws_iam_role.rds_monitoring.arn
  performance_insights_enabled = true
  performance_insights_retention_period = 7
  auto_minor_version_upgrade = true
  deletion_protection        = true
  copy_tags_to_snapshot      = true

  tags = {
    Environment = "production"
    Workload    = "<name>"
  }
}

# Aurora PostgreSQL cluster
resource "aws_rds_cluster" "cluster" {
  cluster_identifier              = "<cluster>"
  engine                          = "aurora-postgresql"
  engine_version                  = "16.3"
  master_username                 = "<admin-user>"
  manage_master_user_password     = true
  database_name                   = "<db>"
  vpc_security_group_ids          = [aws_security_group.db.id]
  db_subnet_group_name            = aws_db_subnet_group.db.name
  db_cluster_parameter_group_name = aws_rds_cluster_parameter_group.cluster_params.name
  storage_encrypted               = true
  kms_key_id                      = aws_kms_key.rds.arn
  backup_retention_period         = 14
  preferred_backup_window         = "03:00-04:00"
  preferred_maintenance_window    = "sun:04:00-sun:05:00"
  enable_http_endpoint            = true
  deletion_protection             = true
}

resource "aws_rds_cluster_instance" "writer" {
  identifier              = "<cluster>-0"
  cluster_identifier      = aws_rds_cluster.cluster.id
  instance_class          = "db.r7g.large"
  engine                  = "aurora-postgresql"
  monitoring_interval     = 30
  monitoring_role_arn     = aws_iam_role.rds_monitoring.arn
  performance_insights_enabled = true
  auto_minor_version_upgrade = true
}

resource "aws_rds_cluster_instance" "reader" {
  identifier              = "<cluster>-1"
  cluster_identifier      = aws_rds_cluster.cluster.id
  instance_class          = "db.r7g.large"
  engine                  = "aurora-postgresql"
  availability_zone       = "${data.aws_region.current.name}b"
  performance_insights_enabled = true
  auto_minor_version_upgrade = true
}

# Aurora Serverless v2
resource "aws_rds_cluster" "serverless" {
  cluster_identifier              = "<cluster>"
  engine                          = "aurora-postgresql"
  engine_version                  = "16.3"
  master_username                 = "<admin-user>"
  manage_master_user_password     = true
  vpc_security_group_ids          = [aws_security_group.db.id]
  db_subnet_group_name            = aws_db_subnet_group.db.name
  storage_encrypted               = true
  kms_key_id                      = aws_kms_key.rds.arn
  backup_retention_period         = 14
  serverless_v2_scaling_configuration {
    min_capacity = 2
    max_capacity = 16
  }
}

resource "aws_rds_cluster_instance" "serverless" {
  cluster_identifier = aws_rds_cluster.serverless.id
  identifier         = "<cluster>-0"
  instance_class     = "db.serverless"
  engine             = "aurora-postgresql"
}
```

## Step 2 — DB subnet group

```bash
aws rds create-db-subnet-group \
  --db-subnet-group-name <name>-subnet-group \
  --db-subnet-group-description "Subnet group for <name>" \
  --subnet-ids subnet-aaa subnet-bbb subnet-ccc
```

## Step 2 — Security group ingress

```bash
aws ec2 authorize-security-group-ingress \
  --group-id <db-sg-id> \
  --protocol tcp \
  --port 5432 \
  --source-security-group-id <app-sg-id>
```

## Step 3 — Encryption at creation (instance)

```bash
aws rds create-db-instance ... \
  --storage-encrypted \
  --kms-key-id arn:aws:kms:<region>:<account-id>:key/<cmk-id>
```

## Step 3 — Encryption at creation (cluster)

```bash
aws rds create-db-cluster ... \
  --storage-encrypted \
  --kms-key-id arn:aws:kms:<region>:<account-id>:key/<cmk-id>
```

## Step 4 — Multi-AZ enable

```bash
aws rds create-db-instance ... --multi-az
# Or enable later (causes 1-3 minute I/O suspension):
aws rds modify-db-instance --db-instance-identifier <id> --multi-az
```

## Step 4 — Aurora reader instance

```bash
aws rds create-db-instance \
  --db-instance-class db.r7g.large \
  --engine aurora-postgresql \
  --db-cluster-identifier <cluster> \
  --db-instance-identifier <cluster>-reader-1 \
  --availability-zone us-east-1b
```

## Step 5 — Backup retention

```bash
aws rds create-db-instance ... --backup-retention-period 14
# Or modify:
aws rds modify-db-instance --db-instance-identifier <id> --backup-retention-period 14
```

## Step 6 — Enhanced Monitoring

```bash
aws rds create-db-instance ... \
  --monitoring-interval 30 \
  --monitoring-role-arn arn:aws:iam::<account-id>:role/rds-monitoring-role
```

## Step 6 — Performance Insights

```bash
aws rds create-db-instance ... \
  --enable-performance-insights \
  --performance-insights-retention-period 7  # or 731
```

## Step 7 — Parameter group create + modify

```bash
aws rds create-db-parameter-group \
  --db-parameter-group-name <name>-params \
  --db-parameter-group-family postgres14 \
  --description "Custom params for <name>"

aws rds modify-db-parameter-group \
  --db-parameter-group-name <name>-params \
  --parameters "ParameterName=shared_buffers,ParameterValue={DBInstanceClassMemory/4},ApplyMethod=pending-reboot" \
               "ParameterName=rds.force_ssl,ParameterValue=1,ApplyMethod=immediate"
```

## Step 7 — Option group create + modify

```bash
aws rds create-option-group \
  --option-group-name <name>-options \
  --engine-name postgres \
  --major-engine-version 14 \
  --option-group-description "Options for <name>"

aws rds modify-option-group \
  --option-group-name <name>-options \
  --options OptionName=pgaudit,OptionSettings=[{Name=pgaudit.log,Value=write,ddl}]
```

## Step 8 — Aurora Serverless v2 scaling

```bash
aws rds create-db-cluster ... \
  --serverless-v2-scaling-configuration MinCapacity=0.5,MaxCapacity=16,SecondsUntilAutoPause=0
```

## Step 8 — Aurora Global Database

```bash
aws rds create-global-cluster \
  --global-cluster-identifier <global-name> \
  --source-cluster-identifier <primary-cluster-id> \
  --engine aurora-mysql
```

## Step 8 — Backtrack window

```bash
aws rds create-db-cluster ... \
  --backtrack-window 72   # 0-72 hours; default is 0 (disabled)
```

## Step 9 — Deletion protection

```bash
aws rds modify-db-instance --db-instance-identifier <id> --deletion-protection
# For Aurora, on the cluster:
aws rds modify-db-cluster --db-cluster-identifier <cluster> --deletion-protection
```

## Step 9 — Tags

```bash
aws rds add-tags-to-resource \
  --resource-name arn:aws:rds:<region>:<account-id>:db:<id> \
  --tags "[{Key=Environment,Value=production},{Key=Workload,Value=orders}]"
```

## Step 10 — Blue/Green deployment

```bash
aws rds create-blue-green-deployment \
  --blue-green-deployment-name <name>-bg \
  --source arn:aws:rds:<region>:<account-id>:cluster:<current-cluster> \
  --target-engine-version 8.0 \
  --target-db-parameter-group-name <new-params>
```

