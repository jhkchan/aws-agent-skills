# Subnet Group and Connection Sizing — RDS Proxy Deployer

Deep reference on DB subnet group configuration for multi-AZ proxy
deployment, security group associations (proxy SG and database SG),
MaxConnectionsPercent sizing based on Aurora instance class and ACU,
MaxIdleConnectionsPercent, session pinning filters, and CloudWatch
metrics. Loaded on demand by the skill — kept out of the main SKILL.md
body so the provisioning procedure stays scannable.

## DB subnet group configuration

### Multi-AZ requirement

RDS Proxy requires a DB subnet group spanning at least 2 AZs. If all
subnets are in the same AZ, the proxy is single-AZ and not highly
available.

```bash
# Create a DB subnet group spanning 3 AZs
aws rds create-db-subnet-group \
  --db-subnet-group-name "my-proxy-subnet-group" \
  --db-subnet-group-description "Subnet group for RDS Proxy" \
  --subnet-ids subnet-aaa subnet-bbb subnet-ccc \
  --region us-east-1
```

### Verify AZ distribution

```bash
aws ec2 describe-subnets \
  --subnet-ids subnet-aaa subnet-bbb subnet-ccc \
  --query 'Subnets[*].{SubnetId:SubnetId,AZ:AvailabilityZone}' \
  --region us-east-1 --output table
```

Output:
```text
------------------------------
|        DescribeSubnets     |
+------------+----------------+
| SubnetId   |      AZ        |
+------------+----------------+
| subnet-aaa | us-east-1a     |
| subnet-bbb | us-east-1b     |
| subnet-ccc | us-east-1c     |
+------------+----------------+
```

If all subnets show the same AZ, the proxy will be single-AZ.

## Security group associations

### The two security groups

RDS Proxy involves TWO security groups:

1. **Proxy security group:** attached to the proxy. Controls ingress
   from the application to the proxy.
2. **Database security group:** attached to the Aurora/RDS cluster.
   Controls ingress from the proxy to the database.

### Proxy security group rules

```bash
# Create the proxy security group
PROXY_SG=$(aws ec2 create-security-group \
  --group-name "rds-proxy-sg" \
  --description "Security group for RDS Proxy" \
  --vpc-id vpc-aaa11122 \
  --query 'GroupId' --output text --region us-east-1)

# Allow ingress from the application to the proxy (port 5432 for PostgreSQL)
aws ec2 authorize-security-group-ingress \
  --group-id "$PROXY_SG" \
  --protocol tcp --port 5432 \
  --source-security-group-id sg-app111 \
  --region us-east-1
```

### Database security group rules (CRITICAL)

```bash
# Allow ingress from the PROXY SG to the DATABASE SG
aws ec2 authorize-security-group-ingress \
  --group-id sg-database222 \
  --protocol tcp --port 5432 \
  --source-security-group-id "$PROXY_SG" \
  --region us-east-1
```

**Without the database SG → proxy SG rule, connections time out.** The
proxy creates successfully, but all database connections fail because
the database rejects the proxy's traffic. This is the #1 forgotten
network configuration.

## MaxConnectionsPercent sizing

### Aurora provisioned instances

For Aurora provisioned instances, `max_connections` is determined by
the instance class:

| Instance Class | Approximate max_connections |
|---|---|
| db.r6g.large | ~2,100 |
| db.r6g.xlarge | ~4,200 |
| db.r6g.2xlarge | ~8,400 |
| db.r6g.4xlarge | ~16,800 |
| db.r6g.8xlarge | ~33,600 |

MaxConnectionsPercent is a PERCENTAGE of this value.

### Aurora Serverless v2

For Aurora Serverless v2, `max_connections` is determined by the ACU
allocation:

| ACU | Approximate max_connections |
|---|---|
| 2 (minimum) | ~90 |
| 4 | ~180 |
| 8 | ~375 |
| 16 | ~750 |
| 32 | ~1,500 |
| 64 | ~3,000 |

Formula: approximately 46-47 connections per ACU.

### Recommended MaxConnectionsPercent

| Scenario | Recommended % | Rationale |
|---|---|---|
| Proxy is the only connection source | 90% | Leaves 10% for admin/superuser |
| Mixed workload (proxy + direct) | 60-75% | Leaves headroom for non-proxy connections |
| Aurora Serverless v2 (low ACU) | 75% | Conservative; avoids starving the DB at low ACU |
| Aurora Serverless v2 (high ACU) | 60% | Plenty of capacity; reduce proxy footprint |
| Unknown workload | 75% | Safe default for most use cases |

### Setting MaxConnectionsPercent

MaxConnectionsPercent is set on the TARGET GROUP, not the proxy itself.

```bash
aws rds modify-db-proxy-target-group \
  --db-proxy-name "my-app-proxy" \
  --target-group-name "default" \
  --connection-pool-config '{
    "MaxConnectionsPercent": 75,
    "MaxIdleConnectionsPercent": 50,
    "ConnectionBorrowTimeout": 120,
    "SessionPinningFilters": ["EXCLUDE_VARIABLE_SETS"]
  }' \
  --region us-east-1
```

## MaxIdleConnectionsPercent

MaxIdleConnectionsPercent controls how many idle connections the proxy
keeps open. Setting this too high wastes database connections; too low
causes connection churn (frequent open/close).

| Recommended value | Rationale |
|---|---|
| 50% (default) | Keeps half of the max connections warm for quick ramp-up |
| 25% | For cost-sensitive environments; more connection churn |
| 75% | For latency-sensitive environments; keeps most connections warm |

## Session pinning filters

Session pinning occurs when the proxy cannot reuse a connection for a
different client session (e.g., after a temporary table is created or a
session variable is set). Pinning reduces the effectiveness of
connection pooling.

```bash
# For PostgreSQL, EXCLUDE_VARIABLE_SETS reduces pinning from SET commands
aws rds modify-db-proxy-target-group \
  --db-proxy-name "my-app-proxy" \
  --target-group-name "default" \
  --connection-pool-config '{"SessionPinningFilters":["EXCLUDE_VARIABLE_SETS"]}' \
  --region us-east-1
```

**Note:** session pinning filters should be tested carefully. Some
applications rely on session variables for correctness; filtering them
out may cause unexpected behavior.

## CloudWatch metrics

RDS Proxy emits the following CloudWatch metrics automatically.

| Metric | Description | Alert threshold |
|---|---|---|
| DatabaseConnections | Active connections to the DB via the proxy | Trend approaching MaxConnectionsPercent |
| CPUUtilization | Proxy instance CPU usage | Sustained > 80% |
| MaxConnectionsPercent | Current connections as % of configured max | Sustained > 90% |
| DataReceived | Throughput (bytes received) | Capacity planning |
| DataWritten | Throughput (bytes written) | Capacity planning |

### Create CloudWatch alarms

```bash
# Alarm for high connection utilization
aws cloudwatch put-metric-alarm \
  --alarm-name "rds-proxy-high-connections" \
  --namespace "AWS/RDS" \
  --metric-name "DatabaseConnections" \
  --dimensions Name=DBProxy,Value=my-app-proxy \
  --statistic Average \
  --period 300 \
  --threshold 200 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --alarm-actions "arn:aws:sns:us-east-1:123456789012:alerts" \
  --region us-east-1

# Alarm for high CPU
aws cloudwatch put-metric-alarm \
  --alarm-name "rds-proxy-high-cpu" \
  --namespace "AWS/RDS" \
  --metric-name "CPUUtilization" \
  --dimensions Name=DBProxy,Value=my-app-proxy \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 3 \
  --alarm-actions "arn:aws:sns:us-east-1:123456789012:alerts" \
  --region us-east-1
```

## Terraform examples

```hcl
# DB subnet group
resource "aws_db_subnet_group" "proxy" {
  name = "my-proxy-subnet-group"
  subnet_ids = [aws_subnet.proxy_a.id, aws_subnet.proxy_b.id, aws_subnet.proxy_c.id]
}

# RDS Proxy
resource "aws_db_proxy" "main" {
  name = "my-app-proxy"
  engine_family = "POSTGRESQL"
  role_arn = aws_iam_role.rds_proxy.arn
  require_tls = true
  vpc_subnet_ids = aws_subnet.proxy[*].id
  vpc_security_group_ids = [aws_security_group.proxy.id]
}

# Target group with connection pool config
resource "aws_db_proxy_default_target_group" "main" {
  db_proxy_name = aws_db_proxy.main.name

  connection_pool_config {
    max_connections_percent = 75
    max_idle_connections_percent = 50
    connection_borrow_timeout = 120
    session_pinning_filters = ["EXCLUDE_VARIABLE_SETS"]
  }
}

# Target (Aurora cluster)
resource "aws_db_proxy_target" "main" {
  db_proxy_name = aws_db_proxy.main.name
  target_group_name = aws_db_proxy_default_target_group.main.target_group_name
  db_cluster_identifier = aws_rds_cluster.aurora.cluster_identifier
}
```
