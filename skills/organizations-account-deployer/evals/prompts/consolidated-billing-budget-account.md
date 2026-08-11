# Eval: consolidated-billing-budget-account

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — Organizations create-account with consolidated billing focus, $500/month budget, billing alternate contact, Cost Explorer opt-in

## Prompt

Provision an AWS member account "marketing-sandbox-use1" via
Organizations create-account. Root email
aws+marketing@yourdomain.com. IAM role name
"OrganizationAccountAccessRole". Management account 123456789012 is
the payer with consolidated billing. Place in OU ou-sandbox-abc.
CloudTrail org trail exists. Set the billing alternate contact to
finops@yourdomain.com. Define a budget of $500/month with an alert at
90%. Enable Cost Explorer. Region: us-east-1.
