# Eval: enterprise-spice-athena-dashboard

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — Enterprise edition, SPICE ingestion from Athena, hourly refresh schedule, row-level security via rules dataset

## Prompt

Create a QuickSight dashboard in us-east-1 (aws-account-id
123456789012, Enterprise edition). Data source: Athena workgroup
"primary". Dataset "sales_metrics" with SPICE mode, hourly refresh.
Analysis with 2 sheets. Dashboard "sales-dashboard". Enable
row-level security using a rules dataset mapping users to region
values. Tags: Environment=production, Domain=sales.
