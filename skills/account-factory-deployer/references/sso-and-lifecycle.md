# SSO Permission Sets and Account Lifecycle — AWS Control Tower Account Factory Deployer

Deep reference on Identity Center (SSO) permission set creation,
group-based assignment, three-way binding, permission set provisioning,
account vending lifecycle (creation, baseline deployment, SSO
provisioning), account updating (baseline updates, OU moves), and
account termination (dis-enrollment, SUSPENDED state, permanent
closure). Loaded on demand by the skill — kept out of the main
SKILL.md body so the provisioning procedure stays scannable.

## Identity Center (SSO) architecture

### Components

```text
Identity Center (formerly AWS SSO)
  ├── Identity Store
  │     ├── Users (synced from AD, Okta, or created locally)
  │     └── Groups (e.g., "PlatformTeam", "SecurityTeam")
  ├── Permission Sets
  │     ├── AWSAdministratorAccess (managed policy)
  │     ├── AWSReadOnlyAccess (managed policy)
  │     └── DataEngineerAccess (custom inline policy)
  └── Account Assignments
        └── principal + permission set + account (three-way binding)
```

### Permission set lifecycle

```text
1. Create permission set in Identity Center
   → aws sso-admin create-permission-set
2. Attach managed or inline policies
   → aws sso-admin attach-managed-policy-to-permission-set
   → aws sso-admin put-inline-policy-to-permission-set
3. Assign to principal (user or group) for an account
   → aws sso-admin create-account-assignment
4. Provision the permission set to the account
   → aws sso-admin provision-permission-set
5. User accesses via Identity Center portal
   → authenticates → sees account list → assumes role
```

**Critical:** steps 3 and 4 are separate operations. Step 3 creates
the assignment binding, but the user cannot access the account until
step 4 pushes the permission set to the account as an IAM role. This
is the #1 cause of "SSO assignment exists but no access" issues.

## Creating permission sets

### With a managed policy

```bash
PERMISSION_SET_ARN=$(aws sso-admin create-permission-set \
  --instance-arn "$SSO_INSTANCE_ARN" \
  --name "DataEngineerAccess" \
  --description "Data engineering read-write access" \
  --session-duration "PT8H" \
  --query 'PermissionSet.PermissionSetArn' --output text)

aws sso-admin attach-managed-policy-to-permission-set \
  --instance-arn "$SSO_INSTANCE_ARN" \
  --permission-set-arn "$PERMISSION_SET_ARN" \
  --managed-policy-arn "arn:aws:iam::aws:policy/AWSGlueConsoleFullAccess"

aws sso-admin attach-managed-policy-to-permission-set \
  --instance-arn "$SSO_INSTANCE_ARN" \
  --permission-set-arn "$PERMISSION_SET_ARN" \
  --managed-policy-arn "arn:aws:iam::aws:policy/AmazonS3FullAccess"
```

### With a custom inline policy

```bash
aws sso-admin put-inline-policy-to-permission-set \
  --instance-arn "$SSO_INSTANCE_ARN" \
  --permission-set-arn "$PERMISSION_SET_ARN" \
  --inline-policy '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "glue:*",
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ],
        "Resource": "*"
      },
      {
        "Effect": "Deny",
        "Action": "iam:DeleteRole",
        "Resource": "*"
      }
    ]
  }'
```

### Session duration

| Duration | Use case |
|---|---|
| PT1H (1 hour) | Break-glass / emergency access |
| PT4H (4 hours) | Short operational tasks |
| PT8H (8 hours) | Standard workday (recommended default) |
| PT12H (12 hours) | Long development sessions |

After the session expires, the user must re-authenticate. Choose the
shortest duration that covers the typical work session.

## Group-based assignment (scaling pattern)

### Why groups, not users

Assigning permission sets to individual users does not scale:

```text
Per-user assignment:
  10 accounts × 50 users × 3 permission sets = 1,500 assignments
  Each new user: 10 × 3 = 30 manual assignments
  Each new account: 50 × 3 = 150 manual assignments

Group-based assignment:
  10 accounts × 3 groups × 3 permission sets = 90 assignments
  Each new user: add to group (1 operation)
  Each new account: 3 × 3 = 9 assignments (auto for OU-scoped groups)
```

### Assignment to group for a specific account

```bash
aws sso-admin create-account-assignment \
  --instance-arn "$SSO_INSTANCE_ARN" \
  --target-id "123456789012" \
  --target-type "AWS_ACCOUNT" \
  --permission-set-arn "$PERMISSION_SET_ARN" \
  --principal-type "GROUP" \
  --principal-id "$GROUP_ID"
```

### Provisioning after assignment

```bash
aws sso-admin provision-permission-set \
  --instance-arn "$SSO_INSTANCE_ARN" \
  --permission-set-arn "$PERMISSION_SET_ARN" \
  --target-id "123456789012" \
  --target-type "AWS_ACCOUNT"
```

### Verifying provisioning status

```bash
aws sso-admin describe-account-assignment-deletion-status \
  --instance-arn "$SSO_INSTANCE_ARN" \
  --account-assignment-deletion-request-id "$REQUEST_ID"
```

## Account vending lifecycle

### Complete vending flow

```text
1. PREREQUISITES CHECK
   ├── Landing zone: ENABLED
   ├── Target OU: REGISTERED with Control Tower
   ├── Email: GLOBALLY UNIQUE
   ├── Account name: UNIQUE within org
   ├── Identity Center: ENABLED
   └── Permission sets: DEFINED

2. PROVISIONING
   ├── Service Catalog provision-product
   │     → Organizations CreateAccount (internal)
   │     → Account created (5-30 min)
   │     → Placed in target OU
   │     → SCPs inherited
   │     → AWSControlTowerExecutionRole created
   │     └── Baseline StackSets deployed

3. POST-PROVISIONING
   ├── Verify account ACTIVE
   ├── Verify SCP inheritance
   ├── Verify StackSet deployment
   ├── Set alternate contacts
   ├── Create SSO account assignments
   ├── Provision permission sets to account
   └── Deploy custom StackSets (if any)

4. VERIFICATION
   ├── describe-account → Status: ACTIVE
   ├── list-policies-for-target → SCPs present
   ├── list-stack-instances → All CURRENT
   ├── list-account-assignments → Assignments present
   └── describe-account-assignment → Status: SUCCEEDED
```

## Account updating

### Updating account baseline

When the landing zone is updated, baseline StackSets are automatically
redeployed. For custom StackSets, update manually:

```bash
aws cloudformation update-stack-set \
  --stack-set-name "CustomBaseline-VPC" \
  --template-body file://custom-vpc-v2.yaml \
  --operation-preferences RegionConcurrencyType=PARALLEL,FailureToleranceCount=1
```

### Moving an account between OUs

```bash
aws organizations move-account \
  --account-id "123456789012" \
  --source-parent-id "ou-source-111" \
  --destination-parent-id "ou-dest-222"
```

**Impact of OU move:**
- SCPs change immediately (new OU's SCPs replace old)
- StackSets may be added or removed (if OUs have different StackSet targets)
- SSO assignments are NOT affected (they are account-level, not OU-level)
- Alternate contacts are NOT affected

**Always verify SCPs after moving** — the new OU may have different
preventive Guardrails, and some resources may become non-compliant.

## Account termination

### Termination flow

```text
1. PRE-TERMINATION
   ├── Verify account is not in use (check recent CloudTrail activity)
   ├── Back up critical data (S3, databases)
   ├── Notify account owners
   └── Document reason for termination

2. DIS-ENROLLMENT
   ├── Remove SSO assignments
   │     aws sso-admin delete-account-assignment
   ├── Terminate Service Catalog provisioned product
   │     aws servicecatalog terminate-provisioned-product
   └── Control Tower dis-enrolls the account
         → Removes baseline StackSets from the account
         → Removes Guardrail associations (SCPs remain at OU level)

3. ACCOUNT CLOSURE
   ├── Move account to a "Suspended" OU (optional but recommended)
   ├── Close the account via Organizations
   │     aws organizations close-account --account-id "123456789012"
   └── Account enters SUSPENDED state

4. POST-CLOSURE
   ├── Account remains in SUSPENDED state for 90 days
   ├── Data is NOT accessible during SUSPENDED period
   ├── After 90 days, account is PERMANENTLY CLOSED
   └── All resources are deleted (irreversible)
```

### Terminating the Service Catalog product

```bash
aws servicecatalog terminate-provisioned-product \
  --provisioned-product-name "data-platform-prod"
```

**This does NOT close the AWS account.** It only:
- Dis-enrolls the account from Control Tower
- Removes baseline StackSets
- Removes the product from Service Catalog

The AWS account itself remains active. To close it:

```bash
aws organizations close-account \
  --account-id "123456789012"
```

### SSO assignment removal before termination

```bash
# List all assignments for the account
aws sso-admin list-account-assignments \
  --instance-arn "$SSO_INSTANCE_ARN" \
  --account-id "123456789012" \
  --output table

# Delete each assignment
for assignment in $(aws sso-admin list-account-assignments \
  --instance-arn "$SSO_INSTANCE_ARN" \
  --account-id "123456789012" \
  --query 'AccountAssignments[*].PermissionSetArn' --output text); do
  aws sso-admin delete-account-assignment \
    --instance-arn "$SSO_INSTANCE_ARN" \
    --target-id "123456789012" \
    --target-type "AWS_ACCOUNT" \
    --permission-set-arn "$assignment" \
    --principal-type "GROUP" \
    --principal-id "$PRINCIPAL_ID"
done
```

## Email management

### Email pattern recommendation

```text
Pattern: aws+<ou>-<account-name>@<company-domain>

Rationale:
  - aws+ prefix groups all AWS emails in the inbox
  - <ou> enables filtering by organizational unit
  - <account-name> identifies the specific account
  - The + alias routes to the same inbox (Gmail, Outlook, most providers)

Examples:
  aws+prod-data-platform@company.com  → Production OU, Data Platform account
  aws+dev-sandbox-01@company.com      → Development OU, Sandbox 01 account
  aws+security-audit@company.com      → Security OU, Audit account
  aws+logging-archive@company.com     → Logging OU, Archive account
```

### Email uniqueness verification

```bash
# Check existing account emails
aws organizations list-accounts \
  --query 'Accounts[*].Email' --output text | tr '\t' '\n' | \
  sort | uniq -d
# If any output, those are duplicate emails (should be none)
```

**Closed accounts:** a closed account's email is reserved and CANNOT
be reused for 12 months after permanent closure. If you need to recreate
an account with the same email, you must wait or use a different email.

## Terraform examples

```hcl
# Control Tower Account Factory via Service Catalog
resource "aws_servicecatalog_provisioned_product" "data_platform" {
  name                     = "data-platform-prod"
  product_name             = "AWS Control Tower Account Factory Factory"
  provisioning_artifact_name = "Account Factory"

  provisioning_parameters {
    key   = "AccountEmail"
    value = "aws+prod-data-platform@company.com"
  }

  provisioning_parameters {
    key   = "AccountName"
    value = "data-platform-prod"
  }

  provisioning_parameters {
    key   = "ManagedOrganizationalUnit"
    value = "Custom (DataPlatform)"
  }

  provisioning_parameters {
    key   = "SSOUserEmail"
    value = "platform-lead@company.com"
  }

  provisioning_parameters {
    key   = "SSOUserFirstName"
    value = "Platform"
  }

  provisioning_parameters {
    key   = "SSOUserLastName"
    value = "Lead"
  }

  tags = {
    Environment = "production"
    OU          = "DataPlatform"
  }
}

# SSO permission set
resource "aws_ssoadmin_permission_set" "data_engineer" {
  instance_arn     = data.aws_ssoadmin_instance.this.arn
  name             = "DataEngineerAccess"
  description      = "Data engineering read-write access"
  session_duration = "PT8H"
}

# SSO account assignment (group → permission set → account)
resource "aws_ssoadmin_account_assignment" "data_team" {
  instance_arn       = data.aws_ssoadmin_instance.this.arn
  permission_set_arn = aws_ssoadmin_permission_set.data_engineer.arn
  principal_id       = data.aws_identitystore_group.data_team.group_id
  principal_type     = "GROUP"
  target_id          = "123456789012"
  target_type        = "AWS_ACCOUNT"
}
```
