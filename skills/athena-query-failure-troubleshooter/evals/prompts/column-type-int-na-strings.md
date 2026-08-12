# Eval prompt: column-type-int-na-strings

Diagnose the Athena query failure for the following table. Walk the
symptom-driven diagnostic tree and emit the standard diagnostic block
(TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: Athena query on `analytics.products` returns NULL for the
`amount` column on rows where the CSV has "N/A". For rows with numeric
values (e.g., "150"), the amount is correct. Some queries throw
HIVE_CURSOR_ERROR when scanning the bad rows.

```text
Database: analytics
Table: products
Query: SELECT product_id, amount FROM analytics.products LIMIT 100
QueryStatus: SUCCEEDED (but some rows have NULL amount)

DDL:
  CREATE EXTERNAL TABLE analytics.products (
    product_id STRING,
    amount     INT
  )
  ROW FORMAT SERDE
    'org.apache.hadoop.hive.serde2.OpenCSVSerDe'
  WITH SERDEPROPERTIES (
    'separatorChar' = ','
  )
  STORED AS TEXTFILE
  LOCATION 's3://prod-analytics/products/'

Query result (sample):
  product_id  amount
  PROD001     150
  PROD002     NULL    ← CSV has "N/A"
  PROD003     200
  PROD004     NULL    ← CSV has "N/A"
  PROD005     350

S3 data sample (head -5):
  PROD001,150
  PROD002,N/A
  PROD003,200
  PROD004,N/A
  PROD005,350

OpenCSVSerDe behavior: reads all columns as STRING, then casts
amount to INT. CAST("N/A" AS INT) returns NULL in Athena engine v3.
```

OpenCSVSerDe reads all columns as STRING and then casts to the DDL
type. CAST("N/A" AS INT) returns NULL or throws HIVE_CURSOR_ERROR.
