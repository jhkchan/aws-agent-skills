# Eval prompt: copy-data-format-delimiter

Diagnose the Redshift COPY command failure for the following cluster.
Walk the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: COPY command from `s3://etl-bucket/daily/orders.csv` fails.
`STL_LOAD_ERRORS` shows errcode 1204 "Delimiter not found" at line 1.

```text
Cluster: rs-redshift-copy-delimiter
Database: analytics_db

Failed COPY command:
  COPY orders
  FROM 's3://etl-bucket/daily/orders.csv'
  IAM_ROLE 'arn:aws:iam::111111111111:role/RedshiftETLRole'
  DELIMITER ','
  FORMAT CSV;

STL_LOAD_ERRORS (latest entry):
  starttime: 2026-08-11 14:23:15
  errcode: 1204
  errmsg: "Delimiter not found"
  filename: orders.csv
  line_number: 1
  colname: order_id
  coltype: integer
  raw_line: "1001|2024-01-15|450.00|shipped"
  raw_field_value: "1001|2024-01-15|450.00|shipped"

File header (verified from S3):
  order_id|order_date|amount|status

IAM role has s3:GetObject on the bucket (verified).
File exists and is readable.
```

The data file uses pipe `|` delimiters but the COPY command specifies
`DELIMITER ','`. The raw_line in STL_LOAD_ERRORS clearly shows pipe
separators. The IAM role and S3 access are confirmed working.
