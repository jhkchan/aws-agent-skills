# Deployment CLI Commands — RDS Parameter Group Deployer

Full copy-pasteable CLI command sequence for all 9 provisioning steps.
Variables to substitute: `<region>`, `<pg-name>`, `<family>`, `<db-id>`,
`<cluster-id>`, `<parameter-values>`.

## Step 0: Prerequisites check

```bash
# Confirm the DB engine and version
aws rds describe-db-instances --db-instance-identifier <db-id> \
  --query 'DBInstances[].{Engine:Engine,EngineVersion:EngineVersion}'

# For Aurora clusters
aws rds describe-db-clusters --db-cluster-identifier <cluster-id> \
  --query 'DBClusters[].{Engine:Engine,EngineVersion:EngineVersion}'

# Find the correct parameter group family for the engine version
aws rds describe-db-engine-versions --engine postgres \
  --query 'DBEngineVersions[].{Version:EngineVersion,Family:DBParameterGroupFamily}'

# Check parameter data types and allowed values
aws rds describe-db-parameters --db-parameter-group-name default.postgres15 \
  --query 'Parameters[?ParameterName==`shared_buffers`].{Name:ParameterName,Value:ParameterValue,Type:DataType,Allowed:AllowedValues,ApplyType:ApplyType}'

# Check which parameters are static vs dynamic
aws rds describe-db-parameters --db-parameter-group-name default.postgres15 \
  --query 'Parameters[?ApplyType==`static`].ParameterName' --output table
```

## Step 1: Create a DB parameter group (PostgreSQL)

```bash
aws rds create-db-parameter-group \
  --db-parameter-group-name payments-pg15-params \
  --db-parameter-group-family postgres15 \
  --description "PostgreSQL 15 parameters for payments service" \
  --tags '[{"Key":"Environment","TagValue":"production"},{"Key":"Application","TagValue":"payments"}]'
```

## Step 2: Create a DB cluster parameter group (Aurora)

```bash
aws rds create-db-cluster-parameter-group \
  --db-cluster-parameter-group-name payments-aurora-pg15-params \
  --db-parameter-group-family aurora-postgresql15 \
  --description "Aurora PostgreSQL 15 cluster parameters" \
  --tags '[{"Key":"Environment","TagValue":"production"},{"Key":"Application","TagValue":"payments"}]'
```

## Step 3: Modify parameters (PostgreSQL — mix of static and dynamic)

```bash
aws rds modify-db-parameter-group \
  --db-parameter-group-name payments-pg15-params \
  --parameters '[
    {"ParameterName":"max_connections","ParameterValue":"200","ApplyMethod":"pending-reboot"},
    {"ParameterName":"shared_buffers","ParameterValue":"{DBInstanceClassMemory/4}","ApplyMethod":"pending-reboot"},
    {"ParameterName":"work_mem","ParameterValue":"8MB","ApplyMethod":"immediate"},
    {"ParameterName":"maintenance_work_mem","ParameterValue":"256MB","ApplyMethod":"immediate"},
    {"ParameterName":"wal_buffers","ParameterValue":"16MB","ApplyMethod":"immediate"},
    {"ParameterName":"checkpoint_completion_target","ParameterValue":"0.9","ApplyMethod":"immediate"},
    {"ParameterName":"effective_cache_size","ParameterValue":"{DBInstanceClassMemory*3/4}","ApplyMethod":"immediate"},
    {"ParameterName":"random_page_cost","ParameterValue":"1.1","ApplyMethod":"immediate"},
    {"ParameterName":"log_min_duration_statement","ParameterValue":"1000","ApplyMethod":"immediate"},
    {"ParameterName":"autovacuum","ParameterValue":"1","ApplyMethod":"immediate"},
    {"ParameterName":"autovacuum_naptime","ParameterValue":"30s","ApplyMethod":"immediate"}
  ]'
```

## Step 4: Modify parameters (MySQL)

```bash
aws rds modify-db-parameter-group \
  --db-parameter-group-name orders-mysql8-params \
  --parameters '[
    {"ParameterName":"innodb_buffer_pool_size","ParameterValue":"{DBInstanceClassMemory*3/4}","ApplyMethod":"immediate"},
    {"ParameterName":"max_connections","ParameterValue":"300","ApplyMethod":"pending-reboot"},
    {"ParameterName":"slow_query_log","ParameterValue":"1","ApplyMethod":"immediate"},
    {"ParameterName":"long_query_time","ParameterValue":"1","ApplyMethod":"immediate"},
    {"ParameterName":"innodb_flush_log_at_trx_commit","ParameterValue":"1","ApplyMethod":"immediate"},
    {"ParameterName":"sync_binlog","ParameterValue":"1","ApplyMethod":"immediate"},
    {"ParameterName":"character_set_server","ParameterValue":"utf8mb4","ApplyMethod":"pending-reboot"},
    {"ParameterName":"collation_server","ParameterValue":"utf8mb4_unicode_ci","ApplyMethod":"pending-reboot"},
    {"ParameterName":"binlog_format","ParameterValue":"ROW","ApplyMethod":"immediate"}
  ]'
```

## Step 5: Modify cluster parameters (Aurora)

```bash
aws rds modify-db-cluster-parameter-group \
  --db-cluster-parameter-group-name payments-aurora-pg15-params \
  --parameters '[
    {"ParameterName":"max_connections","ParameterValue":"{GREATEST({log(DBInstanceClassMemory/805306368)*80},{log(DBInstanceClassMemory/16106127360)*50})}","ApplyMethod":"pending-reboot"},
    {"ParameterName":"shared_buffers","ParameterValue":"{DBInstanceClassMemory/4}","ApplyMethod":"pending-reboot"},
    {"ParameterName":"work_mem","ParameterValue":"8MB","ApplyMethod":"immediate"},
    {"ParameterName":"checkpoint_completion_target","ParameterValue":"0.9","ApplyMethod":"immediate"},
    {"ParameterName":"log_min_duration_statement","ParameterValue":"1000","ApplyMethod":"immediate"}
  ]'
```

## Step 6: Aurora-specific parameters

```bash
# Aurora MySQL cluster parameters
aws rds modify-db-cluster-parameter-group \
  --db-cluster-parameter-group-name payments-aurora-mysql8-params \
  --parameters '[
    {"ParameterName":"aurora_enable_repl_bin_log_filter","ParameterValue":"1","ApplyMethod":"immediate"},
    {"ParameterName":"aurora_enable_hash_join","ParameterValue":"1","ApplyMethod":"immediate"},
    {"ParameterName":"binlog_format","ParameterValue":"ROW","ApplyMethod":"immediate"},
    {"ParameterName":"innodb_buffer_pool_size","ParameterValue":"{DBInstanceClassMemory*3/4}","ApplyMethod":"immediate"}
  ]'
```

## Step 7: Aurora Serverless v2 capacity configuration

```bash
# Capacity is set on the cluster, NOT in the parameter group
aws rds modify-db-cluster \
  --db-cluster-identifier payments-slsv2-cluster \
  --serverless-v2-scaling-configuration MinCapacity=2,MaxCapacity=16 \
  --apply-immediately

# Verify the scaling configuration
aws rds describe-db-clusters \
  --db-cluster-identifier payments-slsv2-cluster \
  --query 'DBClusters[].ServerlessV2ScalingConfigurationInfo'

# For Serverless v2 parameter groups — ALWAYS use formula values
aws rds modify-db-cluster-parameter-group \
  --db-cluster-parameter-group-name slsv2-pg15-params \
  --parameters '[
    {"ParameterName":"shared_buffers","ParameterValue":"{DBInstanceClassMemory/4}","ApplyMethod":"pending-reboot"},
    {"ParameterName":"work_mem","ParameterValue":"4MB","ApplyMethod":"immediate"},
    {"ParameterName":"effective_cache_size","ParameterValue":"{DBInstanceClassMemory*3/4}","ApplyMethod":"immediate"},
    {"ParameterName":"max_connections","ParameterValue":"{LEAST({DBInstanceClassMemory/9531392},5000)}","ApplyMethod":"pending-reboot"}
  ]'
```

## Step 8: Associate parameter group with DB instance

```bash
# Regular RDS instance
aws rds modify-db-instance \
  --db-instance-identifier payments-db-pg15 \
  --db-parameter-group-name payments-pg15-params \
  --apply-immediately

# Aurora cluster
aws rds modify-db-cluster \
  --db-cluster-identifier payments-aurora-cluster \
  --db-cluster-parameter-group-name payments-aurora-pg15-params \
  --apply-immediately

# Check for pending parameter changes (static params awaiting reboot)
aws rds describe-pending-maintenance-actions \
  --db-instance-identifier payments-db-pg15
```

## Step 9: Reboot if static parameters were changed

```bash
# Reboot DB instance (REQUIRED for static parameter changes)
aws rds reboot-db-instance \
  --db-instance-identifier payments-db-pg15

# For Aurora — reboot the writer instance
aws rds reboot-db-instance \
  --db-instance-identifier payments-aurora-cluster-instance-1

# Or failover the cluster (rolls the writer to a reader, then reboots)
aws rds failover-db-cluster \
  --db-cluster-identifier payments-aurora-cluster \
  --target-db-instance-identifier payments-aurora-cluster-instance-2
```

## Post-deployment verification

```bash
# Verify parameter group settings
aws rds describe-db-parameters \
  --db-parameter-group-name payments-pg15-params \
  --query 'Parameters[?Source!=`engine-default`].{Name:ParameterName,Value:ParameterValue,ApplyType:ApplyType,ApplyMethod:ApplyMethod}' \
  --output table

# Verify DB instance association
aws rds describe-db-instances \
  --db-instance-identifier payments-db-pg15 \
  --query 'DBInstances[].DBParameterGroups'

# Check pending maintenance (static params awaiting reboot)
aws rds describe-pending-maintenance-actions \
  --db-instance-identifier payments-db-pg15

# For Aurora clusters
aws rds describe-db-cluster-parameters \
  --db-cluster-parameter-group-name payments-aurora-pg15-params \
  --query 'Parameters[?Source!=`engine-default`]'

aws rds describe-db-clusters \
  --db-cluster-identifier payments-aurora-cluster \
  --query 'DBClusters[].DBClusterParameterGroup'

# Check Serverless v2 scaling
aws rds describe-db-clusters \
  --db-cluster-identifier payments-slsv2-cluster \
  --query 'DBClusters[].ServerlessV2ScalingConfigurationInfo'
```

## Terraform equivalents

```hcl
# DB Parameter Group (PostgreSQL)
resource "aws_db_parameter_group" "payments" {
  name        = "payments-pg15-params"
  family      = "postgres15"
  description = "PostgreSQL 15 parameters for payments service"

  parameter {
    name         = "max_connections"
    value        = "200"
    apply_method = "pending-reboot"
  }

  parameter {
    name         = "shared_buffers"
    value        = "{DBInstanceClassMemory/4}"
    apply_method = "pending-reboot"
  }

  parameter {
    name         = "work_mem"
    value        = "8MB"
    apply_method = "immediate"
  }

  parameter {
    name         = "checkpoint_completion_target"
    value        = "0.9"
    apply_method = "immediate"
  }

  parameter {
    name         = "effective_cache_size"
    value        = "{DBInstanceClassMemory*3/4}"
    apply_method = "immediate"
  }

  parameter {
    name         = "random_page_cost"
    value        = "1.1"
    apply_method = "immediate"
  }

  parameter {
    name         = "log_min_duration_statement"
    value        = "1000"
    apply_method = "immediate"
  }

  tags = {
    Environment = "production"
    Application = "payments"
  }
}

# Associate with DB instance
resource "aws_db_instance" "payments" {
  # ...
  parameter_group_name = aws_db_parameter_group.payments.name
}

# Aurora Cluster Parameter Group
resource "aws_rds_cluster_parameter_group" "payments_aurora" {
  name        = "payments-aurora-pg15-params"
  family      = "aurora-postgresql15"
  description = "Aurora PostgreSQL 15 cluster parameters"

  parameter {
    name         = "shared_buffers"
    value        = "{DBInstanceClassMemory/4}"
    apply_method = "pending-reboot"
  }

  parameter {
    name         = "work_mem"
    value        = "8MB"
    apply_method = "immediate"
  }

  tags = {
    Environment = "production"
    Application = "payments"
  }
}

# Aurora cluster with parameter group + Serverless v2 scaling
resource "aws_rds_cluster" "payments" {
  # ...
  db_cluster_parameter_group_name = aws_rds_cluster_parameter_group.payments_aurora.name

  serverlessv2_scaling_configuration {
    min_capacity = 2
    max_capacity = 16
  }
}

# MySQL parameter group
resource "aws_db_parameter_group" "orders_mysql" {
  name   = "orders-mysql8-params"
  family = "mysql8.0"

  parameter {
    name         = "innodb_buffer_pool_size"
    value        = "{DBInstanceClassMemory*3/4}"
    apply_method = "immediate"
  }

  parameter {
    name         = "max_connections"
    value        = "300"
    apply_method = "pending-reboot"
  }

  parameter {
    name         = "slow_query_log"
    value        = "1"
    apply_method = "immediate"
  }

  parameter {
    name         = "long_query_time"
    value        = "1"
    apply_method = "immediate"
  }
}
```

## CloudFormation equivalents

- `AWS::RDS::DBParameterGroup` — `Family`, `Description`, `Parameters`
  (list of `ParameterName`, `ParameterValue`, `ApplyMethod`).
- `AWS::RDS::DBClusterParameterGroup` — same structure, for Aurora
  clusters.
- `AWS::RDS::DBInstance` — `DBParameterGroupName` for association.
- `AWS::RDS::DBCluster` — `DBClusterParameterGroupName` for
  association. `ServerlessV2ScalingConfiguration` for capacity.
