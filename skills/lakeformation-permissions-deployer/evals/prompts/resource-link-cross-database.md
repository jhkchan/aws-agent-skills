# Eval: resource-link-cross-database

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — resource link, cross-database access, dual grants

## Prompt

Deploy a cross-database resource link for the reporting team.
Data lake admin
arn:aws:iam::123456789012:role/LFDataLakeAdmin is registered.
Create resource link finance_transactions_link in database
reporting_db pointing to table analytics_db.transactions. Both
databases (reporting_db, analytics_db) and the target table
(transactions) exist. Grant DESCRIBE on the resource link
finance_transactions_link in reporting_db to principal
arn:aws:iam::123456789012:role/ReportingTeamRole. Grant SELECT
on the underlying table analytics_db.transactions to the same
principal. Account: 123456789012. Region: us-east-1.
