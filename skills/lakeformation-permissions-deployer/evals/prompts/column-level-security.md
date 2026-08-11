# Eval: column-level-security

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — column grant, data cells filter, row filter, PII exclusion

## Prompt

Deploy column-level security for the RegionalAnalystRole on the
transactions table. Data lake admin
arn:aws:iam::123456789012:role/LFDataLakeAdmin is registered.
Database analytics_db and table transactions exist with LF-tags
already attached. Principal:
arn:aws:iam::123456789012:role/RegionalAnalystRole. Grant
column-level SELECT on columns [transaction_id, amount,
currency, timestamp, merchant, region] — explicitly EXCLUDE
PII columns [ssn, credit_card]. Create data cells filter
regional_access_filter on table analytics_db.transactions with
row filter region = 'us-east-1' and column wildcard excluding
[ssn, credit_card]. Grant SELECT on the data cells filter to
RegionalAnalystRole. Account: 123456789012. Region: us-east-1.
