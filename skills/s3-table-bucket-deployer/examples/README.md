# End-to-End Example: S3 Table Bucket Deployment

A walkthrough showing how to use the `s3-table-bucket-deployer` skill
from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning an S3 table bucket with an Apache Iceberg v2
table for sales analytics, with Athena integration via the Iceberg
REST catalog and Lake Formation permissions. The deployment needs:

- Table bucket: analytics-tables (us-east-1)
- Account: 123456789012
- Namespace: sales_analytics
- Table: orders (Iceberg v2)
- Schema: order_id (long), customer_id (long), order_date (timestamp),
  amount (double), status (string)
- Partition spec: day(order_date)
- Maintenance: default (all ENABLED)
- Athena: via REST catalog
- Lake Formation: table-level SELECT for AthenaUserRole

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-s3-table-bucket
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create an S3 table bucket named analytics-tables with an
      Iceberg v2 table in sales_analytics namespace. Schema:
      order_id, customer_id, order_date, amount, status. Partition
      by day(order_date). Set up Athena via REST catalog and Lake
      Formation."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create an s3 table bucket"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
S3_TABLES: analytics-tables / sales_analytics / orders
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Table bucket: analytics-tables (arn:aws:s3tables:us-east-1:123456789012:bucket/analytics-tables)
  [✓] Namespace: sales_analytics
  [✓] Table: orders (format: ICEBERG v2)
  [✓] Schema: 5 columns (long, long, timestamp, double, string)
  [✓] Partition spec: day(order_date)
  [✓] Maintenance — compaction: ENABLED (target 512MB, min 5 files)
  [✓] Maintenance — snapshot management: ENABLED (max 7d, min 5 snapshots)
  [✓] Maintenance — unreferenced file cleanup: ENABLED (max 30d)
  [✓] Table bucket policy: none
  [✓] Athena integration: REST catalog configured
  [✓] Lake Formation: grants applied (table-level SELECT for AthenaUserRole)
  [✓] Tags: Environment=production, Team=analytics
VERIFICATION_COMMANDS:
  aws s3tables get-table --table-bucket-arn arn:aws:s3tables:us-east-1:123456789012:bucket/analytics-tables --namespace sales_analytics --name orders --region us-east-1
  aws s3tables get-table-maintenance-configuration --table-bucket-arn arn:aws:s3tables:us-east-1:123456789012:bucket/analytics-tables --namespace sales_analytics --name orders --region us-east-1
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Create the table bucket
aws s3tables create-table-bucket \
  --name analytics-tables \
  --region us-east-1

TABLE_BUCKET_ARN="arn:aws:s3tables:us-east-1:123456789012:bucket/analytics-tables"

# Step 2: Create the namespace (REQUIRED before table creation)
aws s3tables create-namespace \
  --table-bucket-arn "$TABLE_BUCKET_ARN" \
  --namespace '{"namespace": ["sales_analytics"]}' \
  --region us-east-1

# Step 3: Create the Iceberg v2 table with schema and partition spec
aws s3tables create-table \
  --table-bucket-arn "$TABLE_BUCKET_ARN" \
  --namespace sales_analytics \
  --name orders \
  --format ICEBERG \
  --metadata '{
    "iceberg": {
      "schema": {
        "type": "struct",
        "fields": [
          {"id": 1, "name": "order_id", "type": "long", "required": true},
          {"id": 2, "name": "customer_id", "type": "long", "required": true},
          {"id": 3, "name": "order_date", "type": "timestamp", "required": true},
          {"id": 4, "name": "amount", "type": "double", "required": false},
          {"id": 5, "name": "status", "type": "string", "required": false}
        ]
      },
      "partition-spec": [
        {"name": "order_date_day", "transform": "day", "source-id": 3}
      ],
      "format-version": 2
    }
  }' \
  --region us-east-1

# Step 4: Maintenance is ENABLED by default — no action needed.
# Optionally verify the configuration:
aws s3tables get-table-maintenance-configuration \
  --table-bucket-arn "$TABLE_BUCKET_ARN" \
  --namespace sales_analytics \
  --name orders \
  --region us-east-1

# Step 5: Grant Lake Formation permissions for Athena access
aws lakeformation grant-permissions \
  --principal DataLakePrincipalIdentifier=arn:aws:iam::123456789012:role/AthenaUserRole \
  --permissions SELECT DESCRIBE \
  --resource '{"Table": {"DatabaseName": "sales_analytics", "Name": "orders"}}' \
  --region us-east-1

# Step 6: Verify Athena can query the table
aws athena start-query-execution \
  --query-string "SELECT COUNT(*) FROM sales_analytics.orders" \
  --work-group primary \
  --query-execution-context Database=sales_analytics \
  --result-configuration OutputLocation=s3://query-results-bucket/athena/ \
  --region us-east-1
```

---

## Step 4 — Post-deployment verification

```bash
# Verify table exists with correct format
aws s3tables get-table \
  --table-bucket-arn arn:aws:s3tables:us-east-1:123456789012:bucket/analytics-tables \
  --namespace sales_analytics \
  --name orders \
  --region us-east-1

# Verify maintenance configuration (all should be ENABLED)
aws s3tables get-table-maintenance-configuration \
  --table-bucket-arn arn:aws:s3tables:us-east-1:123456789012:bucket/analytics-tables \
  --namespace sales_analytics \
  --name orders \
  --region us-east-1

# Verify Lake Formation grants
aws lakeformation list-permissions \
  --principal DataLakePrincipalIdentifier=arn:aws:iam::123456789012:role/AthenaUserRole \
  --region us-east-1
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Namespace | Skips namespace creation | Namespace created before table | create-table fails without namespace (hard dependency) |
| Table format | Unspecified or v1 | Iceberg v2 explicitly | v2 enables UPDATE/DELETE/MERGE; v1 does not |
| APIs | Uses aws s3api / s3:* | Uses aws s3tables / s3tables:* | Table buckets have separate API namespace |
| Maintenance | Suggests separate compaction job | Recognizes built-in auto-maintenance | S3 Tables has compaction/snapshot/cleanup built-in |
| Athena | Points at S3 path | Uses Iceberg REST catalog | Athena reads S3 Tables via REST catalog, not S3 paths |
| Table bucket policy | Uses s3api put-bucket-policy with s3:* | Uses s3tables put-table-bucket-policy with s3tables:* | Table bucket policy is a separate policy type |
| Lake Formation | Ignores LF | Grants LF permissions | Without LF grants, Athena queries fail |

---

## Related artifacts

- **Skill definition:** `skills/s3-table-bucket-deployer/SKILL.md`
- **Maintenance and Iceberg guide:** `skills/s3-table-bucket-deployer/references/maintenance-and-iceberg.md`
- **Policy and integrations guide:** `skills/s3-table-bucket-deployer/references/table-bucket-policy-and-integrations.md`
- **Slash command:** `commands/aws/deploy-s3-table-bucket.md`
- **Eval suite:** `skills/s3-table-bucket-deployer/evals/evals.json`
- **Legacy test cases:** `skills/s3-table-bucket-deployer/eval/test-cases.yaml`
