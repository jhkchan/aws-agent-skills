# Baseline (no-skill) response: greenfield-cur-athena-automated

This file captures what a generic assistant produces WITHOUT the
cur-automation-automator skill loaded — the contrast that proves the
skill adds structure (partition projection, non-primary workgroup with
DSL, hourly granularity for resource-level cost, bucket policy with
confused-deputy protection).

---

Here's a basic setup for your CUR with Athena.

1. Create the CUR in the console: Billing → Cost and Usage Reports →
   Create report. Name it `prod-cur-hourly`, hourly granularity, Parquet
   format, send to bucket `prod-cur-bucket`.

2. Wait 24 hours for the first delivery.

3. In Athena, run this to create the table:

```sql
CREATE EXTERNAL TABLE cur_data (
  lineitem_usageaccountid string,
  lineitem_unblendedcost double,
  product_servicename string
)
PARTITIONED BY (year string, month string, day string)
STORED AS PARQUET
LOCATION 's3://prod-cur-bucket/cur/prod-cur-hourly/';
```

4. Run `MSCK REPAIR TABLE cur_data;` to load partitions.

5. Query your top services:

```sql
SELECT product_servicename, SUM(lineitem_unblendedcost) AS cost
FROM cur_data
WHERE year = '2026' AND month = '08'
GROUP BY product_servicename
ORDER BY cost DESC;
```

That's it — you have CUR data in Athena. Let me know if you need any
queries.
