# Advanced Patterns — Organizations Account Deployer

Deep-dive material moved out of the SKILL.md body so the provisioning
procedure stays scannable. Loaded on demand by the skill.

## What this skill does

Provisions AWS member accounts with production-grade defaults across
creation path (Organizations `create-account` vs Control Tower Account
Factory), account identity (unique root email, account name, IAM role
name), cross-account admin role (`OrganizationAccountAccessRole`),
billing attachment (consolidated billing under the payer), guardrails
(SCP and tag policy attachment at the right scope), audit propagation
(CloudTrail organization trail), SSO (IAM Identity Center permission
sets), and latest automation (Terraform `aws_organizations_account`,
Account Factory custom baselines). The output is a READY_TO_DEPLOY
checklist with verification commands.

## Mindset

**One-line takeaway:** an AWS account is a security, billing, and
audit boundary — every default decided at creation time (root email,
IAM role name, SCP, tag policy, org trail, SSO) is expensive to
retrofit later. The procedure treats each as a one-way door and
forces an explicit decision before the `create-account` / Account
Factory call.

Three misconceptions dominate account-provisioning misdesign:

- **"Account creation is just `create-account` with a name."** This
  ignores the load-bearing inputs. The **root email** is a unique,
  permanent identity for the new account's root user — reusing or
  losing it locks the account out of password reset. The
  **IAM role name** (default `OrganizationAccountAccessRole`) is the
  cross-account admin entry point the management account assumes;
  mismatching the role name across the org breaks cross-account
  automation silently. **Billing** is consolidated to the payer
  automatically, but Cost Explorer and budgets must be wired per
  account.

- **"Control Tower Account Factory and Organizations create-account are
  interchangeable."** They are not. `create-account` vends a bare
  account in minutes. Account Factory vends an account **with a
  baseline** — guardrails (SCPs), logging (CloudTrail org trail +
  Config aggregation), SSO (IAM Identity Center auto-assignment), and
  VPC — applied at creation. Retrofitting a baseline onto a bare
  account is manual, error-prone work; for landing zones, default to
  Account Factory.

- **"Org trail and SSO propagate automatically to new accounts."** An
  organization trail is inherited by new member accounts **only if it
  is created as an organization trail** (CloudTrail
  `--is-organization-trail`). IAM Identity Center permission sets are
  inherited **only via account assignments** — a new account is silent
  and inaccessible until at least one permission set is assigned.

## Reasoning framework (why provisioning order matters)

Account provisioning has **dependency and inheritance semantics** that
make the order non-trivial:

1. **Root email BEFORE create-account** — the email is the new
   account's permanent root identity. Reusing or losing it locks the
   account out of password reset. Use a distribution list or a
   programmatic alias (`aws+workload@...`).
2. **Management account organization BEFORE member accounts** — the
   organization must exist in `ALL_FEATURES` mode before
   `create-account`. SCP and tag policy types must be enabled on the
   root before any SCP / tag policy can attach.
3. **OU placement BEFORE SCP/tag policy** — SCPs and tag policies are
   inherited by OUs. Placing the account in the right OU first lets
   guardrails apply automatically; moving an account across OUs later
   can silently change its effective policy.
4. **Org trail BEFORE the first workload API** — a new account is
   unaudited until the org trail is established. For landing zones,
   create the org trail before vending any member account.
5. **IAM Identity Center permission set AFTER account creation** — a
   new account ID is required to assign a permission set. The
   `OrganizationAccountAccessRole` is the bootstrap fallback.
6. **Account Factory baseline BEFORE custom IaC** — if you use
   Account Factory, the blueprint's baseline must be defined first.
   Overlaying custom IaC before the baseline lands causes drift.

## Configuration dependency graph (novel heuristic)

Many account-level configurations are **inherited, immutable, or
silently downgraded**. The procedure forces an explicit decision on
each before vending the account.

| Configuration | Immutability / silent failure |
|---|---|
| Root email | **IMMUTABLE** at creation — losing it locks root password reset |
| IAM role name (`OrganizationAccountAccessRole`) | **IMMUTABLE** at creation — cannot be renamed; mismatched names break cross-account automation |
| Organization feature set | Must be `ALL_FEATURES` before SCP/tag policy attach |
| SCP / tag policy type on root | Must be `ENABLED` on the root before any SCP/tag policy can attach |
| OU placement | SCP/tag policy inherited from OU — move account BEFORE attaching account-level policies |
| CloudTrail org trail | New account inherits **only if** trail is created as an organization trail |
| Consolidated billing | Auto-applied for member accounts — but Cost Explorer opt-in and cost-allocation tags are per-account |
| IAM Identity Center permission set | Account assignment required — a new account is silent until assignment |
| Account Factory baseline | Baselines applied at vending — retrofitting onto `create-account`-vended accounts is manual |
| Alternate contacts | Per-account — must be set explicitly (billing, security, operations) |

**Cross-dependency gotchas:**
- Removing the default `FullAWSAccess` SCP from the root without
  replacing it locks every account in the org (including newly vended
  ones).
- `OrganizationAccountAccessRole` trust policy is scoped to the
  management account only. Cross-account access from a different
  account requires an additional role.
- An organization trail is inherited by **new** member accounts only.
  Member accounts that existed before the org trail was created must
  be added explicitly.

## Expert heuristic: sizing the creation path

The most-missed decision is **which creation path to use**. The two
paths — Organizations `create-account` and Control Tower Account
Factory — are not interchangeable.

| Signal | Organizations `create-account` | Control Tower Account Factory |
|---|---|---|
| Need | Bare account, fast (minutes) | Account with baseline (guardrails, logging, SSO, VPC) |
| Audit posture | Bring-your-own CloudTrail | CloudTrail org trail + Config aggregator pre-wired |
| Access posture | `OrganizationAccountAccessRole` only | IAM Identity Center SSO auto-assigned |
| Networking | No VPC by default | VPC from Account Factory blueprint |
| Best for | Sandbox, ad-hoc, break-glass | Production workloads in a landing zone |
| Blast radius of mistake | Per-account (manual remediation) | Blueprint-wide (one fix propagates) |

**Rule of thumb:** if the account will host production workloads,
default to Account Factory. If you cannot (no Control Tower landing
zone), vend with `create-account` and apply the baseline via IaC
immediately (within the same pipeline run), not as a follow-up.

## Step 10 — Latest features (2024-2026)


- **Control Tower Account Factory custom baselines (2024-2025):**
  CloudFormation StackSets deployed at account vending extend Account
  Factory beyond the default landing zone. Define baselines as code;
  Account Factory applies them automatically. See
  references/creation-paths-and-baselines.md.
- **AWS Organizations + Terraform (2024-2025):** The
  `aws_organizations_account`, `aws_organizations_policy`,
  `aws_ssoadmin_account_assignment`, and
  `aws_cloudtrail_organization_trail` resources are the canonical
  vending path. Use a Terraform module to encapsulate the baseline.
- **AWS RAM organization-wide sharing (2024-2025):** RAM shares can
  target the entire org (eliminating per-account shares for Transit
  Gateway, License Manager, and Resource Groups).
- **Account Factory + Config Conformance Packs (2024-2026):**
  Conformance packs deployed as part of the Account Factory baseline
  provide org-wide security posture management.
- **Alternate contacts API (2023-2024):** The `aws account` namespace
  (`put-alternate-contact`, `get-alternate-contact`) enables
  programmatic setting of billing, security, and operations contacts
  per account — previously console-only.

## Recent AWS features (2024-2026)

- **Control Tower Account Factory custom baselines (2024-2025):**
  CloudFormation StackSets deployed at account vending extend Account
  Factory beyond the default landing zone baseline.
- **AWS Organizations with Terraform (2024-2025):** The
  `aws_organizations_account`, `aws_organizations_policy`,
  `aws_ssoadmin_account_assignment`, and
  `aws_cloudtrail_organization_trail` resources are the canonical
  vending path for landing zones.
- **IAM Identity Center (successor to AWS SSO) (2023-2025):**
  Permission sets, account assignments, and OU-level account
  assignments via `aws_ssoadmin_account_assignment`.
- **CloudTrail org trail + delegated administrator (2023-2024):**
  Delegate CloudTrail administration to a logging account. Org trails
  inherit to new accounts automatically.
- **AWS RAM organization-wide sharing (2024-2025):** RAM shares can
  target the entire org, eliminating per-account shares.
- **Account alternate contacts API (2023-2024):** The `aws account`
  namespace enables programmatic setting of billing, security, and
  operations contacts per account — previously console-only.

