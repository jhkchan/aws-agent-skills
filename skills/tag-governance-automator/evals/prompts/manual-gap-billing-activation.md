# Eval prompt: manual-gap-billing-activation

Design the activation of cost allocation tags on a legacy payer
account. Emit the standard GOVERNANCE block (SCOPE, STRATEGY,
POLICY, AUTOMATION, COMPLIANCE, VERDICT, GAP, TEMPLATE).

Design reference: manual-gap-billing-activation
Account: 222222222222 (legacy payer, created pre-2020)
Region: us-east-1

Requirement: activate cost allocation tags so Environment, Owner,
Project, and CostCenter appear as dimensions in Cost Explorer and
the Cost and Usage Report.

Attempted:
  aws ce update-cost-allocation-tags-status \
    --cost-allocation-tags-status '[{"TagKey":"Environment","Status":"Active"},...]'
Result: AccessDenied — the IAM policy on this legacy payer restricts
the CE API. Billing console access is available.

All resources are already tagged correctly. Config required-tags
rule reports 100% compliance. The only gap is that Cost Explorer
shows no tag dimensions.

Provide the path forward and flag any manual steps.
