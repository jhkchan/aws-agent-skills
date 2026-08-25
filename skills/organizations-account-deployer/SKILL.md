---
name: organizations-account-deployer
description: 'Provisions AWS Organizations member accounts with production defaults: account creation (create-account with unique root email, IAM role name), Control Tower Account Factory (automation, blueprints, landing zone vending), cross-account role (OrganizationAccountAccessRole), consolidated billing, SCP and tag policy attachment at correct scope, CloudTrail organization trail propagation, IAM Identity Center SSO permission sets, and latest features (Terraform aws_organizations_account, Account Factory custom baselines). Emits a READY_TO_DEPLOY checklist with verification commands. Use when provisioning a new AWS account via Organizations or Control Tower, vending a landing-zone account, wiring cross-account admin, attaching SCPs and tag policies, propagating an org trail, or assigning SSO permission sets. Triggers: create AWS account, Organizations create-account, Account Factory, OrganizationAccountAccessRole, consolidated billing, SSO, org trail, account baseline.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with organizations, controltower, sso-admin, cloudtrail, ram, sts, and iam access. Works with Terraform aws_organizations_account / aws_controltower_account / aws_ssoadmin_permission_set resources and CloudFormation AWS::Organizations::Account templates.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Governance
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, aws-organizations, control-tower, account-factory, cloudops, deploy, governance, landing-zone, sso, iam-identity-center, consolidated-billing, scp, tag-policy, org-trail, account-vending
  dependencies: aws-orchestrator
  keywords: aws, aws organizations, organizations create-account, control tower, account factory, landing zone, organizationaccountaccessrole, cross-account role, consolidated billing, sso permission set, iam identity center, scp assignment, tag policy, org trail, cloudtrail organization trail, account baseline, account vending, aws_organizations_account, aws_controltower_account, terraform organizations
  when_to_use: Invoke when the user wants to create a new AWS member account through AWS Organizations (create-account) or Control Tower Account Factory, design an account-vending / landing-zone workflow with custom baselines, wire OrganizationAccountAccessRole cross-account admin access, attach SCPs and tag policies to a new account, propagate a CloudTrail organization trail across the org, assign IAM Identity Center SSO permission sets and account assignments to a new account, set up consolidated billing, or generate provisioning CLI / Terraform templates for account creation. Do NOT invoke for SCP authoring (use organizations-scp-deployer), account-level security auditing (use organizations-scp-auditor), or standalone CloudTrail configuration outside the org context.
---

# Organizations Account Deployer

An AWS CloudOps agent skill that provisions AWS Organizations member
accounts (via `create-account` or Control Tower Account Factory) with
correct defaults. The skill walks the operator through a 10-step
provisioning procedure, captures governance, billing, audit, and access
decisions, explains why each default matters, and emits a
READY_TO_DEPLOY checklist with copy-pasteable verification commands.

## What this skill does

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#what-this-skill-does).
> Full capability summary: creation path, identity, cross-account role, billing, guardrails, audit, SSO, automation.

## Activation keywords

create AWS account, Organizations create-account, Control Tower Account
Factory, account vending, landing zone, OrganizationAccountAccessRole,
cross-account role, consolidated billing, SSO permission set, IAM
Identity Center, SCP assignment, tag policy, org trail, CloudTrail
organization trail, account baseline, aws_organizations_account,
aws_controltower_account, AWS Control Tower, AccountFactory blueprint,
RAM share.

## STRICT output contract

When this skill is invoked with an account-provisioning request
(account name, environment, governance intent, region, or a partial
specification), the agent MUST respond with the READY_TO_DEPLOY
checklist defined in the section "Output format" using the literal
all-caps labels `ACCOUNT:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. If a prerequisite is missing, the verdict is
`PREREQUISITES_MISSING` and the checklist cites the specific gap with
`[✗]` markers. This contract is what assertion-based evals and
downstream account-vending pipelines rely on; deviating from the
literal labels breaks automation silently.

## Quick navigation

| Section | When to read |
|---|---|
| §"Prerequisites" | Always — verify before provisioning |
| §"Step 1 — Creation path" | Organizations create-account vs Control Tower Account Factory |
| §"Step 2 — Account identity" | Root email, account name, IAM role name |
| §"Step 3 — Cross-account admin role" | OrganizationAccountAccessRole |
| §"Step 4 — Billing + cost" | Consolidated billing, budgets, tags |
| §"Step 5 — SCP + tag policy attachment" | Guardrails at correct scope |
| §"Step 6 — Org trail propagation" | CloudTrail organization trail |
| §"Step 7 — IAM Identity Center SSO" | Permission sets + account assignments |
| §"Step 8 — Account baselines" | Config aggregation, Config rules, RAM shares |
| §"Step 9 — Terraform / IaC vending" | aws_organizations_account, Account Factory as code |
| §"Step 10 — Latest features" | Account Factory custom baselines, AWS RAM |
| §"NEVER do these things" | Review before signing off |
| §"Output format" | The literal checklist template |
| references/creation-paths-and-baselines.md | Deep Control Tower vs Organizations + baselines |
| references/provisioning-cli-commands.md | Copy-pasteable CLI sequence |

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING** with a
specific gap citation.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| AWS account designated as the management account | `create-account` only works from this account | `aws organizations describe-organization --query 'Organization.MasterAccountId'` |
| Organization in `ALL_FEATURES` mode | Required for SCP, tag policy, IAM Identity Center integration | `aws organizations describe-organization --query 'Organization.FeatureSet'` — expect `ALL_FEATURES` |
| Unique root email for the new account | The new account's root identity — reusing it fails or locks recovery | Confirm via the email provider distribution list |
| Account name not already in use | Names should be unique for traceability | `aws organizations list-accounts --query 'Accounts[*].Name'` |
| IAM role name choice (default `OrganizationAccountAccessRole`) | Cross-account admin entry point — consistency across the org matters | `aws organizations list-accounts --query 'Accounts[*].RoleName'` |
| SCP and tag policy types enabled on root | Without `SERVICE_CONTROL_POLICY`/`TAG_POLICY` enabled, policies cannot attach | `aws organizations list-roots --query 'Roots[0].PolicyTypes'` |
| OU ID for placement (if using OU inheritance) | OU placement before account-level policies lets OU SCP/tag policy apply automatically | `aws organizations list-organizational-units-for-parent --parent-id <root-id>` |
| CloudTrail org trail exists (for audit posture) | New accounts inherit the org trail only if it already exists | `aws cloudtrail list-trails --query 'Trails[?IsOrganizationTrail==\`true\`]'` |
| IAM Identity Center instance (for SSO) | Permission sets can only be assigned if Identity Center is enabled in the management account | `aws sso-admin list-instances` |
| Control Tower landing zone (if using Account Factory) | Account Factory requires an active landing zone | `aws controltower list-landing-zones` |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## 10-step provisioning procedure

### Step 1 — Creation path (immutable — decide BEFORE vending)

The creation path is the highest-impact account-provisioning choice
and is hard to reverse (retrofitting a baseline onto a bare account is
manual work).

**Decision tree:**

```text
Does the workload need production guardrails, audit, SSO, and a VPC at
creation time?
├── YES → Control Tower Account Factory  (baseline applied at vending)
│         Requires an active landing zone.
└── NO  → Organizations create-account  (bare account in minutes)
          Apply baseline via IaC immediately if production-bound.
```

> Moved to [references/creation-paths-and-baselines.md](references/creation-paths-and-baselines.md#step-1--feature-comparison-create-account-vs-account-factory).
> Feature comparison: create-account vs Account Factory (time to ready, SCP, org trail, SSO, VPC, Config, cost).

**Common mistake:** vending a production account with
`create-account`, then retrofitting guardrails. The baseline gaps
(SCP not attached, SSO not assigned, no Config aggregation) are a
silent unaudited window. Use Account Factory for production.

### Step 2 — Account identity (root email, name, IAM role name)

These three fields are **immutable at creation** and define the
account's permanent identity.

**Root email:**
- Must be unique across all of AWS (not just your organization).
- Cannot be reused across accounts.
- Acts as the root user's identity for password reset.
- **Best practice:** use a distribution list or a programmatic alias
  (`aws+prod-workload@yourdomain.com`) owned by the organization.

**Account name:**
- Should follow a naming convention (e.g., `<env>-<workload>-<region>`).
- Used for display and `ListAccounts` filtering — not a unique
  technical constraint.

**IAM role name:**
- Default: `OrganizationAccountAccessRole`.
- The role the management account assumes for cross-account admin.
- **Critical:** use a consistent role name across the org. Mismatched
  names break cross-account automation (assume-role scripts, Lambda
  cross-account invocations, AWS Config aggregation).
- The role name **cannot be renamed** after creation.

```bash
aws organizations create-account \
  --email "aws+prod-workload@yourdomain.com" \
  --account-name "prod-workload-use1" \
  --role-name "OrganizationAccountAccessRole" \
  --iam-user-access-to-billing ALLOW \
  --tags '[{"Key":"Environment","Value":"production"},{"Key":"Workload","Value":"orders"}]'
```

**Common mistake:** using an individual's email for the root account.
When the individual leaves, password reset is lost. Always use a
distribution list.

### Step 3 — Cross-account admin role (OrganizationAccountAccessRole)

The `OrganizationAccountAccessRole` is the bootstrap cross-account
admin entry point. The management account assumes this role to manage
the new member account.

**Trust policy (created by Organizations):**
- Trusts the management account only (`root` of the management
  account ID).
- AdministratorAccess managed policy attached by default.

**Verify and assume:**

```bash
# Wait for account creation to complete (Status: ACTIVE)
aws organizations describe-create-account-status \
  --create-account-request-id <request-id>

# Once the account ID is known, assume the role from the management account
NEW_ACCOUNT_ID=$(aws organizations describe-account \
  --account-id <account-id> --query 'Account.Id' --output text)

aws sts assume-role \
  --role-arn "arn:aws:iam::${NEW_ACCOUNT_ID}:role/OrganizationAccountAccessRole" \
  --role-session-name "bootstrap"
```

**Common mistakes:** customizing the role name per account (breaks
cross-account automation); forgetting to record the account ID —
`create-account` returns a `CreateAccountStatus` ID, and the actual
account ID is available only after the status reaches `ACTIVE`
(seconds to minutes).

### Step 4 — Billing + cost (consolidated billing, budgets, tags)

All member accounts are **automatically consolidated** to the
management (payer) account. However, several per-account settings must
be wired explicitly:

- **Cost Explorer opt-in:** per-account, must be enabled
  (`aws ce update-cost-explorer-optimization-status` or via console).
- **Cost-allocation tags:** defined in the payer account; new accounts
  inherit the tag taxonomy but not the tag values.
- **Budgets:** per-account or consolidated — define a budget per
  member account to catch runaway spend early.
- **Alternate contacts (billing, security, operations):** per-account;
  must be set explicitly via `aws account put-alternate-contact`.

```bash
# Set alternate contacts (run from the member account or via assume-role)
aws account put-alternate-contact \
  --account-id "${NEW_ACCOUNT_ID}" \
  --alternate-contact-type BILLING \
  --email-address "finops@yourdomain.com" \
  --name "FinOps Team" \
  --phone-number "+1-555-0100" \
  --title "Finance Operations"

# Define a budget for the new account
aws budgets create-budget \
  --account-id "${NEW_ACCOUNT_ID}" \
  --budget file://budget.json \
  --notifications-with-subscribers file://notifications.json
```

**Common mistake:** assuming consolidated billing means cost
visibility is automatic. Cost Explorer and budgets must be enabled
per account.

### Step 5 — SCP + tag policy attachment (guardrails at correct scope)

Guardrails (SCPs and tag policies) are inherited from OUs. The
**scope** of attachment matters: attach at the OU level for inherited
guardrails, attach at the account level only for exceptions.

**Decision:** default OU-level attachment (account inherits
automatically when placed in the OU); exception account-level
attachment for one-off deviations.

```bash
# Verify SCP policy type is enabled on the root
aws organizations list-roots --query 'Roots[0].PolicyTypes'

# Attach an SCP to the OU (the new account will inherit)
aws organizations attach-policy \
  --policy-id <scp-policy-id> \
  --target-id <ou-id>

# Attach a tag policy to the OU
aws organizations attach-policy \
  --policy-id <tag-policy-id> \
  --target-id <ou-id>
```

**Common mistakes:**
- Attaching SCPs at account level when an OU-level policy would do
  (creates drift — the account does not inherit future OU updates).
- Forgetting that the default `FullAWSAccess` SCP at the root keeps
  every account usable. Removing it without replacing it locks every
  account in the org.
- Forgetting that SCPs **filter**, never grant. A new account still
  needs IAM identity policies for actual access.

### Step 6 — CloudTrail org trail propagation

A CloudTrail organization trail is inherited by **all** member
accounts — including new accounts created after the trail exists.

```bash
aws cloudtrail list-trails --query 'Trails[?IsOrganizationTrail==`true`]'

# If not present, create one (run from the management / delegated admin account)
aws cloudtrail create-trail \
  --name org-audit-trail \
  --s3-bucket-name org-audit-logs-<management-account-id> \
  --is-organization-trail \
  --enable-log-file-validation
```

**Delegated administrator** (for security separation):

```bash
aws organizations delegate-administrator \
  --service-principal cloudtrail.amazonaws.com \
  --account-id <logging-account-id>
```

**Common mistakes:** creating a per-account trail in the new account
instead of relying on the org trail (duplicated logs, cost, and
management); forgetting that an org trail is inherited by **new**
accounts only if the trail already exists at create-account time.

### Step 7 — IAM Identity Center SSO (permission sets + assignments)

IAM Identity Center (successor to AWS SSO) is the canonical way to
grant human and machine access to member accounts. Permission sets are
defined once in the management account and assigned to accounts.

```bash
aws sso-admin list-instances

# Account assignment: principal (group) + permission set + account
aws sso-admin create-account-assignment \
  --instance-arn <sso-instance-arn> \
  --target-id "${NEW_ACCOUNT_ID}" \
  --target-type AWS_ACCOUNT \
  --permission-set-arn <permission-set-arn> \
  --principal-type GROUP \
  --principal-id <group-id>
```

**Common mistakes:** forgetting that a new account is **silent and
inaccessible** via SSO until at least one permission set is assigned
(`OrganizationAccountAccessRole` is bootstrap-only); assigning
permission sets at account level when an OU-level account assignment
would inherit cleanly.

### Step 8 — Account baselines (Config aggregation, Config rules, RAM shares)

Beyond guardrails and audit, a baseline typically includes:

- **AWS Config aggregator:** centralize Config findings in a delegated
  administrator account.
- **Config rules / conformance packs:** CIS AWS Foundations, security
  best practices.
- **AWS RAM shares:** share Transit Gateway, License Manager, and
  other resources across the org.

```bash
# Config aggregator (run from the delegated administrator account)
aws configservice put-configuration-aggregator \
  --configuration-aggregator-name org-aggregator \
  --organization-aggregation-source \
    RoleArn=arn:aws:iam::<delegated-admin>:role/ConfigAggregatorRole,\
    AllAwsRegions=true

# Share a Transit Gateway with the new account via RAM
aws ram create-resource-share \
  --name org-tgw-share \
  --resource-arns arn:aws:ec2:us-east-1:<mgmt-account>:transit-gateway/tgw-0abc \
  --principals <new-account-id>
```

**Common mistake:** skipping the baseline for "speed." A new account
without Config aggregation is invisible to security findings; without
RAM shares, networking cross-account access fails silently.

### Step 9 — Terraform / IaC vending

For landing-zone consistency, vending accounts as code via Terraform
is the production pattern.

```hcl
# Organizations create-account via Terraform
resource "aws_organizations_account" "workload" {
  name                       = "prod-workload-use1"
  email                      = "aws+prod-workload@yourdomain.com"
  iam_user_access_to_billing = "ALLOW"
  role_name                  = "OrganizationAccountAccessRole"
  parent_id                  = aws_organizations_organizational_unit.workload.id

  tags = {
    Environment = "production"
    Workload    = "orders"
  }
}

# IAM Identity Center permission set assignment
resource "aws_ssoadmin_account_assignment" "admins" {
  instance_arn       = data.aws_ssoadmin_instances.main.arns[0]
  permission_set_arn = aws_ssoadmin_permission_set.admins.arn
  principal_id       = aws_identitystore_group.admins.group_id
  principal_type     = "GROUP"
  target_id          = aws_organizations_account.workload.id
  target_type        = "AWS_ACCOUNT"
}

# CloudTrail org trail (created once from the management account)
resource "aws_cloudtrail_organization_trail" "audit" {
  name                       = "org-audit-trail"
  s3_bucket_name             = aws_s3_bucket.audit_logs.id
  enable_log_file_validation = true
  is_organization_trail      = true
  kms_key_id                 = aws_kms_key.audit.arn
}
```

**Common mistake:** mixing Terraform-vended and console-vended accounts
in the same org. Pick one vending path for consistency.

### Step 10 — Latest features (2024-2026)

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#step-10--latest-features-2024-2026).
> Latest features: Account Factory custom baselines, Terraform vending, RAM org-wide sharing, alternate contacts API.

## NEVER do these things (top 5)

1. **NEVER use an individual's email for the new account's root
   email.** The root email is the permanent identity of the new
   account's root user. When the individual leaves, password reset is
   lost. Always use a distribution list owned by the organization.

2. **NEVER customize the `OrganizationAccountAccessRole` name per
   account.** A consistent role name across the org is what lets
   assume-role scripts, Lambda cross-account invocations, and Config
   aggregation work. Mismatched names break cross-account automation
   silently. Pick one role name and use it everywhere.

3. **NEVER vending a production account without the org trail already
   in place.** A new account is unaudited until the org trail is
   established. The org trail is inherited by new accounts only if it
   exists at create-account time.

4. **NEVER rely on `OrganizationAccountAccessRole` as the long-term
   access path for human users.** The role is a bootstrap entry point.
   For ongoing access, use IAM Identity Center permission sets with
   least-privilege scopes. The cross-account role is for automation
   and break-glass.

5. **NEVER attach SCPs or tag policies at the account level when an
   OU-level policy would inherit.** Account-level attachments create
   drift — the account does not pick up future OU updates. Default to
   OU-level attachment; use account-level only for one-off deviations.

**Additional critical mistakes:** never assume consolidated billing
makes per-account budgets and Cost Explorer automatic (they are not);
never remove the default `FullAWSAccess` SCP from the root without a
replacement (locks every account); never create a per-account
CloudTrail when an org trail exists (duplicated logs and cost); never
assume a new account is SSO-reachable without an account assignment;
never move an account across OUs without reviewing the SCP/tag policy
delta (effective policy changes silently); never mix console-vended and
Terraform-vended accounts in the same org.

## Output format

```text
ACCOUNT: <account-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Creation path: Organizations create-account | Control Tower Account Factory
  [✓|✗] Root email: <distribution-list-email>
  [✓|✗] Account name: <name>
  [✓|✗] IAM role name: OrganizationAccountAccessRole
  [✓|✗] Billing: Consolidated (payer: <management-account-id>)
  [✓|✗] SCP attached: <scp-name> (scope: root | OU <ou-id> | account)
  [✓|✗] Tag policy attached: <tag-policy-name> (scope: root | OU | account)
  [✓|✗] CloudTrail org trail: <trail-name> (inherited by new account)
  [✓|✗] IAM Identity Center: permission set <name> assigned to group <name>
  [✓|✗] Config aggregator: <aggregator-name> (delegated admin: <account-id>)
  [✓|✗] Alternate contacts: Billing=<email>, Security=<email>, Operations=<email>
  [✓|✗] Budget: <budget-name> ($<amount>/month, alert at <percent>%)
  [✓|✗] RAM shares: <share-name> | N/A
  [✓|✗] Baseline (Account Factory or IaC): <baseline-name> | N/A
VERIFICATION_COMMANDS:
  aws organizations describe-account --account-id <account-id>
  aws organizations list-policies-for-target --target-id <account-id>
  aws cloudtrail list-trails --query 'Trails[?IsOrganizationTrail==`true`]'
  aws sso-admin list-account-assignments --instance-arn <arn> --account-id <account-id>
```

### Worked example — production account via Control Tower Account Factory

```text
ACCOUNT: prod-workload-use1
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Creation path: Control Tower Account Factory
  [✓] Root email: aws+prod-workload@yourdomain.com
  [✓] IAM role name: OrganizationAccountAccessRole
  [✓] Billing: Consolidated (payer: 123456789012)
  [✓] SCP attached: DenyUnapprovedRegions (OU ou-prod-abc)
  [✓] Tag policy attached: CostCenterRequired (OU ou-prod-abc)
  [✓] CloudTrail org trail: org-audit-trail (inherited)
  [✓] IAM Identity Center: ProductionAdmins assigned to group Eng-Prod
  [✓] Config aggregator: org-aggregator (delegated admin: 123456789012)
  [✓] Alternate contacts: Billing=finops@, Security=security@, Operations=ops@yourdomain.com
  [✓] Budget: prod-workload-budget ($5000/month, alert at 80%)
  [✓] RAM shares: org-tgw-share
  [✓] Baseline: Account Factory blueprint (VPC, guardrails, SSO, Config)
VERIFICATION_COMMANDS:
  aws organizations describe-account --account-id 111122223333
  aws organizations list-policies-for-target --target-id 111122223333
  aws cloudtrail list-trails --query 'Trails[?IsOrganizationTrail==`true`]'
  aws sso-admin list-account-assignments --instance-arn arn:aws:sso:...:instance/ssoins-0123 --account-id 111122223333
```

## References (load on demand)

- [advanced-patterns](references/advanced-patterns.md) — mindset, reasoning framework, dependency graph, capability summary, recent AWS features (2024-2026)
- [error-handling](references/error-handling.md) — API error table: causes and fixes
- [creation-paths-and-baselines](references/creation-paths-and-baselines.md) — creation-path sizing heuristic, feature comparison, Account Factory baselines
- [provisioning-cli-commands](references/provisioning-cli-commands.md) — copy-pasteable provisioning CLI sequence

## Domain

AWS CloudOps / Organizations Account Provisioning & Landing Zone Vending.

## AWS documentation

- **AWS Organizations — create accounts** — https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_accounts_create.html
- **Control Tower Account Factory** — https://docs.aws.amazon.com/controltower/latest/userguide/account-factory.html
- **IAM Identity Center permission sets** — https://docs.aws.amazon.com/singlesignon/latest/userguide/permissionsets.html
- **CloudTrail organization trail** — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/creating-trail-organization.html
- **AWS Organizations SCPs** — https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps.html
- **Terraform aws_organizations_account** — https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/organizations_account
