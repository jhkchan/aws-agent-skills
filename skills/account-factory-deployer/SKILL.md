---
name: account-factory-deployer
description: 'Deploys AWS Control Tower Account Factory accounts with production defaults: account creation via Service Catalog product (provision-product), Organizational Unit placement, SSO assignment via permission sets, Guardrail inheritance (SCP, Detective, Config), landing zone baseline conformance, email and account name uniqueness, alternate contacts, compliance status verification, account customization via custom product (CloudFormation StackSets), vending new accounts, terminating accounts, and updating account baselines. Emits a READY_TO_DEPLOY checklist with verification commands. Use when creating AWS accounts via Control Tower, vending accounts to teams, assigning SSO permission sets, verifying Guardrail. Triggers: create aws account control tower, account factory provision, vending new account, control tower account enrollment, sso permission set assignment, guardrail scp inheritance, account factory service catalog, control tower landing zone baseline, terminate aws account, custom account baseline.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with servicecatalog, controltower, organizations, and sso-admin access. Works with Terraform aws_controltower_account / aws_organizations_ account / aws_ssoadmin_permission_set resources and CloudFormation AWS::ServiceCatalog::CloudFormationProvisionedProduct templates.'
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
  tags: aws, control-tower, account-factory, cloudops, deploy, governance, provisioning, landing-zone, scp, guardrails, sso, organizations
  dependencies: aws-orchestrator
  keywords: aws, control tower, account factory, service catalog, cloudops, deploy, provisioning, landing zone, scp, guardrails, sso, permission set, organizations, stacksets, baseline, account vending, compliance, alternate contacts
  when_to_use: Invoke when the user wants to create AWS accounts via Control Tower Account Factory, vend accounts to teams, place accounts in Organizational Units, assign SSO permission sets, verify Guardrail (SCP/Detective/Config) inheritance, customize account baselines via CloudFormation StackSets, update account baselines, or terminate accounts. Do NOT invoke for AWS Organizations account creation outside Control Tower (use organizations-account-deployer), Control Tower landing zone setup/upgrade (use controltower-control- auditor), or SCP authoring (use organizations-scp-deployer).
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
| references/advanced-patterns.md | Dependency graph + recent features |
| references/error-handling.md | Provisioning failure remedies |
| references/diagnostic-commands.md | Verification CLI detail |

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

Three misconceptions in full (raw Organizations ≠ Account Factory; Guardrails apply only to registered OUs; SSO assignment is a three-way binding): [Advanced patterns](references/advanced-patterns.md).

## Configuration dependency graph (novel heuristic)

Account Factory configurations are NOT independent. The landing zone
must exist before OUs can be registered. OUs must be registered before
accounts can be enrolled. The Service Catalog product must be available
before provisioning. SSO permission sets must exist before assignment.
Use this graph to sequence provisioning.

Full dependency table (landing zone → registered OU → SC product → account → SSO → guardrails → baseline → custom product → alternate contacts) plus cross-dependency gotchas: [Advanced patterns](references/advanced-patterns.md).

## Expert heuristic: landing zone baseline propagation

Baseline propagation walkthrough (StackSet fan-out via AWSControlTowerExecutionRole, per-account baseline resources, incomplete-baseline failure mode): [Guardrails and baseline](references/guardrails-and-baseline.md).

## Expert heuristic: SCP inheritance from parent OU

SCP hierarchy walkthrough (effective-SCP intersection, OU-move consequences) and the preventive/detective/proactive Guardrail types: [Guardrails and baseline](references/guardrails-and-baseline.md).

## Expert heuristic: SSO permission set auto-assignment

Group-based auto-assignment flow and the O(groups × OUs) scaling model: [SSO and lifecycle](references/sso-and-lifecycle.md).

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

Create/attach/assign/provision CLI sequence and the provisioning-is-separate-from-assignment rule: [SSO and lifecycle](references/sso-and-lifecycle.md).

## Step 4 — Guardrail inheritance (SCP, Detective, Config)

Guardrails are inherited from the OU level. An account in a registered
OU automatically gets:

| Guardrail type | Implementation | Example |
|---|---|---|
| Preventive | SCP in Organizations | Deny leaving org, deny disabling CloudTrail |
| Detective | Config rule + Security Hub control | Detect publicly readable S3 bucket |
| Proactive | Config rule | Detect non-compliant resource creation |

SCP and Config-rule verification CLI: [Diagnostic commands](references/diagnostic-commands.md).

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

StackSet instance-status check and failure triage: [Diagnostic commands](references/diagnostic-commands.md).

## Step 6 — Email and account name uniqueness

**Email uniqueness:** the root email for each AWS account must be
globally unique across ALL AWS accounts (including accounts in other
orgs and closed accounts). AWS rejects provisioning with a duplicate
email.

Email alias pattern, examples, and the uniqueness-check CLI: [SSO and lifecycle](references/sso-and-lifecycle.md).

## Step 7 — Alternate contacts

Alternate contacts provide operational metadata for billing, security,
and operational notifications. They are set per-account via the Account
Management API.

put-alternate-contact CLI for BILLING, SECURITY, and OPERATIONS contacts: [Diagnostic commands](references/diagnostic-commands.md).

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

Custom StackSet create CLI and the customization-template flow: [Guardrails and baseline](references/guardrails-and-baseline.md).

## Step 9 — Account lifecycle (vending, updating, terminating)

Baseline update, terminate-provisioned-product, and the SUSPENDED-then-closed-after-90-days lifecycle: [SSO and lifecycle](references/sso-and-lifecycle.md).

## Step 10 — Compliance status verification

After provisioning, verify the account's compliance status:

OU placement, SCP, Config, Security Hub, and SSO verification CLI: [Diagnostic commands](references/diagnostic-commands.md).

## Step 11 — Recent features

2023-2026 features — Account Factory Customization, group-based auto-assignment, email validation API, Landing Zone 3.0+, API termination, StackSet alternate contacts: [Advanced patterns](references/advanced-patterns.md).

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

Stuck provisioning, failed baseline StackSet, unprovisioned permission set, missing Guardrails, unset alternate contacts: [Error handling](references/error-handling.md).

## References (load on demand)

- [Guardrails and baseline](references/guardrails-and-baseline.md) — guardrail types, OU registration, baseline StackSets, SCP-inheritance and propagation heuristics, custom StackSets
- [SSO and lifecycle](references/sso-and-lifecycle.md) — permission sets, group assignment, vending/updating/terminating, email management
- [Advanced patterns](references/advanced-patterns.md) — provisioning misconceptions, configuration dependency graph, recent features
- [Error handling](references/error-handling.md) — provisioning, StackSet, SSO, and Guardrail failure remedies
- [Diagnostic commands](references/diagnostic-commands.md) — guardrail, baseline, alternate-contact, and compliance verification CLI

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
