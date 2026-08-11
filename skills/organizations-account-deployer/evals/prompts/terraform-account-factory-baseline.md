# Eval: terraform-account-factory-baseline

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — Terraform vending with Control Tower Account Factory custom baseline (SecurityBaseline StackSet, VPC, Config conformance pack), permission set assignment, org trail

## Prompt

Provision a production AWS account "payments-prod-use1" via Terraform
aws_organizations_account. Root email aws+payments@yourdomain.com.
Use the Control Tower Account Factory custom baseline that applies
the "SecurityBaseline" StackSet, VPC, and Config conformance pack at
vending. IAM role name "OrganizationAccountAccessRole". Place in OU
ou-prod-abc (inherits "DenyUnapprovedRegions" SCP and
"CostCenterRequired" tag policy). Management account 123456789012.
CloudTrail org trail "org-audit-trail" exists. Assign the
"PaymentsAdmins" permission set to the "Eng-Payments" group. Region:
us-east-1.
