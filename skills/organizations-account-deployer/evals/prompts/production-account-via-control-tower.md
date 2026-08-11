# Eval: production-account-via-control-tower

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — Account Factory vending with OU-level SCP and tag policy inheritance, CloudTrail org trail, IAM Identity Center permission set, Config aggregator, alternate contacts, budget, RAM share

## Prompt

Provision a production AWS account named "prod-workload-use1" via
Control Tower Account Factory. Root email is the distribution list
aws+prod-workload@yourdomain.com. Place the account in the prod OU
(ou-prod-abc). Management account 123456789012 is in ALL_FEATURES
mode with SCP and tag policy types enabled. SCP
"DenyUnapprovedRegions" and tag policy "CostCenterRequired" should
apply via OU inheritance. The CloudTrail org trail "org-audit-trail"
already exists. Assign the "ProductionAdmins" permission set to the
"Eng-Prod" group (Identity Center instance ssoins-0123). Config
aggregator "org-aggregator" lives in delegated admin 123456789012.
Alternate contacts: Billing=finops@yourdomain.com,
Security=security@yourdomain.com,
Operations=ops@yourdomain.com. Budget: $5000/month alert at 80%.
Share the org Transit Gateway tgw-0abc123 via RAM. Region: us-east-1.
