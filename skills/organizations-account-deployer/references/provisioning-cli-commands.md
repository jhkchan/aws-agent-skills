# Provisioning CLI Commands — Organizations Account Deployer

Full copy-pasteable CLI command sequence for the 10-step account
provisioning procedure. Variables to substitute: `<account-name>`,
`<root-email>`, `<region>`, `<management-account-id>`,
`<ou-id>`, `<scp-policy-id>`, `<tag-policy-id>`,
`<permission-set-arn>`, `<group-id>`, `<logging-account-id>`.

## Step 0: Prerequisites check

```bash
# Confirm the caller is in the management account
MGMT_ACCOUNT=$(aws organizations describe-organization \
  --query 'Organization.MasterAccountId' --output text)
CALLER=$(aws sts get-caller-identity --query Account --output text)
[ "$CALLER" = "$MGMT_ACCOUNT" ] || echo "ERROR: not in management account"

# Confirm ALL_FEATURES mode (required for SCP, tag policy, Identity Center)
aws organizations describe-organization \
  --query 'Organization.FeatureSet' --output text
# Expect: ALL_FEATURES

# Confirm SCP and tag policy types are enabled on the root
ROOT_ID=$(aws organizations list-roots --query 'Roots[0].Id' --output text)
aws organizations list-roots --query 'Roots[0].PolicyTypes' --output table
# Must include SERVICE_CONTROL_POLICY ENABLED and (optionally) TAG_POLICY ENABLED

# Enable policy types if missing
aws organizations enable-policy-type \
  --root-id "$ROOT_ID" \
  --policy-type SERVICE_CONTROL_POLICY

aws organizations enable-policy-type \
  --root-id "$ROOT_ID" \
  --policy-type TAG_POLICY

# Confirm CloudTrail org trail exists
aws cloudtrail list-trails \
  --query 'Trails[?IsOrganizationTrail==`true`].Name' --output text

# Confirm IAM Identity Center is enabled (for SSO)
aws sso-admin list-instances

# Confirm Control Tower landing zone (if using Account Factory)
aws controltower list-landing-zones 2>/dev/null || echo "No Control Tower"
```

## Step 1: Create the account (Organizations create-account)

```bash
# Issue the create-account request
REQUEST_ID=$(aws organizations create-account \
  --email "aws+prod-workload@yourdomain.com" \
  --account-name "prod-workload-use1" \
  --role-name "OrganizationAccountAccessRole" \
  --iam-user-access-to-billing ALLOW \
  --tags '[{"Key":"Environment","Value":"production"},{"Key":"Workload","Value":"orders"}]' \
  --query 'CreateAccountStatus.Id' --output text)

echo "CreateAccountStatus ID: $REQUEST_ID"

# Poll for completion (Status: ACTIVE)
aws organizations describe-create-account-status \
  --create-account-request-id "$REQUEST_ID"

# Once State is ACTIVE, capture the new account ID
NEW_ACCOUNT_ID=$(aws organizations describe-create-account-status \
  --create-account-request-id "$REQUEST_ID" \
  --query 'CreateAccountStatus.AccountId' --output text)

echo "New account ID: $NEW_ACCOUNT_ID"
```

## Step 2: Move the account into the target OU

```bash
# List OUs under the root
aws organizations list-organizational-units-for-parent \
  --parent-id "$ROOT_ID" \
  --query 'OrganizationalUnits[*].[Id,Name]' --output table

# Move the account into the prod OU (so it inherits OU-level SCPs and tag policies)
aws organizations move-account \
  --account-id "$NEW_ACCOUNT_ID" \
  --source-parent-id "$ROOT_ID" \
  --destination-parent-id "ou-prod-abc"
```

## Step 3: Verify cross-account admin role (OrganizationAccountAccessRole)

```bash
# Verify the role exists in the new account (assume from management account)
aws sts assume-role \
  --role-arn "arn:aws:iam::${NEW_ACCOUNT_ID}:role/OrganizationAccountAccessRole" \
  --role-session-name "verify-bootstrap" \
  --query 'Credentials.AccessKeyId' --output text
```

## Step 4: Billing, budgets, alternate contacts

```bash
# Set billing alternate contact
aws account put-alternate-contact \
  --account-id "$NEW_ACCOUNT_ID" \
  --alternate-contact-type BILLING \
  --email-address "finops@yourdomain.com" \
  --name "FinOps Team" \
  --phone-number "+1-555-0100" \
  --title "Finance Operations"

# Set security and operations alternate contacts
for contact_type in SECURITY OPERATIONS; do
  aws account put-alternate-contact \
    --account-id "$NEW_ACCOUNT_ID" \
    --alternate-contact-type "$contact_type" \
    --email-address "${contact_type,,}@yourdomain.com" \
    --name "${contact_type} Team" \
    --phone-number "+1-555-0100" \
    --title "${contact_type}"
done

# Create a monthly budget (write budget.json and notifications.json first)
aws budgets create-budget \
  --account-id "$NEW_ACCOUNT_ID" \
  --budget file://budget.json \
  --notifications-with-subscribers file://notifications.json
```

## Step 5: Attach SCP and tag policy at the OU (or account) scope

```bash
# OU-level attachment is preferred (the new account inherits automatically)
aws organizations attach-policy \
  --policy-id "<scp-policy-id>" \
  --target-id "ou-prod-abc"

aws organizations attach-policy \
  --policy-id "<tag-policy-id>" \
  --target-id "ou-prod-abc"

# Verify the policies are attached to the account (via inheritance)
aws organizations list-policies-for-target \
  --target-id "$NEW_ACCOUNT_ID" \
  --filter SERVICE_CONTROL_POLICY \
  --query 'Policies[*].[Id,Name]' --output table

aws organizations list-policies-for-target \
  --target-id "$NEW_ACCOUNT_ID" \
  --filter TAG_POLICY \
  --query 'Policies[*].[Id,Name]' --output table
```

## Step 6: CloudTrail org trail (one-time setup in the logging account)

```bash
# Run from the management (or logging delegated admin) account
# Create the org trail once — new accounts inherit automatically
aws cloudtrail create-trail \
  --name org-audit-trail \
  --s3-bucket-name "org-audit-logs-${MGMT_ACCOUNT}" \
  --is-organization-trail \
  --enable-log-file-validation \
  --kms-key-id "arn:aws:kms:us-east-1:${MGMT_ACCOUNT}:alias/audit-kms"

aws cloudtrail start-logging --name org-audit-trail

# (Optional) Delegate CloudTrail administration to the logging account
aws organizations delegate-administrator \
  --service-principal cloudtrail.amazonaws.com \
  --account-id "<logging-account-id>"
```

## Step 7: IAM Identity Center SSO permission set assignment

```bash
# Get the Identity Center instance ARN
SSO_INSTANCE_ARN=$(aws sso-admin list-instances \
  --query 'Instances[0].InstanceArn' --output text)

# Assign the ProductionAdmins permission set to the Eng-Prod group
aws sso-admin create-account-assignment \
  --instance-arn "$SSO_INSTANCE_ARN" \
  --target-id "$NEW_ACCOUNT_ID" \
  --target-type AWS_ACCOUNT \
  --permission-set-arn "<permission-set-arn>" \
  --principal-type GROUP \
  --principal-id "<group-id>"

# Verify the assignment
aws sso-admin list-account-assignments \
  --instance-arn "$SSO_INSTANCE_ARN" \
  --account-id "$NEW_ACCOUNT_ID"
```

## Step 8: Config aggregator and RAM shares

```bash
# Create the org aggregator (run from the delegated administrator account)
aws configservice put-configuration-aggregator \
  --configuration-aggregator-name org-aggregator \
  --organization-aggregation-source \
    RoleArn=arn:aws:iam::<delegated-admin>:role/ConfigAggregatorRole,AllAwsRegions=true

# Share the org's Transit Gateway with the new account via RAM
aws ram create-resource-share \
  --name "org-tgw-share" \
  --resource-arns "arn:aws:ec2:us-east-1:${MGMT_ACCOUNT}:transit-gateway/tgw-0abc123" \
  --principals "$NEW_ACCOUNT_ID"
```

## Step 9: Terraform vending (alternative to CLI)

```bash
# Apply the account-vending Terraform module
terraform init
terraform apply \
  -var="account_name=prod-workload-use1" \
  -var="root_email=aws+prod-workload@yourdomain.com" \
  -var="parent_ou_id=ou-prod-abc" \
  -var="environment=production" \
  -var="workload=orders"
```

## Step 10: Post-deployment verification

```bash
# Account state and details
aws organizations describe-account --account-id "$NEW_ACCOUNT_ID"

# Effective SCPs and tag policies
aws organizations list-policies-for-target --target-id "$NEW_ACCOUNT_ID" \
  --filter SERVICE_CONTROL_POLICY
aws organizations list-policies-for-target --target-id "$NEW_ACCOUNT_ID" \
  --filter TAG_POLICY

# Org trail exists and is logging
aws cloudtrail list-trails \
  --query 'Trails[?IsOrganizationTrail==`true`].[Name,IsLogging]' --output table

# SSO assignments
aws sso-admin list-account-assignments \
  --instance-arn "$SSO_INSTANCE_ARN" \
  --account-id "$NEW_ACCOUNT_ID"

# Config aggregator status
aws configservice describe-configuration-aggregators \
  --configuration-aggregator-names org-aggregator

# RAM shares
aws ram get-resource-shares --resource-owner SELF \
  --query 'resourceShares[*].[resourceShareName,status]' --output table

# Alternate contacts
aws account get-alternate-contact \
  --account-id "$NEW_ACCOUNT_ID" \
  --alternate-contact-type BILLING

# Budget
aws budgets describe-budget \
  --account-id "$NEW_ACCOUNT_ID" \
  --budget-name "prod-workload-budget"
```
