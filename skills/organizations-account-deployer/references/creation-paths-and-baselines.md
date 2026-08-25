# Creation Paths and Baselines — Organizations Account Deployer

Deep reference on the two account-creation paths (Organizations
`create-account` vs Control Tower Account Factory), baseline components
(SCP, tag policy, CloudTrail org trail, Config aggregator, IAM Identity
Center permission sets, RAM shares), Account Factory custom baselines,
and landing-zone topology. Loaded on demand by the skill — kept out of
the main SKILL.md body so the provisioning procedure stays scannable.

## Organizations create-account vs Control Tower Account Factory

The two paths are not interchangeable. They differ in what they
deliver, the prerequisites, and the retrofit cost.

| Dimension | Organizations `create-account` | Control Tower Account Factory |
|---|---|---|
| Output | Bare account in minutes | Account with landing-zone baseline |
| SCP / tag policy | Manual attach (or inherit from OU) | Inherited from OU + blueprint |
| CloudTrail | Manual per-account or relies on org trail | Org trail wired by landing zone |
| Config | No aggregator | Config aggregator wired by landing zone |
| IAM Identity Center | Manual `create-account-assignment` | Auto-assigned per blueprint |
| VPC | Not created | Created from Account Factory blueprint |
| Audit posture | Bring-your-own | Pre-wired by landing zone |
| Prerequisite | Org in `ALL_FEATURES` mode | Control Tower landing zone active |
| Programmatic | `aws organizations create-account` | `aws controltower create-landing-zone` / Account Factory |
| Best for | Sandbox, ad-hoc, break-glass | Production workloads in a landing zone |
| Retrofit cost | High (manual baseline) | Low (baseline is the default) |

**Decision rule (when in doubt):** pick Account Factory if the
workload is production-bound and you have an active landing zone. Pick
`create-account` for sandbox, break-glass, or one-off accounts where
the baseline overhead is not justified.

## Landing-zone topology

```
Management account (org root)
├── Logging account (delegated CloudTrail administrator)
│   ├── S3 bucket: org-audit-logs-<mgmt-id>
│   ├── CloudTrail org trail
│   └── Config aggregator
├── Audit / Security account (delegated Security Hub, GuardDuty)
├── Network account (Transit Gateway, shared VPCs)
└── Workload OUs
    ├── OU: prod
    │   ├── SCP: DenyUnapprovedRegions
    │   ├── Tag policy: CostCenterRequired
    │   └── Accounts: prod-workload-use1, prod-payments-use1, ...
    └── OU: sandbox
        ├── SCP: DenyProductionServices
        └── Accounts: sandbox-experiment-1, ...
```

**Key invariants:**
- The org trail lives in the management or logging account and is
  created with `--is-organization-trail`.
- SCPs and tag policies are attached at the **OU** level, not the
  account level, so all accounts under the OU inherit.
- The `OrganizationAccountAccessRole` is created in **every** member
  account with the same name, allowing the management account to
  assume it.

## Baseline components (what a baseline should include)

A production account baseline typically wires:

1. **SCP attachment (OU-level):** deny unapproved regions, deny root
   principal actions, require encryption, deny unapproved services.
2. **Tag policy attachment (OU-level):** enforce `CostCenter`,
   `Environment`, `Workload` tag compliance.
3. **CloudTrail org trail:** inherited by all member accounts; logs
   land in the logging account's S3 bucket.
4. **Config aggregator:** in the logging or audit account; aggregates
   Config findings from all member accounts.
5. **Config conformance packs:** operational best practices (CIS AWS
   Foundations, NIST, PCI-DSS).
6. **IAM Identity Center permission sets:** defined once in the
   management account; assigned to groups and accounts.
7. **Alternate contacts:** billing, security, operations (per-account
   via `aws account put-alternate-contact`).
8. **Budgets:** per-account spend alert.
9. **RAM shares:** Transit Gateway, License Manager configurations.
10. **VPC (if Account Factory):** from the Account Factory blueprint.

## Account Factory custom baselines (2024-2026)

Control Tower Account Factory now supports **custom baselines**:
CloudFormation StackSets that deploy automatically when an account is
vended via Account Factory. This extends Account Factory beyond the
default landing zone.

**How custom baselines work:**

1. Define a CloudFormation StackSet template (the custom baseline).
2. Register the StackSet as a Control Tower `EnabledControl` or as
   part of an Account Factory blueprint.
3. When an account is vended via Account Factory, Control Tower:
   - Creates the account.
   - Creates a StackSet instance targeting the new account.
   - The StackSet applies the custom baseline (e.g., additional SCPs,
     Lambda functions, IAM roles, CloudWatch alarms).

**Custom baseline examples:**
- A `SecurityBaseline` StackSet that creates a security-read IAM role
  for the audit account.
- A `NetworkBaseline` StackSet that attaches the new account's VPC to
  the org's Transit Gateway.
- A `ComplianceBaseline` StackSet that enables AWS Config rules for
  the org's compliance framework (HIPAA, PCI-DSS, FedRAMP).

```bash
# Register a custom baseline as an EnabledControl (Control Tower)
aws controltower enable-control \
  --control-identifier arn:aws:controltower:us-east-1::control/CustomBaseline \
  --target-identifier arn:aws:organizations::111122223333:ou/o-abc/ou-prod-xyz \
  --parameters file://baseline-parameters.json
```

## Terraform vending module (canonical pattern)

For landing zones managed as code, the canonical pattern is a
Terraform module that encapsulates:

1. The account (`aws_organizations_account`).
2. OU placement (`aws_organizations_organizational_unit`).
3. SCP attachment (`aws_organizations_policy_attachment`).
4. Tag policy attachment.
5. IAM Identity Center permission set assignment
   (`aws_ssoadmin_account_assignment`).
6. Config aggregator (created once in the logging account).
7. CloudTrail org trail (created once in the logging account).

```hcl
# Module: modules/account-vending

resource "aws_organizations_account" "this" {
  name      = var.account_name
  email     = var.root_email
  role_name = "OrganizationAccountAccessRole"
  parent_id = var.parent_ou_id

  tags = merge(
    { "Environment" = var.environment },
    { "Workload"    = var.workload },
    var.additional_tags
  )
}

resource "aws_organizations_policy_attachment" "scp" {
  policy_id = var.scp_policy_id
  target_id = aws_organizations_account.this.id
}

resource "aws_ssoadmin_account_assignment" "default" {
  count              = length(var.permission_set_arns)
  instance_arn       = var.sso_instance_arn
  permission_set_arn = var.permission_set_arns[count.index]
  principal_id       = var.admin_group_id
  principal_type     = "GROUP"
  target_id          = aws_organizations_account.this.id
  target_type        = "AWS_ACCOUNT"
}

output "account_id" {
  value = aws_organizations_account.this.id
}

output "role_arn" {
  value = "arn:aws:iam::${aws_organizations_account.this.id}:role/OrganizationAccountAccessRole"
}
```

## Common pitfalls in baseline design

- **Per-account SCP attachment instead of OU-level:** creates drift.
  Prefer OU-level attachment; account-level for one-off exceptions.
- **Missing CloudTrail org trail before vending:** the first hours of
  the new account's activity are unaudited.
- **Forgetting the `FullAWSAccess` SCP:** if you remove it from the
  root without a replacement, every account in the org (including
  newly vended ones) loses access to all AWS services.
- **Mismatched `OrganizationAccountAccessRole` names:** breaks
  cross-account automation. Use one role name across the org.
- **No Identity Center permission set assigned:** the new account is
  silent and unreachable by humans; only the management account's
  assume-role path works.
- **Custom baseline StackSet failures:** if a StackSet fails on a
  newly vended account, the account is half-provisioned. Monitor
  StackSet operation status (`aws cloudformation describe-stack-set-operation`).

## AWS documentation references

- AWS Organizations — create accounts — https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_accounts_create.html
- Control Tower Account Factory — https://docs.aws.amazon.com/controltower/latest/userguide/account-factory.html
- Control Tower custom baselines — https://docs.aws.amazon.com/controltower/latest/userguide/customizing-control-tower.html
- IAM Identity Center permission sets — https://docs.aws.amazon.com/singlesignon/latest/userguide/permissionsets.html
- CloudTrail organization trail — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/creating-trail-organization.html
- AWS Config aggregator — https://docs.aws.amazon.com/config/latest/developerguide/aggregate-data.html
- Terraform aws_organizations_account — https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/organizations_account
- AWS RAM — https://docs.aws.amazon.com/ram/latest/userguide/what-is.html
## Step 1 — feature comparison (create-account vs Account Factory)

**Feature comparison:**

| Feature | Organizations `create-account` | Control Tower Account Factory |
|---|---|---|
| Time to ready | Minutes | Minutes (with baseline) |
| SCP / tag policy | Manual attach | Inherited from OU + blueprint |
| CloudTrail org trail | Inherits if org trail exists | Wired by landing zone |
| IAM Identity Center | Manual account assignment | Auto-assigned per blueprint |
| VPC | Not created | Created from blueprint |
| Config aggregator | Manual | Wired by landing zone |
| Cost | Free | Free (Control Tower) |
| Programmatic vending | `aws organizations create-account` | `aws controltower create-landing-zone` / Account Factory |
