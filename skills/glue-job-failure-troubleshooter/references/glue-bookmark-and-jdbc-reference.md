# Glue Bookmark and JDBC Connection Reference

Supplementary reference for the Glue Job Failure Troubleshooter skill.
Loaded on-demand when a diagnostic needs bookmark state detail, JDBC
connection setup, security group rules, or partition-management
commands.

## Job bookmark

Job bookmarking allows a Glue job to track the last-processed
partition value and process only new data on subsequent runs.

### How bookmarking works

1. The job reads from a source (Data Catalog table or S3 path).
2. The source has partition columns (e.g., `year`, `month`, `day`).
3. Glue records the last-processed partition value in the bookmark
   state (stored internally by Glue).
4. On the next run, Glue reads only partitions newer than the
   bookmark value.

### Bookmark options

```bash
# Enable bookmarking
aws glue start-job-run --job-name <name> \
  --arguments '{"--job-bookmark-option":"job-bookmark-enable"}'

# Disable bookmarking (process all data every run)
aws glue start-job-run --job-name <name> \
  --arguments '{"--job-bookmark-option":"job-bookmark-disable"}'

# Pause bookmarking (bookmark state is preserved but not advanced)
aws glue start-job-run --job-name <name> \
  --arguments '{"--job-bookmark-option":"job-bookmark-pause"}'

# Reset bookmark for a specific period
aws glue start-job-run --job-name <name> \
  --arguments '{"--job-bookmark-option":"job-bookmark-reset-period"}'
```

### Reset bookmark state

```bash
# Full reset (bookmark state cleared; next run processes all data)
aws glue reset-job-bookmark --job-name <name> --output json

# Get current bookmark state
aws glue get-job-bookmark --job-name <name> --output json

# Get bookmark state for a specific run
aws glue get-job-bookmark --job-name <name> --run-id <run-id> --output json
```

### Bookmark and partition keys

The bookmark state tracks the last-processed value of the `partition_keys`
argument in `glue_context.create_dynamic_frame.from_catalog`:

```python
# In the Glue script
datasource = glue_context.create_dynamic_frame.from_catalog(
    database="analytics",
    table_name="events_table",
    partition_keys=["event_date"],  # bookmark tracks this
    transformation_ctx="datasource")
```

If the `partition_keys` argument changes (e.g., from `["event_date"]`
to `["event_date", "event_hour"]`), the bookmark state cannot compare
because the key schema differs. The job reprocesses all data on every
run.

**Fix**: reset the bookmark after any `partition_keys` change:

```bash
aws glue reset-job-bookmark --job-name <name>
```

The first run after reset reprocesses all data (expected). Subsequent
runs process only new partitions.

### Common bookmark failure patterns

| Pattern | Cause | Fix |
|---|---|---|
| Job reprocesses all data every run | `partition_keys` changed; bookmark cannot compare | `reset-job-bookmark` |
| Job processes no data | Bookmark is ahead of the source (source data was deleted or recreated) | `reset-job-bookmark` |
| Job processes duplicate data | `--job-bookmark-option` is `job-bookmark-disable` or `job-bookmark-pause` | Set to `job-bookmark-enable` |
| Job processes data out of order | Source partitions not sorted by partition key | Sort the source or use `pushDownPredicate` |
| Bookmark state corrupted after Glue version upgrade | Internal bookmark format changed | `reset-job-bookmark` |

## JDBC connections

A Glue JDBC connection enables the job to read from or write to a
JDBC data source (RDS, Redshift, Aurora, on-prem database).

### Creating a JDBC connection

```bash
aws glue create-connection \
  --connection-input '{
    "Name": "rds-prod-connection",
    "ConnectionType": "jdbc",
    "ConnectionProperties": {
      "JDBC_CONNECTION_URL": "jdbc:postgresql://rds-prod.cluster-xxx.us-east-1.rds.amazonaws.com:5432/db",
      "USERNAME": "etl_user",
      "PASSWORD": "<secret>",
      "JDBC_ENFORCE_SSL": "false"
    },
    "PhysicalConnectionRequirements": {
      "SubnetId": "subnet-private-a",
      "SecurityGroupIdList": ["sg-glue-etl"],
      "AvailabilityZone": "us-east-1a"
    }
  }'
```

### JDBC connection requirements

For a JDBC connection to work, ALL THREE of the following must be
configured:

1. **Glue connection object** (above) — holds the JDBC URL, VPC,
   subnet, and security group.
2. **Security group on the database** — must allow inbound from the
   Glue connection's security group (`sg-glue-etl` above) on the
   database port.
3. **Route table** — the Glue connection's subnet must have a route
   to the database's subnet (same VPC, peered VPC, or TGW).

A failure at ANY of these three points produces
`Connection timed out` with no further detail.

### Verifying a JDBC connection

```bash
# Get the Glue connection
aws glue get-connection --name <connection-name> --output json | \
  jq '.Connection.{ConnectionType, ConnectionProperties, PhysicalConnectionRequirements}'

# Check the Glue connection's security group outbound
SG=$(aws glue get-connection --name <connection-name> --output json | \
  jq -r '.Connection.PhysicalConnectionRequirements.SecurityGroupIdList[]')
aws ec2 describe-security-groups --group-ids "$SG" --output json | \
  jq '.SecurityGroups[].IpPermissionsEgress'

# Check the database's security group inbound
aws ec2 describe-security-groups \
  --filters Name=group-id,Values=<db-sg-id> --output json | \
  jq '.SecurityGroups[].IpPermissions[] | select(.FromPort==<db-port>)'

# Check the route table for the Glue subnet
aws ec2 describe-route-tables \
  --filters Name=association.subnet-id,Values=<glue-subnet-id> --output json | \
  jq '.RouteTables[].Routes'
```

### Testing a JDBC connection

```bash
# Test the connection (Glue will attempt to connect and report success/failure)
aws glue test-connection --connection-name <connection-name> --output json
```

### Common JDBC failure patterns

| Pattern | Cause | Fix |
|---|---|---|
| `Connection timed out` | Database SG missing inbound rule for Glue SG | Add inbound rule on DB SG for `sg-glue-etl` on the DB port |
| `Connection refused` | Database is reachable but port is wrong or DB is down | Verify the port and DB instance state |
| `Access denied for user` | Credentials are wrong | Update the connection's `USERNAME` / `PASSWORD` |
| `SSL handshake failed` | DB requires SSL but connection has `JDBC_ENFORCE_SSL: false` | Set `JDBC_ENFORCE_SSL: true` |
| `Connection timed out` (cross-VPC) | Route table missing peering/TGW route | Add route to the database VPC |
| Job reads slowly via JDBC | Single-partition read (no JDBC partitioning) | Use `hashfield` or `hashexpression` partitioning |

## Partition management

### MSCK REPAIR TABLE

When partition data lands in S3 via an external process (Kinesis
Firehose, S3 copy, EMR), the Data Catalog table does not know about
the new partitions until a crawl or `MSCK REPAIR TABLE` runs.

```sql
-- Via Athena
MSCK REPAIR TABLE analytics.events_table;
```

```bash
# Via Athena CLI
aws athena start-query-execution \
  --query-string "MSCK REPAIR TABLE analytics.events_table" \
  --work-group <workgroup> --output json
```

### Glue crawler

A Glue crawler infers schema and adds partitions automatically:

```bash
# Start a crawler
aws glue start-crawler --name <crawler-name>

# Create a crawler on the S3 path
aws glue create-crawler \
  --name events-crawler \
  --role AWSGlueServiceRole-crawler \
  --database-name analytics \
  --targets '{"S3Targets":[{"Path":"s3://data-lake-prod/events/"}]}'
```

### Checking partition state

```bash
# Count partitions in the Data Catalog
aws glue get-partitions \
  --database analytics \
  --table-name events_table \
  --output json | jq '.Partitions | length'

# List partition values
aws glue get-partitions \
  --database analytics \
  --table-name events_table \
  --output json | \
  jq '.Partitions[].Values'

# Check the table's StorageDescriptor.Location
aws glue get-table \
  --database analytics \
  --name events_table \
  --output json | jq '.Table.StorageDescriptor.Location'
```

### Common partition failure patterns

| Pattern | Cause | Fix |
|---|---|---|
| Table exists but `df.count()` returns 0 | Partitions not registered in Data Catalog | Run `MSCK REPAIR TABLE` or a crawler |
| MSCK REPAIR adds partitions but table still returns 0 | Partition format in S3 does not match table's partition columns | Verify the S3 path format matches `year=YYYY/month=MM/day=DD` |
| Crawler adds partitions but with wrong schema | Crawler inferred a different schema than expected | Edit the table's schema or use a classifier |
| Partitions disappear after a crawler run | Crawler overwrote the table with a new schema | Use `UpdateBehavior: UPDATE_IN_DATABASE` or exclude old partitions |

## CloudWatch Logs

### Verifying log delivery

```bash
# Check the log group exists
aws logs describe-log-groups \
  --log-group-name-prefix /aws-glue/jobs --output json

# Filter logs for the failed run
aws logs filter-log-events \
  --log-group-name /aws-glue/jobs/default \
  --filter-pattern '"Container killed by YARN" OR "Table not found" OR "Connection timed out"' \
  --start-time $(date -d '-2 hours' +%s)000 --output json
```

### IAM permissions for log delivery

The job's IAM role must have:
- `logs:CreateLogStream` on the log group ARN.
- `logs:PutLogEvents` on the log group ARN.
- `logs:DescribeLogGroups` (optional, for discovery).

The `AWSGlueServiceRole` managed policy includes these. Custom roles
that omit them produce a job that runs but delivers no logs.

### Security configuration and KMS

If the job has a SecurityConfiguration with CloudWatch KMS encryption,
the KMS key must:
1. Be enabled (not disabled or pending deletion).
2. Have a key policy allowing the job's IAM role to `kms:Decrypt`.
3. Have a key policy allowing the CloudWatch Logs service to
   `kms:Encrypt` and `kms:Decrypt`.

If any of these fail, the job runs but logs are not delivered.

```bash
# Check the security configuration
aws glue get-security-configuration --name <sec-config-name> --output json | \
  jq '.SecurityConfiguration.{EncryptionConfiguration}'

# Verify the KMS key state
aws kms describe-key --key-id <key-id> --output json | \
  jq '.KeyMetadata.{KeyState, KeyManager, Enabled}'
```
