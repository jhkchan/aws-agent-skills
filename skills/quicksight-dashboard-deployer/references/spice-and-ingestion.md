# SPICE and Ingestion — QuickSight Dashboard Deployer

Deep reference on SPICE engine mechanics, ingestion modes, capacity
management, refresh scheduling, and the SPICE-vs-Direct-Query decision
tree. Loaded on demand by the skill — kept out of the main SKILL.md body
so the provisioning procedure stays scannable.

## SPICE fundamentals

SPICE (Super-fast, Parallel, In-memory Calculation Engine) is
QuickSight's in-memory data store. When a dataset uses SPICE mode,
QuickSight ingests data from the source into SPICE at creation and on
schedule. All subsequent queries hit SPICE — never the source.

### SPICE capacity

| Edition | Default capacity | Scalable | Cost |
|---|---|---|---|
| Standard | 10 GB | No | Included |
| Enterprise | 500 GB+ | Yes (purchase additional) | Per-GB-month |

Capacity is per-account, shared across ALL datasets. Monitor with:

```bash
aws quicksight describe-account-settings \
  --aws-account-id 123456789012 \
  --region us-east-1
```

### SPICE ingestion lifecycle

```text
1. create-ingestion → triggered at dataset creation or manually
2. Status: INITIATED → IN_PROGRESS → COMPLETED | FAILED
3. On COMPLETED: data available for queries
4. On FAILED: check error message, fix source/query, re-trigger
5. Scheduled refresh: auto-triggers per schedule interval
```

**Check ingestion status:**

```bash
aws quicksight list-ingestions \
  --aws-account-id 123456789012 \
  --data-set-id ds-sales-metrics \
  --region us-east-1
```

### Incremental vs full refresh

- **Full refresh:** re-ingests the entire dataset. Simple but
  expensive for large datasets.
- **Incremental refresh:** only ingests new/changed rows since the
  last refresh. Requires a look-back window and a change-detection
  column (e.g., `updated_at`). Configured via
  `put-data-set-refresh-properties`.

```bash
aws quicksight put-data-set-refresh-properties \
  --aws-account-id 123456789012 \
  --data-set-id ds-sales-metrics \
  --refresh-properties '{"RefreshConfiguration":{"IncrementalRefresh":{"LookBackWindow":{"ColumnName":"updated_at","Size":1,"SizeUnit":"HOURS"},"Frequency":{"Interval":"HOURLY","TimeOfTheDay":"00:00"}}}}' \
  --region us-east-1
```

## Direct Query fundamentals

Direct Query sends every dashboard interaction as a live query to the
source. No data is cached in SPICE.

### When Direct Query is appropriate

| Source | Appropriate? | Why |
|---|---|---|
| Amazon Redshift | Yes | Columnar analytical store designed for BI workloads |
| Amazon Athena | Yes | Serverless query engine designed for ad-hoc analytics |
| Amazon RDS (OLTP) | Rarely | Connection limits, not designed for analytical scan |
| Amazon Aurora (OLTP) | Rarely | Same as RDS; use SPICE to offload |
| Amazon S3 | Via Athena only | S3 is not a query engine; use Athena Direct Query |

### Direct Query limitations

- Every filter/sort/group-by sends a new query to the source.
- Concurrent viewer limit depends on source connection pool.
- No SPICE capacity consumed, but source DB CPU/mem cost scales with
  viewer count.
- No scheduled refresh needed (data is always live).

## Decision tree: SPICE vs Direct Query

```text
Is the source an OLTP database (RDS/Aurora)?
  ├── Yes → SPICE (always, unless data is tiny and traffic is 1-2 viewers)
  └── No (Athena/Redshift)
        ├── High concurrency (> 20 viewers)? → SPICE (reduce source load)
        ├── Near-real-time requirement (< 15 min)? → Direct Query
        ├── Data volume > 500 GB? → Direct Query (SPICE capacity limit)
        └── Otherwise → SPICE (better latency, lower source load)
```

## SPICE capacity management

### Check remaining capacity

```bash
aws quicksight describe-account-subscription \
  --aws-account-id 123456789012 \
  --region us-east-1
```

### Free up SPICE capacity

Delete unused datasets or reduce dataset scope (narrow SQL, fewer
columns):

```bash
aws quicksight delete-data-set \
  --aws-account-id 123456789012 \
  --data-set-id ds-old-unused \
  --region us-east-1
```

## Common ingestion pitfalls

### Pitfall 1: SPICE capacity exhausted

Symptom: ingestion fails with capacity error. Fix: delete unused
datasets, reduce dataset scope, or purchase additional SPICE capacity
(Enterprise).

### Pitfall 2: Stale data with no refresh schedule

Symptom: dashboard shows old data. Fix: set up a refresh schedule via
`put-data-set-refresh-properties`.

### Pitfall 3: Direct Query overwhelming source DB

Symptom: source DB CPU spikes when dashboard is accessed. Fix: switch
to SPICE with a scheduled refresh.

## Terraform example

```hcl
resource "aws_quicksight_data_set" "sales" {
  data_set_id = "ds-sales-metrics"
  name        = "Sales Metrics"
  import_mode = "SPICE"

  physical_table_map {
    physical_table_map_id = "sales-table"
    custom_sql {
      data_source_arn = aws_quicksight_data_source.athena.arn
      name            = "sales_query"
      sql_query       = "SELECT * FROM sales"
      columns {
        name = "order_id"
        type = "STRING"
      }
    }
  }

  refresh_properties {
    refresh_configuration {
      incremental_refresh {
        frequency {
          interval = "HOURLY"
        }
      }
    }
  }
}
```


## Step 4 — Trigger SPICE ingestion

**Trigger SPICE ingestion:**

```bash
aws quicksight create-ingestion \
  --aws-account-id 123456789012 \
  --data-set-id ds-sales-metrics \
  --ingestion-id "ingestion-$(date +%s)" \
  --region us-east-1
```
