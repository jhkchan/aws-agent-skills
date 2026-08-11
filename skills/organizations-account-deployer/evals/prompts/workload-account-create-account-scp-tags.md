# Eval: workload-account-create-account-scp-tags

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — Organizations create-account with consolidated billing, OU-level SCP/tag policy inheritance, OrganizationAccountAccessRole bootstrap

## Prompt

Provision a new AWS member account via Organizations create-account.
Account name "analytics-pipeline-use1", root email
aws+analytics@yourdomain.com. Management account 123456789012 in
ALL_FEATURES mode. Place in the OU ou-data-abc so it inherits the
"DenyUnapprovedRegions" SCP and the "CostCenterRequired" tag policy.
IAM role name "OrganizationAccountAccessRole". Consolidated billing
under the management payer. CloudTrail org trail "org-audit-trail"
exists. Budget: $2000/month alert at 75%. Region: us-east-1.
