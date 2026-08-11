---
name: account-factory-deployer
description: >-
  Deploys AWS Control Tower Account Factory accounts with production
  defaults: account creation via Service Catalog product
  (provision-product), Organizational Unit placement, SSO assignment
  via permission sets, Guardrail inheritance (SCP, Detective, Config),
  landing zone baseline conformance, email and account name uniqueness,
  alternate contacts, compliance status verification, account
  customization via custom product (CloudFormation StackSets), vending
  new accounts, terminating accounts, and updating account baselines.
  Emits a READY_TO_DEPLOY checklist with verification commands. Use
  when creating AWS accounts via Control Tower, vending accounts to
  teams, assigning SSO permission sets, verifying Guardrail
  inheritance, customizing account baselines, or managing the account
  lifecycle. Triggers: create aws account control tower, account
  factory provision, vending new account, control tower account
  enrollment, sso permission set assignment, guardrail scp inheritance,
  account factory service catalog, control tower landing zone baseline,
  terminate aws account, custom account baseline.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). For live deployment: AWS CLI v2 with
  servicecatalog, controltower, organizations, and sso-admin access.
  Works with Terraform aws_controltower_account / aws_organizations_
  account / aws_ssoadmin_permission_set resources and CloudFormation
  AWS::ServiceCatalog::CloudFormationProvisionedProduct templates.
keywords:
  - aws
  - control tower
  - account factory
  - service catalog
  - cloudops
  - deploy
  - provisioning
  - landing zone
  - scp
  - guardrails
  - sso
  - permission set
  - organizations
  - stacksets
  - baseline
  - account vending
  - compliance
  - alternate contacts
tags:
  - aws
  - control-tower
  - account-factory
  - cloudops
  - deploy
  - governance
  - provisioning
  - landing-zone
  - scp
  - guardrails
  - sso
  - organizations
dependencies:
  - aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: Governance
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  version: 0.1.0
  author: "Jacky Chan — AWS Community Builder"
  tags:
    - aws
    - control-tower
    - account-factory
    - cloudops
    - deploy
    - governance
    - provisioning
    - landing-zone
    - scp
    - guardrails
    - sso
    - organizations
  dependencies:
    - aws-orchestrator
  keywords:
    - create aws account control tower
    - account factory provision
    - vending new account
    - control tower account enrollment
    - sso permission set assignment
    - guardrail scp inheritance
    - account factory service catalog
    - control tower landing zone baseline
    - terminate aws account
    - custom account baseline
  when_to_use: >-
    Invoke when the user wants to create AWS accounts via Control Tower
    Account Factory, vend accounts to teams, place accounts in
    Organizational Units, assign SSO permission sets, verify Guardrail
    (SCP/Detective/Config) inheritance, customize account baselines
    via CloudFormation StackSets, update account baselines, or
    terminate accounts. Do NOT invoke for AWS Organizations account
    creation outside Control Tower (use organizations-account-deployer),
    Control Tower landing zone setup/upgrade (use controltower-control-
    auditor), or SCP authoring (use organizations-scp-deployer).
---

# AWS Control Tower Account Factory Deployer

An AWS CloudOps agent skill that deploys AWS accounts via Control Tower
Account Factory with correct defaults. The skill walks the operator
through Service Catalog product provisioning, OU placement, SSO
permission set assignment, Guardrail inheritance verification, landing
zone baseline conformance, email uniqueness, alternate contacts, account
customization via StackSets, and account lifecycle management (vending,
updating, terminating), captures governance decisions, explains why each
default matters, and emits a READY_TO_DEPLOY checklist with copy-
pasteable verification commands.

## Activation keywords

create AWS account Control Tower, account factory provision, vending
new account, Control Tower account enrollment, SSO permission set
assignment, Guardrail SCP inheritance, Account Factory Service Catalog,
Control Tower landing zone baseline, terminate AWS account, custom
account baseline.

## STRICT output contract

When this skill is invoked with an Account Factory provisioning request
(create/vend an account, assign permission sets, verify Guardrails,
customize baselines, or a partial configuration), the agent MUST respond
with the READY_TO_DEPLOY checklist defined in the "Output format" section
using the literal all-caps labels `ACCOUNT_FACTORY:`, `VERDICT:`,
`CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT preface the checklist
with prose, headings, or disclaimers — emit the block as the first lines
of the response. This contract is what assertion-based evals and
downstream provisioning pipelines rely on; deviating from the literal
labels breaks automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Account Factory via Service Catalog | Core vending mechanism |
| Step 2 — Organizational Unit placement | OU topology |
| Step 3 — SSO permission set assignment | Access control |
| Step 4 — Guardrail inheritance (SCP, Detective, Config) | Compliance |
| Step 5 — Landing zone baseline conformance | Baseline enforcement |
| Step 6 — Email and account name uniqueness | Prerequisite check |
| Step 7 — Alternate contacts | Operational metadata |
| Step 8 — Account customization (custom product/StackSets) | Baseline customization |
| Step 9 — Account lifecycle (vending, updating, terminating) | Lifecycle management |
| Step 10 — Compliance status verification | Post-provision audit |
| Step 11 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/guardrails-and-baseline.md | Guardrail + baseline detail |
| references/sso-and-lifecycle.md | SSO + lifecycle detail |

## Mindset

**One-line takeaway:** Control Tower Account Factory vends AWS accounts
through a Service Catalog product. Each account is placed in an
Organizational Unit, inherits Guardrails (SCP, Detective, Config) from
the OU and landing zone, gets SSO access via permission sets, and
receives a baseline (CloudFormation StackSets for logging, security,
and operational standards). The Service Catalog product is the ONLY
supported way to create accounts that Control Tower manages — accounts
created directly via Organizations `CreateAccount` are NOT enrolled in
Control Tower and do NOT inherit Guardrails or baselines.

Three misconceptions dominate Account Factory misdesign at provisioning
time:

- **"Creating an account via Organizations is the same as Account
  Factory."** It is NOT. Organizations `CreateAccount` creates a raw
  AWS account with no Guardrails, no baseline, no SSO enrollment, and
  no landing zone integration. The account exists in the org but is
  unmanaged by Control Tower. Account Factory wraps Organizations
  `CreateAccount` with additional steps: SCP inheritance, Config
  recorder setup, CloudTrail logging, Security Hub enablement, SSO
  integration, and StackSet deployment. Using raw Organizations creates
  a governance gap that must be retroactively fixed.

- **"Guardrails apply automatically to all accounts."** Only to accounts
  in enrolled OUs. Guardrails (SCPs) are attached at the OU level in
  Organizations. An account in an OU with Guardrails inherits them
  automatically. But an account in the root or an unregistered OU gets
  NO Guardrails. The landing zone defines which OUs are registered for
  Guardrails. The #1 cause of "my account has no Guardrails" is that
  the account was placed in an OU that is not registered with Control
  Tower.

- **"SSO permission sets are assigned at the account level."** They are
  assigned at the account level, but they are DEFINED at the Identity
  Center (SSO) level and then PROVISIONED to accounts. The permission
  set must exist in Identity Center first, then be assigned to a
  principal (user or group) for a specific account (or account group).
  The assignment is a three-way binding: principal → permission set →
  account. Missing any leg of this binding means no access.

## Configuration dependency graph (novel heuristic)

Account Factory configurations are NOT independent. The landing zone
must exist before OUs can be registered. OUs must be registered before
accounts can be enrolled. The Service Catalog product must be available
before provisioning. SSO permission sets must exist before assignment.
Use this graph to sequence provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Landing zone | Control Tower enabled in the management account | landing zone version must be up to date for latest features; an outdated version silently lacks newer Guardrails | registered OUs, Account Factory |
| Registered OU | Landing zone exists; OU exists in Organizations | OU must be registered via Control Tower console or API — an unregistered OU does NOT get Guardrails even if it is in the org | Guardrail inheritance for accounts in that OU |
| Service Catalog product | Landing zone exists; Account Factory portfolio provisioned | the Account Factory product is auto-created by Control Tower; the product must be in AVAILABLE state; a deleted product blocks all new account creation | account vending |
| Account (vending) | Service Catalog product available; target OU registered; unique email and account name | account creation is asynchronous (5-30 minutes); email must be globally unique across ALL AWS accounts; a duplicate email fails the entire provisioning | managed account with Guardrails + baseline |
| SSO permission set | Identity Center enabled; permission set created in Identity Center store | permission set must be provisioned to the account before users can assume it; provisioning is a separate step from assignment | SSO access |
| SSO assignment | Permission set provisioned to account; principal exists in Identity Center | assignment is a three-way binding: principal + permission set + account; missing any leg = no access | user access to the account |
| Guardrail (SCP) | OU registered with Control Tower | SCPs are attached at the OU level; an account inherits from its OU; moving an account to a different OU changes its SCPs | preventive controls |
| Baseline (StackSet) | Landing zone deployed; account enrolled in Control Tower | StackSets deploy to the account automatically upon enrollment; a failed StackSet leaves the account with incomplete baseline (security/logging gaps) | logging, security, operational standards |
| Custom product (customization) | Account Factory portfolio exists; custom CloudFormation template published | custom products deploy additional StackSets beyond the default baseline; template errors cause StackSet drift | account-specific customization |
| Alternate contacts | Account exists; account is ACTIVE | alternate contacts (Billing, Security, Operations) are set via Account Management API; not inherited from OU | operational metadata for alerts |

**The OU-registration row is the one a baseline model misses.** Many
operators assume that any OU in the org automatically gets Guardrails.
It does NOT — the OU must be explicitly registered with Control Tower.
An account placed in an unregistered OU has NO preventive Guardrails,
NO Detective detection, and NO Config baseline. This is the #1 cause of
"my new account has no compliance controls."

**Cross-dependency gotchas:**
- The Service Catalog product (AWS Control Tower Account Factory
  Factory) is auto-created by Control Tower during landing zone setup.
  If it is deleted or misconfigured, ALL account vending stops.
- SSO permission set assignment requires TWO API calls:
  `CreatePermissionSet` (define the role), then
  `AssignPermissions` (bind to principal + account). Forgetting the
  second call means the permission set exists but no one has access.
- Account email must be globally unique. AWS rejects the entire
  provisioning if the email is already used by any AWS account,
  including closed accounts. Use a consistent email alias pattern
  (e.g., `aws+<account-name>@company.com`).
- Baseline StackSets are deployed by Control Tower's `AWSControlTower`
  role in the management account. If the StackSet execution role is
  missing or misconfigured in the target account, the StackSet fails
  silently — the account is enrolled but the baseline is incomplete.
- Moving an account between OUs changes its inherited SCPs. An account
  moved from a "Production" OU (strict SCPs) to a "Sandbox" OU (loose
  SCPs) immediately loses its production Guardrails.

## Expert heuristic: landing zone baseline propagation

A baseline model says "create an account and it's done." The correct
heuristic recognizes that Control Tower's landing zone propagates a
baseline (set of StackSets) to every enrolled account automatically.
Understanding this propagation is essential for troubleshooting
"missing baseline" issues.

```text
Landing zone baseline propagation:
  1. Control Tower Landing Zone (management account)
     → defines baseline StackSets (AWSControlTowerLogging,
        AWSControlTowerSecurity, AWSControlTowerBP-BASELINE-CLOUDTRAIL,
        etc.)
     → StackSets target all registered OUs

  2. New account vended via Account Factory
     → placed in a registered OU
     → Control Tower's AWSControlTowerExecutionRole auto-created
     → StackSets deploy to the new account via this role

  3. Baseline resources in the new account:
     ├── CloudTrail trail (logging to the logging account)
     ├── Config recorder (compliance tracking)
     ├── Security Hub (security findings)
     ├── GuardDuty (threat detection, if enabled)
     ├── IAM password policy (if configured)
     └── CloudWatch alarms (if configured in baseline)

  4. If a StackSet fails (e.g., role missing):
     → account is enrolled but baseline is INCOMPLETE
     → no CloudTrail, no Config, no Security Hub
     → the account is a compliance gap
```

**Key implication:** baseline propagation is automatic for enrolled
accounts in registered OUs, but it is NOT guaranteed to succeed. Always
verify StackSet deployment status in the management account after
vending a new account. A failed StackSet leaves a compliance gap.

## Expert heuristic: SCP inheritance from parent OU

SCPs flow top-down through the Organizations hierarchy. An account's
effective SCPs are the intersection of all SCPs at every level from the
root down to the account's OU.

```text
Organizations SCP hierarchy:
  Root
    ├── SCP: DenyLeavingOrg (preventative)
    ├── SCP: RequireMFA
    └── OU: "Production"
        ├── SCP: DenyUnapprovedRegions (only us-east-1, us-west-2, eu-west-1)
        ├── SCP: RequireEncryption (S3, EBS, RDS)
        └── Account: prod-app-001
            → effective SCPs = Root ∩ Production OU
            = DenyLeavingOrg + RequireMFA + DenyUnapprovedRegions + RequireEncryption

  If the account moves to OU "Sandbox":
    └── OU: "Sandbox"
        ├── SCP: AllowAllServices (no restrictions)
        └── Account: prod-app-001 (moved here)
            → effective SCPs = Root ∩ Sandbox OU
            = DenyLeavingOrg + RequireMFA + AllowAllServices
            → LOST: DenyUnapprovedRegions, RequireEncryption
```

**Key implication:** the effective permissions of an account depend on
its OU placement. Moving an account between OUs changes its SCPs
immediately. Always verify SCPs after any OU move.

**Control Tower Guardrail types:**
- **Preventive Guardrails** — implemented as SCPs. Block disallowed
  actions (e.g., leaving the org, disabling CloudTrail, creating
  resources in unapproved regions).
- **Detective Guardrails** — implemented as Config rules + Security Hub
  controls. Detect non-compliance and alert (e.g., publicly readable
  S3 bucket, unencrypted EBS volume).
- **Proactive Guardrails** — implemented as Config rules. Detect
  resources that would violate policy before they are fully provisioned.

## Expert heuristic: SSO permission set auto-assignment

A baseline model says "assign permission sets manually per account."
The correct heuristic recognizes that Control Tower SSO integration
enables auto-assignment of permission sets to Account Factory-vended
accounts, and that group-based assignment scales better than
individual user assignment.

```text
SSO permission set assignment flow:
  1. Define permission set in Identity Center
     → e.g., "AWSAdministratorAccess" (maps to AdministratorAccess)
     → e.g., "AWSReadOnlyAccess" (maps to ReadOnlyAccess)
     → e.g., "DataEngineerAccess" (custom policy)

  2. Assign permission set to a GROUP
     → group: "PlatformTeam" → permission: "AWSAdministratorAccess"
     → group: "Developers" → permission: "AWSReadOnlyAccess"
     → This is an account-scoped assignment

  3. Account Factory auto-provisions SSO
     → when a new account is vended, Control Tower provisions the
       Identity Center instance to the account
     → permission sets assigned to the OU (via account group) are
       automatically available in the new account

  4. Users access via Identity Center portal
     → user authenticates via SSO
     → sees available accounts and permission sets
     → assumes role in the target account

  Scaling model:
    Instead of: assign permission to user per account (O(users × accounts))
    Use: assign permission to group per OU (O(groups × OUs))
    → add users to groups; groups inherit permission sets across OU accounts
```

**Key implication:** group-based permission set assignment at the OU
level is the scaling pattern. New accounts vended into the OU
automatically inherit the group-to-permission-set bindings, so new
accounts immediately have the correct access without per-account
configuration.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Control Tower landing zone enabled | Account Factory requires an active landing zone | `aws controltower list-landing-zones` |
| Target OU registered with Control Tower | Only registered OUs get Guardrails and baselines | `aws controltower list-controls --control-source-ou <ou-id>` |
| Service Catalog product available | Account vending uses the Account Factory SC product | `aws servicecatalog search-products --filters FullTextSearch=Control` |
| Unique account email | Duplicate emails fail provisioning | Check email pattern against existing accounts |
| Unique account name | Duplicate names cause confusion in billing and console | `aws organizations list-accounts --query 'Accounts[*].Name'` |
| Identity Center enabled | SSO assignment requires Identity Center | `aws sso-admin list-instances` |
| Permission sets defined | Assignment requires existing permission sets | `aws sso-admin list-permission-sets --instance-arn <arn>` |
| Management account access | Account Factory runs from the management account | `aws sts get-caller-identity` (must be management account) |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Account Factory via Service Catalog

Account Factory vends accounts through a Service Catalog product. The
product is auto-created by Control Tower during landing zone setup.

**Provision a new account:**

```bash
# Get the Account Factory product ID
PRODUCT_ID=$(aws servicecatalog search-products \
  --filters FullTextSearch="AWS Control Tower Account Factory Factory" \
  --query 'ProductViewSummaries[0].ProductId' --output text)

# Get the provisioning artifact ID (the "version" of the product)
ARTIFACT_ID=$(aws servicecatalog describe-product \
  --id "$PRODUCT_ID" \
  --query 'ProvisioningArtifacts[0].Id' --output text)

# Provision the account
aws servicecatalog provision-product \
  --product-id "$PRODUCT_ID" \
  --provisioning-artifact-id "$ARTIFACT_ID" \
  --provisioned-product-name "data-platform-prod" \
  --provisioning-parameters '[
    {"Key":"AccountEmail","Value":"aws+data-platform@company.com"},
    {"Key":"AccountName","Value":"data-platform-prod"},
    {"Key":"ManagedOrganizationalUnit","Value":"Custom (DataPlatform)"},
    {"Key":"SSOUserEmail","Value":"platform-lead@company.com"},
    {"Key":"SSOUserFirstName","Value":"Platform"},
    {"Key":"SSOUserLastName","Value":"Team"}
  ]'
```

**Provisioning parameters (required):**

| Parameter | Description | Constraints |
|---|---|---|
| AccountEmail | Root email for the account | Globally unique; not used by any other AWS account |
| AccountName | Display name | Unique within the org |
| ManagedOrganizationalUnit | Target OU (name or SelectWithExist) | Must be a registered OU |
| SSOUserEmail | Initial SSO admin email | Must be unique in Identity Center |
| SSOUserFirstName | Initial SSO admin first name | Non-empty |
| SSOUserLastName | Initial SSO admin last name | Non-empty |

**Provisioning is asynchronous** — typically 5-30 minutes. Poll the
provisioned product status:

```bash
aws servicecatalog describe-provisioned-product \
  --name "data-platform-prod" \
  --query 'ProvisionedProductDetail.Status' --output text
# Wait for status: AVAILABLE
```

## Step 2 — Organizational Unit placement

The target OU determines Guardrail inheritance and baseline StackSet
deployment. The OU must be registered with Control Tower.

**Registered vs. unregistered OUs:**

| OU type | Guardrails | Baseline | SSO auto-provision |
|---|---|---|---|
| Registered with Control Tower | Full SCP inheritance | StackSets auto-deploy | Yes |
| Unregistered (raw org OU) | No Guardrails | No baseline | No |

**List registered OUs:**

```bash
# List all registered OUs in the landing zone
aws controltower list-enabled-controls \
  --control-source-ou <root-ou-id> \
  --query 'EnabledControls[*].ControlIdentifier' --output table
```

**Place the account in the correct OU:**

The OU is specified via the `ManagedOrganizationalUnit` parameter in
the Service Catalog provisioning call. The format is the OU name as
shown in Control Tower (e.g., "Custom (DataPlatform)") or the OU's
SelectWithExist path.

**Moving an account between OUs** (after creation):

```bash
aws organizations move-account \
  --account-id "123456789012" \
  --source-parent-id "ou-aaa-source111" \
  --destination-parent-id "ou-bbb-dest222"
```

**Critical:** moving an account to a different OU immediately changes
its inherited SCPs. Moving from a strict OU to a permissive OU can
expose the account to previously-blocked actions.

## Step 3 — SSO permission set assignment

SSO (Identity Center) provides federated access to accounts via
permission sets. Assignment is a three-way binding: principal (user or
group) + permission set + account.

**Create a permission set:**

```bash
PERMISSION_SET_ARN=$(aws sso-admin create-permission-set \
  --instance-arn "$SSO_INSTANCE_ARN" \
  --name "DataEngineerAccess" \
  --description "Data engineering read-write access" \
  --session-duration "PT8H" \
  --relay-state-type "https://console.aws.amazon.com/" \
  --query 'PermissionSet.PermissionSetArn' --output text)

# Attach a managed policy
aws sso-admin attach-managed-policy-to-permission-set \
  --instance-arn "$SSO_INSTANCE_ARN" \
  --permission-set-arn "$PERMISSION_SET_ARN" \
  --managed-policy-arn "arn:aws:iam::aws:policy/AWSGlueConsoleFullAccess"

# Attach an inline policy (custom)
aws sso-admin put-inline-policy-to-permission-set \
  --instance-arn "$SSO_INSTANCE_ARN" \
  --permission-set-arn "$PERMISSION_SET_ARN" \
  --inline-policy file://data-engineer-inline-policy.json
```

**Assign to a group for an account:**

```bash
aws sso-admin create-account-assignment \
  --instance-arn "$SSO_INSTANCE_ARN" \
  --target-id "123456789012" \
  --target-type "AWS_ACCOUNT" \
  --permission-set-arn "$PERMISSION_SET_ARN" \
  --principal-type "GROUP" \
  --principal-id "group-id-xxx"
```

**Critical:** the assignment does NOT take effect until the permission
set is provisioned to the account. Control Tower auto-provisions SSO
for Account Factory accounts, but manual assignments require a
provisioning step:

```bash
# Provision the permission set to the account
aws sso-admin provision-permission-set \
  --instance-arn "$SSO_INSTANCE_ARN" \
  --permission-set-arn "$PERMISSION_SET_ARN" \
  --target-id "123456789012" \
  --target-type "AWS_ACCOUNT"
```

## Step 4 — Guardrail inheritance (SCP, Detective, Config)

Guardrails are inherited from the OU level. An account in a registered
OU automatically gets:

| Guardrail type | Implementation | Example |
|---|---|---|
| Preventive | SCP in Organizations | Deny leaving org, deny disabling CloudTrail |
| Detective | Config rule + Security Hub control | Detect publicly readable S3 bucket |
| Proactive | Config rule | Detect non-compliant resource creation |

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

## Step 5 — Landing zone baseline conformance

Control Tower deploys a baseline (set of StackSets) to every enrolled
account. The baseline includes:

| Baseline StackSet | Purpose | Target |
|---|---|---|
| AWSControlTowerLogging | CloudTrail trail to logging account | All enrolled accounts |
| AWSControlTowerSecurity | Security Hub, Config rules | All enrolled accounts |
| AWSControlTowerBP-BASELINE-CLOUDTRAIL | CloudTrail baseline | All enrolled accounts |
| AWSControlTowerBP-BASELINE-CONFIG | Config recorder baseline | All enrolled accounts |
| AWSControlTowerBP-BASELINE-CLOUDWATCH | CloudWatch alarms baseline | All enrolled accounts |

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

## Step 6 — Email and account name uniqueness

**Email uniqueness:** the root email for each AWS account must be
globally unique across ALL AWS accounts (including accounts in other
orgs and closed accounts). AWS rejects provisioning with a duplicate
email.

**Recommended email pattern:**

```text
aws+<ou>-<account-name>@<company-domain>

Examples:
  aws+prod-data-platform@company.com
  aws+dev-sandbox-01@company.com
  aws+security-audit@company.com
```

Using the `+` alias pattern (Gmail, Outlook, most email providers)
routes all emails to the same inbox while providing unique addresses
for each account.

**Account name uniqueness:** while not enforced by the API, duplicate
account names cause confusion in billing, the console, and automation.
Always verify:

```bash
aws organizations list-accounts \
  --query 'Accounts[*].Name' --output text | tr '\t' '\n' | \
  grep -q "data-platform-prod" && echo "DUPLICATE" || echo "UNIQUE"
```

## Step 7 — Alternate contacts

Alternate contacts provide operational metadata for billing, security,
and operational notifications. They are set per-account via the Account
Management API.

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

**Critical:** alternate contacts are NOT inherited from the OU or org
level. They must be set per-account. Automate this in the account
customization pipeline (Step 8).

## Step 8 — Account customization (custom product/StackSets)

Beyond the default baseline, accounts can be customized via custom
Service Catalog products that deploy additional CloudFormation
StackSets.

**Custom product pattern:**

```text
Custom account customization flow:
  1. Create a CloudFormation template with account-specific resources
     (VPC, KMS keys, IAM roles, CloudWatch dashboards, etc.)
  2. Publish as a Service Catalog product in the Account Factory portfolio
  3. When vending an account, provision BOTH the standard Account Factory
     product AND the custom product
  4. Control Tower's StackSets deploy the custom resources alongside the
     baseline
```

**Example custom StackSet (deploy VPC in every new account):**

```bash
# Create a custom StackSet
aws cloudformation create-stack-set \
  --stack-set-name "CustomBaseline-VPC" \
  --template-body file://vpc-template.yaml \
  --permission-model SERVICE_MANAGED \
  --capabilities CAPABILITY_NAMED_IAM \
  --auto-deployment 'Enabled=true,RetainStacksOnAccountRemoval=false'
```

**Account Factory customization via CloudFormation StackSets:**

Control Tower supports customized account factory via the
`AWSControlTowerBP-ENABLE-CONFIG-RULES` and custom products in the
Account Factory portfolio. The customization template runs during
account provisioning.

## Step 9 — Account lifecycle (vending, updating, terminating)

### Vending new accounts

Covered in Step 1. The vending process creates the account, places it
in the OU, deploys baselines, and configures SSO.

### Updating account baseline

When the landing zone is updated (new Control Tower version), baseline
StackSets are redeployed to all enrolled accounts. For custom
customizations, update the StackSet:

```bash
aws cloudformation update-stack-set \
  --stack-set-name "CustomBaseline-VPC" \
  --template-body file://vpc-template-v2.yaml \
  --operation-preferences RegionConcurrencyType=PARALLEL
```

### Terminating accounts

Account Factory supports account termination via Service Catalog:

```bash
# Terminate the provisioned product
aws servicecatalog terminate-provisioned-product \
  --provisioned-product-name "data-platform-prod"

# Note: this dis-enrolls the account from Control Tower and removes
# baseline StackSets. The AWS account itself is NOT deleted — it enters
# SUSPENDED state and is permanently closed after 90 days.
```

**Critical:** terminating an Account Factory provisioned product does
NOT delete the AWS account. It only removes Control Tower management
(SCPs remain until the account is moved out of the OU, baselines are
removed). The account transitions to SUSPENDED and is closed after
90 days. To fully remove an account, you must also close it via the
Organizations console/API.

## Step 10 — Compliance status verification

After provisioning, verify the account's compliance status:

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

## Step 11 — Recent features

**Recent AWS features (2023-2026):**

- **Control Tower Account Factory Customization (2023-2024):** Enhanced
  support for custom CloudFormation templates that run during account
  provisioning, enabling account-specific baselines beyond the default
  Control Tower StackSets. Custom products can include VPC setup, KMS
  keys, and IAM roles.

- **Identity Center group-based auto-assignment (2023-2024):** SSO
  permission sets can be auto-assigned to groups at the OU level, so
  new accounts vended into the OU automatically inherit the correct
  access without per-account configuration.

- **Account Factory email validation (2023-2024):** Pre-provisioning
  email validation API that checks email uniqueness before submitting
  the provisioning request, reducing failed account creations.

- **Landing Zone 3.0+ (2024-2025):** Enhanced landing zone with
  improved Guardrail coverage, including new Detective controls for
  generative AI workloads and strengthened encryption requirements.

- **Account termination via API (2024-2025):** Programmatic account
  termination via the Account Factory Service Catalog product,
  enabling automated account lifecycle management without console
  access.

- **Alternate contacts via StackSet (2024-2025):** Alternate contacts
  can now be set via CloudFormation StackSet, simplifying bulk
  deployment across hundreds of accounts.

## NEVER do these things

1. **NEVER create accounts via raw Organizations `CreateAccount` when
   Control Tower is in use.** Organizations-created accounts are NOT
   enrolled in Control Tower. They miss Guardrails, baselines, and SSO.
   Always use the Account Factory Service Catalog product for managed
   accounts.

2. **NEVER place accounts in unregistered OUs.** Only registered OUs
   get Guardrails (SCP, Detective, Config). An account in an
   unregistered OU is a compliance gap. Always verify the OU is
   registered with Control Tower before vending.

3. **NEVER use duplicate root emails.** The root email must be globally
   unique. Duplicate emails cause provisioning failures. Use a
   consistent alias pattern (e.g., `aws+<ou>-<name>@company.com`).

4. **NEVER assume SCPs persist after moving accounts between OUs.**
   SCPs are inherited from the OU. Moving an account to a different OU
   immediately changes its effective SCPs. Always verify SCPs after any
   OU move.

5. **NEVER skip baseline StackSet verification.** Control Tower deploys
   baselines automatically, but StackSets can fail silently. An
   account with a failed StackSet has no CloudTrail, Config, or
   Security Hub — a critical compliance gap. Always verify StackSet
   deployment status.

6. **NEVER assign SSO permission sets without provisioning.** Creating
   a permission set and assigning it to a principal does NOT take
   effect until the permission set is provisioned to the account.
   Always call `provision-permission-set` after assignment.

7. **NEVER forget alternate contacts.** They are not inherited from
   the OU or org level. Without billing/security/operations contacts,
   AWS support and billing notifications go to the root email only.
   Always set all three alternate contacts per account.

8. **NEVER assume Account Factory termination deletes the AWS account.**
   Terminating the Service Catalog product dis-enrolls the account
   from Control Tower but does NOT close the AWS account. The account
   remains in SUSPENDED state for 90 days before permanent closure.
   Close the account separately if immediate removal is needed.

9. **NEVER use individual user SSO assignments at scale.** Assign
   permission sets to GROUPS, not individual users. Group-based
   assignment scales to O(groups x OUs) instead of O(users x accounts).
   Add users to groups; groups inherit permission sets.

10. **NEVER skip landing zone version checks.** Outdated landing zone
    versions silently lack newer Guardrails and features. Always check
    the landing zone version and upgrade before vending accounts that
    require the latest Guardrails.

## Output format

```text
ACCOUNT_FACTORY: <account-name> (<account-id>) in OU <ou-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Account email: <email> — UNIQUE (globally)
  [✓|✗] Account name: <name> — UNIQUE (within org)
  [✓|✗] Target OU: <ou-name> (<ou-id>) — REGISTERED with Control Tower
  [✓|✗] Service Catalog product: <product-id> — AVAILABLE
  [✓|✗] Account provisioned: <account-id> — ACTIVE
  [✓|✗] Guardrails (SCP): <count> preventive controls inherited from OU
  [✓|✗] Guardrails (Detective): Config rules deployed in account
  [✓|✗] Guardrails (Config): baseline StackSets — <all/failed list>
  [✓|✗] Baseline StackSets: AWSControlTowerLogging — DEPLOYED, AWSControlTowerSecurity — DEPLOYED
  [✓|✗] SSO: Identity Center instance <instance-arn>
  [✓|✗] Permission sets: <list> assigned to <group> for this account
  [✓|✗] SSO provisioning: permission set provisioned — SUCCEEDED
  [✓|✗] Alternate contacts: BILLING ✓, SECURITY ✓, OPERATIONS ✓
  [✓|✗] Custom baseline: <stackset-name> — DEPLOYED
  [✓|✗] Compliance status: <compliant | non-compliant (gaps listed)>
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws organizations describe-account --account-id <account-id>
  aws organizations list-policies-for-target --target-id <account-id> --filter SERVICE_CONTROL_POLICY
  aws cloudformation list-stack-instances --stack-set-name AWSControlTowerLogging
  aws sso-admin list-account-assignments --instance-arn <instance-arn> --account-id <account-id>
```

### Worked example — data platform account with SSO and Guardrails

```text
ACCOUNT_FACTORY: data-platform-prod (123456789012) in OU DataPlatform (ou-bbb-ccc)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Account email: aws+prod-data-platform@company.com — UNIQUE
  [✓] Account name: data-platform-prod — UNIQUE
  [✓] Target OU: Custom (DataPlatform) (ou-bbb-ccc) — REGISTERED
  [✓] Service Catalog product: prod-aaa111 — AVAILABLE
  [✓] Account provisioned: 123456789012 — ACTIVE
  [✓] Guardrails (SCP): 8 preventive controls inherited from OU
  [✓] Guardrails (Detective): 12 Config rules deployed
  [✓] Guardrails (Config): baseline StackSets — all DEPLOYED
  [✓] Baseline StackSets: AWSControlTowerLogging — DEPLOYED, AWSControlTowerSecurity — DEPLOYED
  [✓] SSO: Identity Center instance arn:aws:sso:::instance/ssoins-12345
  [✓] Permission sets: DataEngineerAccess assigned to DataPlatformTeam group
  [✓] SSO provisioning: DataEngineerAccess provisioned — SUCCEEDED
  [✓] Alternate contacts: BILLING ✓, SECURITY ✓, OPERATIONS ✓
  [✓] Custom baseline: CustomBaseline-VPC — DEPLOYED
  [✓] Compliance status: compliant
  [✓] Tags: Environment=production, OU=DataPlatform, Owner=PlatformTeam
VERIFICATION_COMMANDS:
  aws organizations describe-account --account-id 123456789012
  aws organizations list-policies-for-target --target-id 123456789012 --filter SERVICE_CONTROL_POLICY
  aws cloudformation list-stack-instances --stack-set-name AWSControlTowerLogging
  aws sso-admin list-account-assignments --instance-arn arn:aws:sso:::instance/ssoins-12345 --account-id 123456789012
```

## Error handling

### Account provisioning stuck in CREATE_IN_PROGRESS
- Account creation takes 5-30 minutes. If it exceeds 30 minutes, check
  the Service Catalog provisioning status for errors. Common causes:
  duplicate email, OU not registered, or IAM permission issues in the
  management account.

### Baseline StackSet deployment failed
- Check the StackSet operation status in the management account. Common
  causes: missing `AWSControlTowerExecutionRole` in the target account,
  conflicting resources (e.g., an existing CloudTrail), or IAM
  permission issues. Re-run the StackSet after fixing the root cause.

### SSO permission set not available in the account
- The permission set was assigned but not provisioned. Run
  `provision-permission-set` to push the permission set to the account.
  Also verify the account is enrolled in the Identity Center.

### Account has no Guardrails despite being in an OU
- The OU is NOT registered with Control Tower. Only registered OUs get
  Guardrails. Register the OU via the Control Tower console or verify
  the OU's registration status. If the account was in the OU before
  registration, it may need to be re-enrolled.

### Alternate contacts not set
- The contacts were not set during provisioning. They are per-account
  and NOT inherited from the OU. Set them manually via
  `put-alternate-contact` or automate via a custom StackSet in the
  account customization pipeline.

## Domain

AWS CloudOps / AWS Control Tower Account Factory Governance & Account
Lifecycle Management.

## AWS documentation

- **Control Tower User Guide** — https://docs.aws.amazon.com/controltower/latest/userguide/
- **Account Factory** — https://docs.aws.amazon.com/controltower/latest/userguide/account-factory.html
- **Guardrails** — https://docs.aws.amazon.com/controltower/latest/userguide/guardrails.html
- **Landing zone** — https://docs.aws.amazon.com/controltower/latest/userguide/landing-zone.html
- **SCP inheritance** — https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps.html
- **Identity Center** — https://docs.aws.amazon.com/singlesignon/latest/userguide/
- **Permission sets** — https://docs.aws.amazon.com/singlesignon/latest/userguide/permissionsetsconcept.html
- **Service Catalog Account Factory** — https://docs.aws.amazon.com/controltower/latest/userguide/account-factory.html
- **Alternate contacts** — https://docs.aws.amazon.com/accounts/latest/reference/manage-acct-update/alternate-contacts.html
- **CloudFormation StackSets** — https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/what-is-cfnstacksets.html
