# Eval: direct-query-redshift

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — Direct Query on Redshift (analytical store designed for this load), no SPICE refresh schedule, dashboard shared with readers

## Prompt

Create a QuickSight dashboard in us-east-1, aws-account-id
123456789012, Enterprise edition. Data source: Redshift cluster
"analytics-cluster" at analytics.redshift.amazonaws.com port 5439,
database "warehouse". Dataset "executive_metrics" with Direct
Query mode (Redshift is designed for analytical queries).
Dashboard "exec-dashboard" shared with reader@example.com and
analyst@example.com as READERs. Tags: Environment=production,
Audience=executive.
