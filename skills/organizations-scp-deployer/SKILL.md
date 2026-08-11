---
name: organizations-scp-deployer
description: >-
  Provisions AWS Organizations Service Control Policies (SCPs) with safe
  defaults: SCP statement structure (Effect, Action, Resource, Condition),
  SCP evaluation model (intersection with IAM — both IAM and every
  applicable SCP in the hierarchy MUST allow the action), OU inheritance
  (child OU intersected with parent OU), root/OU/account attachment targets,
  common guardrail policies (deny regions, deny unapproved services, require
  encryption, deny root access, deny leave-organization), strategy patterns
  (guardrail: deny dangerous actions; throttle: cap service usage; delegate:
  allow only within boundaries), and latest features (aws:CalledVia
  condition for chained service calls, Organizations condition keys,
  CloudFormation StackSets for SCP deployment). Emits a deployment plan
  with a READY_TO_DEPLOY checklist. Use when provisioning SCPs, designing
  a multi-layer guardrail strategy, delegating service usage within
  boundaries, blocking regions for compliance, or hardening the
  organization root.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline architecture planning. Live
  deployment uses aws organizations create-policy, attach-policy,
  list-policies, describe-policy, list-policies-for-target,
  list-roots, list-organizational-units-for-parent, list-accounts-for-parent,
  enable-policy-type, and aws cloudformation create-stack-set
  (AWS CLI v2, SSO or key-based credentials).
keywords:
  - AWS Organizations
  - SCP
  - Service Control Policy
  - organization guardrail
  - OU inheritance
  - policy hierarchy
  - deny regions
  - deny services
  - require encryption
  - deny root access
  - FullAWSAccess
  - aws:CalledVia
  - aws:CalledViaFirst
  - aws:CalledViaLast
  - policy type
  - tag policy
  - backup policy
  - deployment strategy
  - CloudFormation StackSets
  - Control Tower
  - landing zone
  - preventive control
  - allowlist SCP
  - denylist SCP
tags: [aws-organizations, governance, deploy, scp, ou-inheritance, guardrail, preventive-control, policy-hierarchy, called-via, landing-zone]
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
  when_to_use: >-
    Provisioning a new Service Control Policy, designing a multi-layer
    guardrail strategy (guardrail / throttle / delegate), delegating
    service usage within account boundaries, blocking regions for
    data-residency compliance, denying root principal actions, attaching
    SCPs at root/OU/account scope, enabling the SCP feature on the
    organization root, or integrating SCPs with CloudFormation StackSets
    or Control Tower preventive controls.
  activation_triggers:
    - "create an SCP"
    - "Service Control Policy"
    - "deny region SCP"
    - "block AWS regions"
    - "deny services SCP"
    - "require encryption SCP"
    - "deny root access SCP"
    - "SCP guardrail"
    - "OU inheritance"
    - "attach SCP to OU"
    - "attach SCP to account"
    - "delegate within SCP"
    - "aws:CalledVia"
    - "Control Tower guardrail"
    - "CloudFormation StackSets SCP"
    - "enable policy type"
    - "landing zone preventive controls"
  invocation_schema: >-
    Input shape (one of): (a) a deployment specification including the
    policy goal (deny regions / deny services / require encryption /
    deny root / custom), target scope (root, OU, account), statement
    contents, and strategy pattern (guardrail, throttle, delegate);
    (b) a partial spec for interactive refinement (e.g., "block all
    regions except us-east-1 and eu-west-1"); (c) an existing policy ID
    for architecture review against the well-architected checklist.
    Output shape: { POLICY_SPEC, VERDICT, ARCHITECTURE, CHECKLIST[],
    FINDINGS[], DEPLOY_COMMANDS } where VERDICT ∈ { READY_TO_DEPLOY,
    PREREQUISITES_MISSING, ERROR }.
---

# Organizations SCP Deployer

## Mindset

**One-line takeaway:** an SCP is NOT an IAM policy — it is a **guard
rail** that defines the maximum permissions an account can ever have,
regardless of what IAM policies grant. IAM can expand access within the
SCP boundary but can never exceed it. The intersection model
(IAM ∩ every SCP in the hierarchy) is the single most-misunderstood
aspect of Organizations, and getting it wrong either over-locks
production (FullAWSAccess removed from root) or under-protects
compliance-bound accounts (SCP applied to wrong OU).

Three facts make SCP deployment different from "just another JSON
policy":

- **SCPs filter — they never grant.** An SCP with `Effect: Allow` for
  `s3:*` does NOT let a principal call S3. It only permits IAM in that
  account to grant `s3:*`. The principal still needs an IAM identity
  policy allowing the action. Removing the default
  `FullAWSAccess` from the root without replacing it with explicit
  allows locks every account in the org — IAM grants become inert.

- **SCP evaluation is an intersection across the entire hierarchy.**
  For any API call, every SCP attached at root → parent OU → child OU
  → account is evaluated. The action is permitted at the Organizations
  layer ONLY if at least one SCP at EVERY level permits it. The most
  restrictive OU wins. A common foot-gun: denying `s3:*` on the root
  cannot be re-allowed at the OU level — Deny statements always win
  and there is no "allow override."

- **`aws:CalledVia` is the condition key for chained service calls.**
  Without it, an SCP that allows a service can be abused via another
  service acting on the principal's behalf (e.g., allow CloudFormation
  to create anything → CloudFormation can create IAM roles). Using
  `aws:CalledVia`/`aws:CalledViaFirst`/`aws:CalledViaLast` lets you
  scope which chained calls are in-policy. This is the canonical 2024+
  technique for service-hop containment.

## Quick navigation

| Section | Purpose |
|---|---|
| Pre-flight gate | Validate org, policy type enabled, target exists |
| Quick reference — deployment checklist | 14 dimensions at a glance |
| Strategy patterns | Guardrail vs throttle vs delegate |
| Step-by-step process | Author → attach → verify → document |
| Common guardrail SCP library | Drop-in templates |
| STRICT output contract | Required VERDICT block schema |
| NEVER (top 5) | Highest-blast-radius mistakes |
| Expert heuristic | Field craft for ambiguous cases |
| Edge-case handling | Lockouts, escapes, OU moves |
| Remediation | Recover from a self-lockout |

## Quick reference — deployment checklist

| # | Dimension | Requirement |
|---|---|---|
| 1 | Policy type | `SERVICE_CONTROL_POLICY` enabled on the org root |
| 2 | Strategy pattern | Pick one: guardrail / throttle / delegate |
| 3 | Statement shape | `Effect`, `Action`, `Resource`, optional `Condition` |
| 4 | Intersection awareness | Every parent in the path is intersected |
| 5 | Default `FullAWSAccess` | Preserved at root UNLESS using allowlist strategy |
| 6 | Target scope | root, OU ID, or account ID |
| 7 | Region deny | Allowlist approved regions (requires `aws:RequestedRegion`) |
| 8 | Service deny | Explicit `Deny` on unapproved services (e.g., `iam:DeleteRole`) |
| 9 | Encryption require | Deny CreateBucket / PutObject without SSE-KMS via condition keys |
| 10 | Root deny | Deny `*:*` when `aws:PrincipalType == "root"` |
| 11 | `aws:CalledVia` | Scope chained service calls where applicable |
| 12 | Tag policy alignment | No conflict with `TagPolicy` type |
| 13 | StackSets deploy | IaC path via CloudFormation StackSets for audit trail |
| 14 | Post-attach verify | `list-policies-for-target` confirms attachment |

## Pre-flight: deployment specification gate

Run before producing the deployment plan. Several requirements **block
deployment** — proceeding with an invalid spec can lock every account
in the organization.

**Live-account pre-flight checks (skip if doing offline architecture
plan):**
1. Verify the org is in `ALL_FEATURES` mode (or that
   `SERVICE_CONTROL_POLICY` is the enabled feature):
   `aws organizations describe-organization --query 'Organization.FeatureSet'`
2. Verify policy type is enabled on the root:
   `aws organizations list-roots --query 'Roots[0].PolicyTypes[].Type'`
   — must include `SERVICE_CONTROL_POLICY` with status `ENABLED`.
3. Verify the caller IAM role holds
   `organizations:CreatePolicy`, `organizations:AttachPolicy`, and
   `organizations:EnablePolicyType`.
4. Verify the target (root, OU, account) exists in the organization.
5. If replacing an existing SCP, capture the current policy JSON for
   audit (no inline rollback path — the previous content must be
   retained externally).
6. If applying to an OU with production accounts, run a dry-run
   evaluation via IAM Access Analyzer policy validation
   (`accessanalyzer:ValidatePolicy`).

| Attribute | Value | Effect on plan |
|---|---|---|
| Strategy | guardrail | Default `FullAWSAccess` preserved; add `Deny` statements. |
| Strategy | throttle | Default preserved; add `Deny` with `aws:RequestedRegion` or quota condition. |
| Strategy | delegate | Default `FullAWSAccess` REMOVED from root; replace with explicit `Allow` of approved services. HIGH RISK. |
| Target type | root | Affects every account. Deny statements propagate to all child OUs. |
| Target type | OU | Affects that OU + descendants. Child OU cannot override a parent Deny. |
| Target type | account | Affects one account. Useful for sandbox carve-outs. |
| Existing lockouts | accounts with broken IAM | Deny-on-root propagates instantly; verify no production impact. |

**If the deployment spec is incomplete** (missing strategy, missing
target, conflicting statements), output:

```text
POLICY_SPEC: <name-or-unknown>
VERDICT: PREREQUISITES_MISSING
REASON: Deployment specification is missing required fields (<list>).
Cannot produce a deployment plan without <field> — the resulting SCP
could lock accounts or fail to enforce the intended guardrail.
REQUIRED:
  - strategy (guardrail | throttle | delegate)
  - target (root ID, OU ID, or account ID)
  - policy_goal (deny_regions | deny_services | require_encryption |
                  deny_root | custom)
  - effect_scope (root principal only | all principals | service role)
```

## Strategy patterns — pick one before authoring

### Pattern A — Guardrail (default, low risk)

**Goal:** deny dangerous actions while leaving the rest of the service
catalog open. The default `FullAWSAccess` managed policy STAYS attached
to the root. You add explicit `Deny` statements for the actions you
want to block.

**When to use:** most production orgs. Easiest to reason about, lowest
risk of accidental lockout.

**Example shape:** deny `iam:CreateUser`, `iam:DeleteRolePolicy`,
`organizations:LeaveOrganization`, etc. Deny statements are additive
and do not affect the default allow.

### Pattern B — Throttle (medium risk)

**Goal:** limit service usage by region, instance family, or quota.
Still keeps `FullAWSAccess` attached; adds `Deny` statements with
condition keys.

**When to use:** cost-control programs, data-residency compliance,
approved-region enforcement.

**Example shape:** `Deny *:*` with `Condition: StringNotEquals:
aws:RequestedRegion: ["us-east-1", "eu-west-1"]`.

### Pattern C — Delegate / Allowlist (HIGH RISK)

**Goal:** explicitly list the services the accounts may use; everything
else is implicitly denied. The default `FullAWSAccess` managed policy
is REMOVED from the root (or replaced with a narrower allow).

**When to use:** regulated environments (FedRAMP, PCI-scoped
accounts), tightly-controlled landing zones, ISV multi-tenant
deployments.

**Foot-gun:** removing `FullAWSAccess` without a comprehensive
allowlist locks every account in the org. The org management account
itself is NOT affected by SCPs (SCPs do not apply to the management
account), but every member account is.

**Example shape:** an `Allow` SCP listing approved service prefixes,
attached at the root, replacing `FullAWSAccess`.

## Process — Author, attach, verify (in order)

### Step 0: Expert heuristic — field craft for ambiguous cases

- **If you don't know whether to allowlist or denylist → denylist
  (guardrail).** Allowlist requires you to enumerate every service the
  business uses, including services that don't exist yet. Denylist is
  additive and degrades gracefully as AWS adds services.

- **If a service team complains their workflow broke after an SCP
  attach → look for a chained service call.** The most common case is
  CloudFormation / CDK / Service Catalog invoking IAM on the user's
  behalf. The SCP allows the user's principal but not the chained
  service. Solution: add `aws:CalledVia` to scope the chained calls,
  NOT broaden the principal.

- **If a member account admin says "I have AdministratorAccess but
  can't do X" → check the SCP hierarchy.** `AdministratorAccess` is an
  IAM policy — it expands access within the SCP boundary but cannot
  exceed it. Every SCP in the root → parent OU → account path is
  intersected. The Deny is somewhere in that chain.

- **If you're asked to apply a SCP to "all production accounts" → use
  the OU, not individual accounts.** Account-level SCPs do not
  propagate; OU-level SCPs do. Tag-based SCP targeting is NOT
  supported (only `tag-policy` type uses tags). Group accounts by OU.

- **If the management account needs an SCP applied → it can't.** SCPs
  do not apply to the management account, only to member accounts.
  Harden the management account separately via IAM, MFA, and
  scoped-access roles. Do not assume the org root SCP protects it.

### Step 1: Enable the policy type (if not already enabled)

```bash
aws organizations list-roots \
  --query 'Roots[0].PolicyTypes[?Type==`SERVICE_CONTROL_POLICY`].Status'
```

If the result is empty or `PENDING_ENABLE`, enable it:

```bash
ROOT_ID=$(aws organizations list-roots --query 'Roots[0].Id' --output text)
aws organizations enable-policy-type \
  --root-id "$ROOT_ID" \
  --policy-type SERVICE_CONTROL_POLICY
```

Once enabled, the AWS-managed `FullAWSAccess` policy is automatically
attached to the root. Do NOT detach it unless you are deliberately
using the delegate (allowlist) strategy.

### Step 2: Author the SCP JSON

SCP statements use the same JSON shape as IAM, but the `Principal`
element is **ignored** — SCPs apply to all principals in the target.
Omit `Principal` entirely; if you include it, AWS silently ignores it.

**Guardrail template — deny root principal actions:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyRootUserActions",
      "Effect": "Deny",
      "Action": "*",
      "Resource": "*",
      "Condition": {
        "StringLike": {
          "aws:PrincipalType": "root"
        }
      }
    }
  ]
}
```

**Guardrail template — deny unapproved regions:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyUnapprovedRegions",
      "Effect": "Deny",
      "Action": "*",
      "Resource": "*",
      "Condition": {
        "StringNotEquals": {
          "aws:RequestedRegion": ["us-east-1", "eu-west-1"]
        },
        "ArnNotLike": {
          "aws:CalledVia": ["cloudfront.amazonaws.com"]
        }
      }
    }
  ]
}
```
CloudFront and other global services must be exempted or they break —
they make calls that look region-less.

**Guardrail template — require SSE-KMS on S3 PutObject:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyUnEncryptedObjectUploads",
      "Effect": "Deny",
      "Action": "s3:PutObject",
      "Resource": "*",
      "Condition": {
        "StringNotEquals": {
          "s3:x-amz-server-side-encryption": "aws:kms"
        }
      }
    }
  ]
}
```

**Delegate template — allowlist of approved services:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowApprovedServicesOnly",
      "Effect": "Allow",
      "Action": [
        "ec2:*",
        "s3:*",
        "rds:*",
        "iam:*",
        "logs:*",
        "cloudwatch:*",
        "kms:*"
      ],
      "Resource": "*"
    }
  ]
}
```
Use only when `FullAWSAccess` has been removed from the root.

### Step 3: `aws:CalledVia` for chained service calls

When service A calls service B on the principal's behalf, the
`aws:CalledVia` key contains the chain of services. Use it to scope
which chained calls are permitted.

```json
{
  "Sid": "AllowCloudFormationViaIAM",
  "Effect": "Allow",
  "Action": ["iam:CreateRole", "iam:PassRole"],
  "Resource": "*",
  "Condition": {
    "StringEquals": {
      "aws:CalledVia": ["cloudformation.amazonaws.com"]
    }
  }
}
```

Use `aws:CalledViaFirst` to match the first service in the chain and
`aws:CalledViaLast` for the last. Without this condition, an SCP
allowing `iam:CreateRole` is over-broad — any chained service can
abuse it.

### Step 4: Create the policy

```bash
aws organizations create-policy \
  --content file://scp.json \
  --description "Deny root user actions across all member accounts" \
  --name deny-root-actions \
  --type SERVICE_CONTROL_POLICY
```

The returned `PolicySummary.Id` is the policy ID for attachment.

### Step 5: Attach to target (root, OU, or account)

```bash
ROOT_ID=$(aws organizations list-roots --query 'Roots[0].Id' --output text)

# Attach at the root (applies to every member account)
aws organizations attach-policy \
  --policy-id <POLICY_ID> \
  --target-id "$ROOT_ID"

# Or attach to a specific OU
aws organizations attach-policy \
  --policy-id <POLICY_ID> \
  --target-id ou-abc1-exampleOU

# Or attach to a specific account
aws organizations attach-policy \
  --policy-id <POLICY_ID> \
  --target-id 111111111111
```

### Step 6: Verify the attachment

```bash
aws organizations list-policies-for-target \
  --target-id "$ROOT_ID" \
  --filter SERVICE_CONTROL_POLICY \
  --query 'Policies[].{Name:Name,Id:Id,AwsManaged:AwsManaged}'
```

The policy MUST appear in the list. The change is global and effective
within seconds — there is no propagation delay.

### Step 7: Document the rollback path

SCPs have no built-in rollback. Capture:
- The previous policy JSON (if updating).
- The detach command (`aws organizations detach-policy`) for the
  specific target.
- A tested break-glass procedure (the management account is exempt
  from SCPs, so management account credentials are the universal
  escape hatch).

## Common guardrail SCP library

| Library entry | Strategy | Statement shape |
|---|---|---|
| Deny unapproved regions | guardrail | `Deny *:*` with `aws:RequestedRegion` not in allowlist |
| Deny unapproved services | guardrail | `Deny <service>:*` for each unapproved service |
| Deny root user actions | guardrail | `Deny *` when `aws:PrincipalType == root` |
| Deny leave organization | guardrail | `Deny organizations:LeaveOrganization` |
| Require SSE-KMS on S3 | guardrail | `Deny s3:PutObject` when `s3:x-amz-server-side-encryption != aws:kms` |
| Require tags on resources | guardrail (tag policy preferred) | `Deny <create-action>` when `aws:RequestTag/<key>` absent |
| Prevent security-group ingress 0.0.0.0/0 | guardrail | `Deny ec2:AuthorizeSecurityGroupIngress` when `aws:SourceIp` condition met |
| Cap EC2 instance family | throttle | `Deny ec2:RunInstances` when `ec2:InstanceType` not in approved set |
| Allowlist approved services | delegate | `Allow <service>:*` for each approved service; remove `FullAWSAccess` |

## Output format — STRICT output contract

The output MUST follow this exact schema. Every field is required; do
not omit fields or add undocumented ones.

```text
POLICY_SPEC: <name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
ARCHITECTURE:
  Strategy: <guardrail | throttle | delegate>
  Target: <root-id | ou-id | account-id>
  Target scope: <root | OU | account>
  FullAWSAccess: <preserved | removed>
  Policy type enabled: <yes | no>
  Statements: <count>
  Condition keys used: <aws:RequestedRegion | aws:CalledVia | aws:PrincipalType | none>
CHECKLIST:
  [x] Policy type SERVICE_CONTROL_POLICY enabled on root
  [x] Strategy pattern documented
  [x] Intersection with parent SCPs evaluated
  [x] FullAWSAccess preserved (guardrail) OR explicitly removed (delegate)
  [x] Principal element omitted (ignored by SCP anyway)
  [x] Condition keys valid for the action(s) used
  [x] Rollback path documented
  [x] Dry-run validation passed (accessanalyzer:ValidatePolicy)
FINDINGS:
  - [INFO] Policy affects N accounts across M OUs
  - [WARN] Removing FullAWSAccess without comprehensive allowlist locks all member accounts
DEPLOY_COMMANDS:
  <ordered list of aws organizations create-policy / attach-policy commands>
```

### Worked example — deny root user actions at root scope

```text
POLICY_SPEC: deny-root-user-actions
VERDICT: READY_TO_DEPLOY
ARCHITECTURE:
  Strategy: guardrail
  Target: r-abc1 (root)
  Target scope: root
  FullAWSAccess: preserved
  Policy type enabled: yes
  Statements: 1
  Condition keys used: aws:PrincipalType
CHECKLIST:
  [x] Policy type SERVICE_CONTROL_POLICY enabled on root
  [x] Strategy pattern documented (guardrail — additive Deny)
  [x] Intersection with parent SCPs evaluated (root has no parent)
  [x] FullAWSAccess preserved
  [x] Principal element omitted
  [x] Condition key aws:PrincipalType valid for the action set
  [x] Rollback path documented (detach-policy)
  [x] Dry-run validation passed
FINDINGS:
  - [INFO] Policy affects 47 member accounts across 6 OUs
  - [WARN] Root credentials will be unable to perform any action in
    member accounts — verify break-glass roles exist before attach
DEPLOY_COMMANDS:
  1. aws organizations create-policy --content file://deny-root.json
     --name deny-root-user-actions --type SERVICE_CONTROL_POLICY
  2. aws organizations attach-policy --policy-id <POLICY_ID>
     --target-id r-abc1
  3. aws organizations list-policies-for-target --target-id r-abc1
     --filter SERVICE_CONTROL_POLICY (verify)
```

## Verification commands (run after deployment)

```bash
# Verify policy is attached to target
aws organizations list-policies-for-target \
  --target-id <TARGET_ID> \
  --filter SERVICE_CONTROL_POLICY

# Verify policy contents
aws organizations describe-policy \
  --policy-id <POLICY_ID> \
  --query 'Policy.Content'

# Verify effective SCPs at an account (use IAM Access Analyzer)
aws accessanalyzer list-policy-findings \
  --analyzer-arn <ARN>  # if configured for SCP evaluation

# Validate policy JSON syntax (pre-deploy)
aws accessanalyzer validate-policy \
  --policy-document file://scp.json \
  --policy-type RESOURCE_POLICY
```

## Anti-Patterns — NEVER (top 5)

- **NEVER remove the default `FullAWSAccess` from the org root without
  a tested allowlist SCP attached.** Removing it instantly makes every
  IAM policy in every member account inert. The management account is
  exempt and is the only escape hatch — but operators routinely forget
  this and lock out the entire org. Always have a tested replacement
  allowlist SCP attached first.

- **NEVER assume an `Allow` SCP grants access.** SCPs only filter;
  they never grant. A principal still needs an IAM identity policy
  allowing the action. An `Allow` SCP at the account level with no
  matching IAM policy = no access. This is the single most
  misunderstood aspect of SCPs.

- **NEVER apply a Deny at the root OU and expect a child OU to override
  it.** SCP evaluation is an intersection across the entire hierarchy.
  A Deny at the root propagates to every descendant and CANNOT be
  re-allowed lower in the tree. If you need carve-outs, apply the Deny
  to a more specific OU or use condition keys (`aws:RequestedRegion`,
  resource ARNs) rather than blanket Deny statements.

- **NEVER include a `Principal` element in an SCP and expect it to
  scope enforcement.** SCPs apply to ALL principals in the target
  (root, OU, or account). The `Principal` element is silently ignored.
  To target specific principals, use condition keys
  (`aws:PrincipalType`, `aws:PrincipalArn`, `aws:PrincipalTag/<key>`)
  inside the statement.

- **NEVER assume the management account is protected by SCPs.** SCPs
  do NOT apply to the management account — only to member accounts.
  Harden the management account separately (IAM, MFA, scoped roles,
  CloudTrail). A common compliance finding is "we applied SCPs at the
  root, so the management account is covered" — it is not.

## Additional NEVER

- NEVER attach an SCP to an account without first listing its current
  effective policies (`list-policies-for-target`) — the new SCP
  intersects with whatever is already there.

- NEVER use `Action: "*"` with `Effect: Allow` in an SCP — it is
  equivalent to `FullAWSAccess` and defeats the purpose. Use explicit
  service prefixes.

- NEVER deploy an SCP without a documented rollback path. SCPs have no
  built-in version history; the previous content must be retained
  externally.

- NEVER mix SCP strategy patterns on the same target. A guardrail
  (additive Deny) and a delegate (allowlist) on the same OU produce
  unpredictable intersections.

- NEVER assume SCPs apply across organizational boundaries. Trusted
  access, cross-account roles, and resource-based policies are NOT
  filtered by the calling account's SCPs in all cases — verify with
  IAM Access Analyzer for the specific resource.

- NEVER skip `EnablePolicyType` on a new organization root. The
  `SERVICE_CONTROL_POLICY` type is NOT enabled by default in
  `CONSOLIDATED_BILLING` mode orgs.

## Pre-flight safety checks

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`create-policy`, `attach-policy`, `detach-policy`,
  `enable-policy-type`), the deployer MUST emit:
  `CONFIRM: About to attach SCP <name> (<policy-id>) to target
  <target-id> (<scope>). This affects <N> accounts across <M> OUs.
  Rollback path: <detach command>. Proceed? (yes/no)`

- **Root attach blast radius.** Attaching to the root affects every
  member account. Always prefer OU-level attachment unless the policy
  is truly org-wide.

- **Dry-run validation.** Run `aws accessanalyzer validate-policy` on
  the SCP JSON before `create-policy`. Catches syntax errors and
  unsupported condition keys.

- **`FullAWSAccess` check.** `aws organizations list-policies-for-target
  --target-id <root-id> --filter SERVICE_CONTROL_POLICY` MUST list
  `FullAWSAccess` UNLESS the delegate strategy is in use.

- **OU tree snapshot.** Capture the OU tree before any root-level
  change: `aws organizations list-organizational-units-for-parent
  --parent-id <root-id>`. Provides the rollback reference.

## Edge-case handling

- **Member account locked after SCP attach.** Use management account
  credentials (SCPs do not apply to the management account) to
  `detach-policy` from the target. The break-glass is always the
  management account.

- **`aws:RequestedRegion` breaks global services.** CloudFront,
  Route 53, IAM, and WAF (CLOUDFRONT scope) make region-less API
  calls. A region-deny SCP must exempt them via `ArnNotLike` on
  `aws:CalledVia` or service-specific conditions, or these services
  break in every member account.

- **OU move changes effective SCPs.** When an account moves between
  OUs (`organizations:MoveAccount`), the effective SCP set changes.
  Pre-validate the destination OU's SCP intersection before moving
  production accounts.

- **Tag policy vs SCP.** Tag policies (`TAG_POLICY` type) enforce
  tagging on supported resources. They are NOT SCPs and cannot deny
  API calls. Use SCPs with `aws:RequestTag/<key>` conditions for
  hard enforcement.

- **Trusted-access carve-outs.** Some AWS services (e.g., AWS Config,
  CloudTrail) require specific permissions in member accounts. An SCP
  that denies those services can break organization-wide compliance
  services. Test carve-outs in a non-production OU first.

## Remediation guidance

**Ordering principle:** restore access first (detach or condition
narrowing), then re-architect the SCP strategy, then re-attach with
the corrected statement set.

### For PREREQUISITES_MISSING — policy type not enabled

1. `aws organizations enable-policy-type --root-id <root-id>
   --policy-type SERVICE_CONTROL_POLICY`
2. Verify `FullAWSAccess` is auto-attached to the root.
3. Proceed with policy creation.

### For PREREQUISITES_MISSING — OU does not exist

1. `aws organizations create-organizational-unit --parent-id <root-id>
   --name <new-ou-name>`
2. Move accounts into the new OU with `organizations:MoveAccount`.
3. Attach the SCP to the new OU.

### For accidental org-wide lockout

1. Authenticate as the management account (SCPs do not apply).
2. `aws organizations list-policies-for-target --target-id <root-id>
   --filter SERVICE_CONTROL_POLICY`
3. `aws organizations detach-policy --policy-id <offending-policy-id>
   --target-id <root-id>`
4. Re-author the SCP with narrower scope (OU-level instead of root,
   or with condition keys instead of blanket Deny).

## Recent AWS features (2024-2026)

- **`aws:CalledVia` chain conditions (2023-2024):** scope which chained
  services are permitted to act on the principal's behalf. First/Last
  variants (`aws:CalledViaFirst`, `aws:CalledViaLast`) refine chain
  position matching.

- **Backup policy type (2024):** `BACKUP_POLICY` is now a first-class
  Organizations policy type — apply backup plans org-wide without
  SCP-based enforcement.

- **Tag policy improvements (2024):** `TAG_POLICY` supports
  enforced tagging on additional resource types. Use for tag
  governance; pair with SCPs for hard enforcement.

- **CloudFormation StackSets with Organizations (2024-2025):**
  deploy SCPs via IaC with `DeploymentTargets` specifying OU IDs.
  StackSets auto-reconciles as accounts are added to the OU.

- **IAM Access Analyzer SCP evaluation (2024-2025):** external-access
  findings now include the effective SCP set for cross-account
  resource access. Use to validate that an SCP does not accidentally
  block a legitimate cross-account workflow.

- **Control Tower preventive controls (2025):** Control Tower now
  publishes its preventive controls as composable SCP building blocks.
  Use as reference templates for custom SCPs outside Control Tower.

- **Organizations Accounts API (2025):** enhanced `ListAccounts` with
  OU membership inline — simplifies blast-radius calculations for
  SCP attach planning.

## AWS documentation

- **AWS Organizations User Guide** — https://docs.aws.amazon.com/organizations/latest/userguide/orgs_introduction.html
- **SCP reference** — https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps.html
- **SCP strategies** — https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps_strategies.html
- **SCP examples** — https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps_examples.html
- **aws:CalledVia** — https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_condition-keys.html#condition-keys-calledvia
- **aws:RequestedRegion** — https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_condition-keys.html#condition-keys-requestedregion
- **CloudFormation StackSets + Organizations** — https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stacksets-orgs-enable-trusted-access.html
- **AWS Control Tower preventive controls** — https://docs.aws.amazon.com/controltower/latest/userguide/preventive-controls.html
- **IAM Access Analyzer policy validation** — https://docs.aws.amazon.com/IAM/latest/UserGuide/access-analyzer-policy-validation.html
