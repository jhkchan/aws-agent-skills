# Eval prompt: serde-csv-separator-mismatch

Diagnose the Athena query failure for the following table. Walk the
symptom-driven diagnostic tree and emit the standard diagnostic block
(TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: Athena query on table `analytics.orders_csv` returns NULL for
`customer_id` and `amount` columns. The query SUCCEEDS (no error) but
the data is wrong — `order_id` contains the entire tab-delimited row
as a single string.

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

The query succeeds but the data is wrong — a SerDe property mismatch.
The SerDe's `separatorChar` does not match the actual file delimiter.
