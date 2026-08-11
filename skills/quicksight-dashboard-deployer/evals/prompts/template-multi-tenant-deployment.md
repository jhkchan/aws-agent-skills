# Eval: template-multi-tenant-deployment

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — template creation from analysis, per-tenant datasets and dashboards from template, RLS per tenant, template update propagation

## Prompt

Create a QuickSight template "sales-template" from analysis
"sales-analysis" in us-east-1, aws-account-id 123456789012,
Enterprise edition. Deploy dashboards for Tenant A and Tenant B
from the template, each with its own dataset (ds-tenant-a-sales,
ds-tenant-b-sales) and RLS rules per tenant. Tags:
Environment=production, Pattern=multi-tenant.
