# Example usage: athena-query-failure-troubleshooter

A walkthrough showing the skill diagnosing a SerDe separator mismatch
that produces NULL columns despite a SUCCEEDED query status,
demonstrating the symptom-to-layer triage, the SerDe-vs-data-format
comparison, the evidence-backed ROOT_CAUSE_IDENTIFIED verdict, and the
SerDe property root cause.

## Input (user prompt)

> Our Athena query on `analytics.orders_csv` started returning NULL for
> `customer_id` and `amount` columns this morning. The query shows
> SUCCEEDED status but the data is wrong — `order_id` contains the
> entire tab-delimited row. We checked the S3 data and it's fine.
> Please help us find the root cause.

```text
Database: analytics
Table: orders_csv
Query: SELECT * FROM analytics.orders_csv LIMIT 10
QueryStatus: SUCCEEDED (no error)

DDL:
  CREATE EXTERNAL TABLE analytics.orders_csv (
    order_id    STRING,
    customer_id STRING,
    amount      STRING
  )
  ROW FORMAT SERDE
    'org.apache.hadoop.hive.serde2.OpenCSVSerDe'
  WITH SERDEPROPERTIES (
    'separatorChar' = ','
  )
  STORED AS INPUTFORMAT
    'org.apache.hadoop.mapred.TextInputFormat'
  OUTPUTFORMAT
    'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat'
  LOCATION
    's3://prod-analytics/orders/'

Query result (first 3 rows):
  order_id                          customer_id  amount
  ORD001\tCUST123\t150.00           NULL         NULL
  ORD002\tCUST456\t200.00           NULL         NULL
  ORD003\tCUST789\t350.00           NULL         NULL

S3 data sample (head -3 of s3://prod-analytics/orders/data.csv):
  ORD001	CUST123	150.00
  ORD002	CUST456	200.00
  ORD003	CUST789	350.00

Workgroup: primary (Athena engine v3)
```

## Skill output

```text
TARGET: analytics.orders_csv / QueryExecutionId: (offline)
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: Table orders_csv uses OpenCSVSerDe with separatorChar=','
  but the S3 data is tab-delimited. OpenCSVSerDe splits on commas;
  a row like "ORD001\tCUST123\t150.00" is treated as a single field,
  producing NULL for columns 2 and 3. The SerDe separatorChar does
  not match the actual delimiter. The query SUCCEEDS because no error
  occurs — OpenCSVSerDe simply puts the entire row in column 1 and
  returns NULL for the missing columns (Step 2).
LAYER: SERDE_PROPERTY
EVIDENCE:
  - Symptom: SELECT * FROM analytics.orders_csv LIMIT 10 returns
    order_id = "ORD001\tCUST123\t150.00" (entire row in column 1),
    customer_id = NULL, amount = NULL for every row. Query status is
    SUCCEEDED.
  - Probe: aws glue get-table returns SerDeInfo.SerializationLibrary
    = org.apache.hadoop.hive.serde2.OpenCSVSerDe;
    SerdeInfo.Parameters.separatorChar = ",".
  - Probe: aws s3 cp s3://prod-analytics/orders/data.csv /tmp/ &&
    head -1 /tmp/data.csv returns "ORD001\tCUST123\t150.00" (tab-
    delimited, not comma).
  - Passing: Glue permissions verified (glue:GetTable allowed);
    S3 permissions verified (s3:GetObject allowed); partitions loaded
    (get-partitions returns count > 0); table LOCATION correct
    (s3://prod-analytics/orders/).
REMEDIATION:
  1. Recreate the table with the correct separatorChar:
     DROP TABLE analytics.orders_csv;
     CREATE EXTERNAL TABLE analytics.orders_csv (
       order_id STRING, customer_id STRING, amount STRING
     )
     ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerDe'
     WITH SERDEPROPERTIES ('separatorChar' = '\t')
     STORED AS TEXTFILE
     LOCATION 's3://prod-analytics/orders/';
  2. Verify: SELECT * FROM analytics.orders_csv LIMIT 10 should
     return order_id, customer_id, amount in separate columns with
     correct values.
CONFIRM: Before dropping and recreating the table, emit and await:
  "CONFIRM: About to DROP and RECREATE analytics.orders_csv with
   separatorChar='\t'. This does not affect S3 data. Proceed? (yes/no)"
```

## What the skill caught that a generic assistant misses

1. **Recognised that SUCCEEDED status does not mean correct data.** A
   generic assistant may treat the SUCCEEDED status as evidence the
   query is fine and look elsewhere. The skill immediately recognises
   that NULL columns with SUCCEEDED status is a SerDe mismatch
   signature — the SerDe parsed the data without error but put the
   wrong bytes in the wrong columns.

2. **Identified the specific SerDeProperty mismatch.** The skill reads
   the DDL SerDeProperties (`separatorChar = ','`) and compares against
   the actual S3 data (tab-delimited). The mismatch is specific:
   `separatorChar` is comma but the data uses tabs. The fix is
   `separatorChar = '\t'`, not a different SerDe or a data fix.

3. **Ruled out competing explanations.** The skill's evidence section
   confirms Glue permissions pass, S3 permissions pass, partitions are
   loaded, and the table LOCATION is correct. These are the competing
   explanations a generic assistant might chase.

4. **Provided the exact DROP+CREATE with corrected SerDeProperties.**
   The skill notes that Athena does not support `ALTER TABLE SET
   SERDEPROPERTIES` directly — the table must be dropped and recreated.
   The remediation is copy-pasteable.

## Slash-command invocation

```
/aws:troubleshoot-athena-query
```

Or via the orchestrator:

```
/aws:pipeline
You: "diagnose why SELECT * FROM analytics.orders_csv returns NULL columns"
```

The orchestrator emits
`[Phase: Troubleshoot | Skills routed: athena-query-failure-troubleshooter]`
and hands off to this skill for the diagnostic block.

## Live-account follow-up (optional, requires AWS CLI)

After remediating, validate the query returns correct data:

```bash
# Run a test query after recreating the table
aws athena start-query-execution \
  --query-string "SELECT * FROM analytics.orders_csv LIMIT 10" \
  --work-group primary \
  --query-execution-context Database=analytics \
  --profile default --output json

# Wait for completion, then get results
QUERY_ID=$(aws athena list-query-executions --work-group primary \
  --profile default --output json | jq -r '.QueryExecutions[0].QueryExecutionId')

aws athena get-query-results \
  --query-execution-id $QUERY_ID \
  --profile default --output json
```

Confirm `customer_id` and `amount` columns are populated with correct
values (not NULL).
