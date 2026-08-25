# Advanced Patterns — AWS Control Tower Account Factory Deployer

Load-on-demand deep dives moved verbatim from SKILL.md: mindset misconceptions, dependency graph, and recent features.

## Mindset — three provisioning-time misconceptions

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

## Recent AWS features (2023-2026)

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
