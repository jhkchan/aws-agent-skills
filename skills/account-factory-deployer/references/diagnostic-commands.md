# Diagnostic Commands — AWS Control Tower Account Factory Deployer

Load-on-demand verification and operational CLI moved verbatim from SKILL.md.

## Step 4 — Guardrail inheritance verification commands

**Verify SCP inheritance:**

```bash
# List SCPs attached to the account's OU
aws organizations list-policies-for-target \
  --target-id "ou-bbb-dataplatform" \
  --filter SERVICE_CONTROL_POLICY \
  --query 'Policies[*].{Name:Name,Id:Id,Type:Type}' \
  --output table

# Get the effective SCPs for the account (intersection of all levels)
aws organizations list-policies-for-target \
  --target-id "123456789012" \
  --filter SERVICE_CONTROL_POLICY \
  --output table
```

**Verify Detective Guardrails:**

```bash
# Check Config rules in the account
aws configservice describe-config-rules \
  --config-rule-names "AWSControlTower" \
  --query 'ConfigRules[*].ConfigRuleName' \
  --output table \
  --profile data-platform-prod
```

## Step 5 — baseline StackSet verification

**Verify baseline StackSet deployment:**

```bash
# In the management account, check StackSet status for the new account
aws cloudformation list-stack-instances \
  --stack-set-name "AWSControlTowerLogging" \
  --query 'Summaries[?Account==`123456789012`].{Account:Account,Status:StackInstanceStatus}' \
  --output table
```

**If a StackSet fails:** check the StackSet operation details in the
management account. Common causes: missing execution role in the target
account, IAM permission issues, or conflicting resources.

## Step 7 — alternate contacts CLI

**Set alternate contacts:**

```bash
# Billing contact
aws account put-alternate-contact \
  --account-id "123456789012" \
  --alternate-contact-type "BILLING" \
  --email-address "billing@company.com" \
  --name "Finance Team" \
  --phone-number "+1-555-0100" \
  --title "Accounts Payable"

# Security contact
aws account put-alternate-contact \
  --account-id "123456789012" \
  --alternate-contact-type "SECURITY" \
  --email-address "security@company.com" \
  --name "Security Operations" \
  --phone-number "+1-555-0200" \
  --title "SOC"

# Operations contact
aws account put-alternate-contact \
  --account-id "123456789012" \
  --alternate-contact-type "OPERATIONS" \
  --email-address "ops@company.com" \
  --name "DevOps Team" \
  --phone-number "+1-555-0300" \
  --title "Platform Engineering"
```

## Step 10 — compliance status verification commands

```bash
# Verify account is in the correct OU
aws organizations list-parents \
  --child-id "123456789012" \
  --query 'Parents[0]' --output table

# Verify SCPs are inherited
aws organizations list-policies-for-target \
  --target-id "123456789012" \
  --filter SERVICE_CONTROL_POLICY \
  --output table

# Verify Config rules are deployed
aws configservice describe-config-rule \
  --config-rule-names "aws-control-tower" \
  --query 'ConfigRules[0].ConfigRuleName' \
  --output text \
  --profile data-platform-prod

# Verify Security Hub is enabled
aws securityhub describe-hub \
  --profile data-platform-prod

# Verify SSO permission set provisioning
aws sso-admin describe-account-assignment-creation-status \
  --instance-arn "$SSO_INSTANCE_ARN" \
  --account-assignment-creation-request-id "$REQUEST_ID"
```
