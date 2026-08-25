---
name: organizations-policy-deployer
description: 'Deploys AWS Organizations policy artifacts with production defaults: Service Control Policy (SCP) creation (JSON policy via create-policy), attachment to root/OU/account (attach-policy), SCP inheritance (intersection of parent and child SCPs along the OU tree), SCP effect (Allow list strategy requiring FullAWSAccess + Deny list strategy), the FullAWSAccess managed policy (required on every entity by default), SCP evaluation (explicit Deny wins; intersection applies at every level), tag policy integration, backup policy integration, AI services opt-out policy, multi-OU deployment, policy simulation (simulate-custom-policy), SCP exceptions (break-glass accounts), CloudTrail logging for SCP-denied actions, and Organizations delegated administrator. Emits a READY_TO_DEPLOY checklist with verification. Triggers: create scp, attach scp, organizations policy, scp inheritance, allow list scp, deny list scp, fullawsaccess managed policy, scp simulation, break-glass account, organizations delegated administrator.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with organizations:CreatePolicy, organizations:AttachPolicy, organizations:DescribePolicy, organizations:ListPoliciesForTarget. Works with Terraform aws_organizations_policy / aws_organizations_policy_attachment resources and CloudFormation AWS::Organizations::Policy templates.'
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
  tags: aws, organizations, scp, service-control-policy, cloudops, deploy, governance, allow-list, deny-list, fullawsaccess, inheritance, permission-boundary
  dependencies: aws-orchestrator
  keywords: aws, organizations, scp, service control policy, cloudops, deploy, governance, allow list, deny list, fullawsaccess, inheritance, permission boundary, tag policy, backup policy, ai services opt-out, break-glass, delegated administrator
  when_to_use: Invoke when the user wants to create or attach an AWS Organizations SCP, design Allow list vs Deny list strategy, configure FullAWSAccess managed policy, reason about SCP inheritance across the OU tree, integrate tag policy / backup policy / AI services opt-out policy, simulate policy effect, exclude break-glass accounts, audit SCP-denied API calls, or delegate Organizations administration. Do NOT invoke for IAM permission boundaries within a single account, Resource Access Manager (RAM) sharing, or AWS Control Tower guardrails.
---

# Organizations Policy Deployer

An AWS CloudOps agent skill that deploys AWS Organizations policy
artifacts — Service Control Policies (SCPs), tag policies, backup
policies, and AI services opt-out policies — with correct
defaults. The skill walks the operator through the SCP-as-
permission-boundary model, Allow list vs Deny list strategy,
FullAWSAccess managed policy behavior, inheritance as
intersection, explicit-Deny-wins evaluation, policy simulation,
break-glass exceptions, and delegated administrator setup;
captures policy intent and target hierarchy; explains why each
default matters; and emits a READY_TO_DEPLOY checklist with copy-
pasteable verification commands.

## Activation keywords

create SCP, attach SCP, organizations policy, SCP inheritance,
Allow list SCP, Deny list SCP, FullAWSAccess managed policy, SCP
simulation, break-glass account, organizations delegated
administrator.

## STRICT output contract

When this skill is invoked with an Organizations-policy-deployment
request (create or attach an SCP, design Allow list / Deny list
strategy, configure FullAWSAccess, simulate policy effect, set up
break-glass exceptions, or a partial configuration), the agent
MUST respond with the READY_TO_DEPLOY checklist defined in the
"Output format" section using the literal all-caps labels
`ORGANIZATIONS_POLICY:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with
prose, headings, or disclaimers — emit the block as the first
lines of the response. This contract is what assertion-based
evals and downstream governance pipelines rely on; deviating
from the literal labels breaks automation silently.

If any prerequisite is missing, the verdict is
`PREREQUISITES_MISSING` with a specific gap citation in the
checklist (marked `[✗]`), and `READY_TO_DEPLOY` MUST NOT also
appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before deployment |
| Step 1 — SCP fundamentals (permission boundary, not IAM) | Core model |
| Step 2 — SCP creation (JSON policy) | Authoring step |
| Step 3 — Attachment to root / OU / account | Targeting step |
| Step 4 — SCP inheritance (intersection of parent and child) | Hierarchy |
| Step 5 — Allow list vs Deny list strategy | Strategy decision |
| Step 6 — FullAWSAccess managed policy | Required default |
| Step 7 — SCP evaluation (explicit Deny wins) | Evaluation order |
| Step 8 — Tag policy integration | Tag governance |
| Step 9 — Backup policy integration | Backup governance |
| Step 10 — AI services opt-out policy | Data-usage governance |
| Step 11 — Multi-OU deployment & policy simulation | Rollout & pre-flight |
| Step 12 — SCP exceptions (break-glass accounts) | Break-glass design |
| Step 13 — CloudTrail for SCP-denied actions | Auditing |
| Step 14 — Organizations delegated administrator | Delegation |
| Step 15 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/scp-inheritance-and-strategy.md | Inheritance + Allow/Deny detail |
| references/policy-types-and-delegation.md | Tag/Backup/AI/opt-out + delegation detail |

## Mindset

**One-line takeaway:** An SCP is a permission boundary — it can
only RESTRICT what IAM allows; it can never GRANT. Every account
in an organization gets `FullAWSAccess` attached by default, and
removing it without an explicit Allow-list replacement locks the
account out. SCP inheritance is an INTERSECTION: the effective
SCP at any account is the intersection of all SCPs attached to
the root, every parent OU, and the account itself. The most
restrictive SCP always wins; an explicit Deny anywhere in the
hierarchy overrides every Allow.

Four misconceptions dominate SCP misdesign at deployment time:

- **"An SCP grants permissions."** It does NOT. An SCP is a
  permission boundary that filters what IAM can do. An IAM
  principal can call an API only if BOTH the IAM policy ALLOWS it
  AND no SCP in the hierarchy DENIES it.

- **"Removing FullAWSAccess is enough to lock down an account."**
  Removing `FullAWSAccess` WITHOUT attaching a replacement
  Allow-list SCP leaves the account in a deny-by-default state
  where member-account IAM principals cannot call ANY AWS API —
  including break-glass. Always attach an Allow-list SCP first.

- **"SCP inheritance unions — the broadest SCP wins."** It does
  NOT. Inheritance is an INTERSECTION. If the root SCP allows
  `ec2:*` and a child OU SCP restricts to `ec2:Describe*`, the
  child OU wins — only `ec2:Describe*` survives.

- **"SCPs are IAM policies."** They are NOT IAM. SCPs live in
  Organizations, apply to the whole account (including root), and
  CANNOT grant anything. A `Resource: "*"` Allow in an SCP means
  "passes the SCP filter"; it does NOT mean the principal can
  call the API. (See Step 1 for the comparison table.)

## Configuration dependency graph (novel heuristic)

Organizations policy deployment is NOT a single attach call. The
policy must be created before it can be attached;
`FullAWSAccess` must remain attached (or be replaced by an
Allow-list SCP) or the account locks out; tag and backup policies
are separate policy types with their own enablement; AI services
opt-out is organization-wide and one-shot.

| Configuration | Hard dependencies (API error without) | Silent failure | Enables downstream |
|---|---|---|---|
| SCP creation (create-policy) | "All features" org; organizations:CreatePolicy | SCP created ENABLED but inert until attached | policy available to attach |
| SCP attachment (attach-policy) | target exists; policy ENABLED | root attachment affects EVERY account (incl. break-glass) | policy takes effect |
| FullAWSAccess | AWS-managed, attached by default | detaching WITHOUT a replacement Allow-list locks the account out | baseline Allow |
| Allow-list strategy SCP | child SCP listing ONLY permitted services | if FullAWSAccess remains attached, Allow-list is redundant | least-privilege boundary |
| Deny-list strategy SCP | child SCP with explicit Denies | explicit Deny wins regardless of other Allows | guardrail |
| Tag policy (TAG_POLICIES) | `enable-policy-type --policy-type TAG_POLICIES` | non-blocking by default; add `enforced_for` to make it blocking | tag standardization |
| Backup policy (BACKUP_POLICY) | `enable-policy-type --policy-type BACKUP_POLICIES` | applies to supported resource types only; tag-based selection | org-level backup plan |
| AI services opt-out (AISERVICES_OPT_OUT_POLICY) | org "All features" | ALL-OR-NOTHING per service across ALL accounts — no per-account opt-in | data-usage governance |
| Delegated administrator | account is a member account | delegated admin gets read/list only — CANNOT create/attach SCPs | cross-account read administration |

**The FullAWSAccess-removal row is the one a baseline model
misses.** An Allow-list SCP has zero effect while
`FullAWSAccess` is still attached at the same entity, because
the intersection still permits everything `FullAWSAccess`
permits. The procedure below forces an explicit decision on
whether to keep or remove `FullAWSAccess` at each entity.

## Expert heuristic: SCP is a filter, not a grant

A baseline model says "attach an SCP to allow these services."
The correct heuristic recognizes that an SCP can only FILTER.

```text
For an API call to succeed at a member account, ALL must hold:
  1. SOME SCP in the hierarchy ALLOWS the action (or no SCP at all)
  2. NO SCP in the hierarchy has an explicit Deny for the action
  3. An IAM policy (identity-based or resource-based) ALLOWS it
  4. No IAM permission boundary DENIES it

An SCP Allow alone NEVER makes an API call succeed.
An SCP Deny alone ALWAYS makes the API call fail.
```

**Key implication:** SCP design has two jobs — (a) define the
maximum blast radius (Allow list) and (b) carve out hard
guardrails (Deny list). Everything else is IAM.

## Expert heuristic: inheritance is intersection, not union

```text
Hierarchy:
  Root  ── SCP_R (Allow: ec2:*, s3:*; Deny: iam:DeleteRole)
   │
   └── OU_Prod ── SCP_P (Allow: ec2:*, s3:GetObject)
         │
         └── Account 111122223311 ── SCP_A (Deny: ec2:TerminateInstances)

Effective SCP at Account 111122223311:
  ALLOWED = intersection of Allow lists along the chain
          = s3:GetObject (the most restrictive s3 Allow)
  DENIED  = union of all explicit Denies
          = iam:DeleteRole ∪ ec2:TerminateInstances

Net: account can call s3:GetObject (if IAM also permits);
     CANNOT call iam:DeleteRole or ec2:TerminateInstances ever;
     CANNOT call s3:PutObject (not in SCP_P's Allow set).
```

**Key implication:** to allow `s3:PutObject` at this account,
the Allow must be present in EVERY SCP in the chain. The most-
restrictive SCP anywhere in the chain becomes the ceiling.

## Expert heuristic: Allow list vs Deny list strategy

```text
DENY-LIST (blocklist)                      ALLOW-LIST (allowlist)
─────────────────────────────              ─────────────────────────────
Keep FullAWSAccess attached                REMOVE FullAWSAccess
Attach explicit Deny SCPs                  Attach Allow-list of ONLY permitted services

Default: everything ALLOWED                Default: everything DENIED
Posture: "block known bad"                 Posture: "permit known good"
Use case: established org                  Use case: regulated org, new accounts
Risk: new service auto-allowed (drift)     Risk: new service auto-denied (friction)

NEVER mix at the same entity: keep FullAWSAccess AND attach an Allow-list
SCP — the Allow-list is silently redundant because the intersection still
permits everything FullAWSAccess permits.
```

**Key implication:** an Allow-list strategy is a two-step commit
— attach the Allow-list SCP first, then detach
`FullAWSAccess`. Reversing the order locks the account out.

## Prerequisites (verify before deployment)

Before emitting deployment commands, verify these prerequisites.
If any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Organization "All features" | SCPs require "All features" | `describe-organization --query 'Organization.FeatureSet'` returns `ALL` |
| Caller in management account | Only management account can create/attach SCPs | `sts get-caller-identity` == `describe-organization.MasterAccountId` |
| SCP policy type enabled | Required to create SCPs | `list-roots --query 'Roots[0].PolicyTypes[?Type==`SERVICE_CONTROL_POLICY`].Status'` returns `ENABLED` |
| Target root/OU/account exists | Attachment target must exist | `list-roots` / `list-organizational-units-for-parent` / `describe-account` |
| FullAWSAccess status known (Allow-list) | Detach AFTER Allow-list attached | `list-policies-for-target --target-id <id> --filter SERVICE_CONTROL_POLICY` shows `p-FullAWSAccess` |
| Break-glass path documented (root Deny) | Root Deny hits every member account | Confirm break-glass OU OR Condition exemption in the SCP JSON |
| JSON policy validated | Catches over-/under-permissive statements | `aws iam simulate-principal-policy ...` |
| CloudTrail org trail active (recommended) | Otherwise SCP-denials not centrally logged | `aws cloudtrail describe-trails` shows an Org trail |

If any prerequisite is missing, output
`VERDICT: PREREQUISITES_MISSING` and cite the specific gap.

## Step 1 — SCP fundamentals (permission boundary, not IAM)

An SCP is a JSON policy attached to the organization root, an OU,
or a member account. It is evaluated by AWS BEFORE the member
account's IAM policies. The SCP can only filter; it cannot grant.

| Property | SCP | IAM identity-based policy |
|---|---|---|
| Lives in | Organizations | IAM |
| Scope | Entire account (every principal including root) | Single principal (role/user/group) |
| Can grant permissions | NO — filter only | YES |
| Can deny permissions | YES — explicit Deny wins always | YES |
| Affects management account | NO (management account exempt) | YES |
| Resource element | Must be `*` (SCPs ignore Resource) | Honored per-statement |
| Condition element | Honored | Honored |

**Critical:** SCPs ignore the `Resource` element — every
statement applies to all resources in the account. Use
`Condition` for resource-scoped restrictions inside an SCP.

## Step 2 — SCP creation (JSON policy)

```bash
# Deny-list SCP: block LeaveOrganization and CloudTrail tampering,
# with a break-glass Condition exemption.
POLICY_DOC=$(cat <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyLeaveOrg",
      "Effect": "Deny",
      "Action": "organizations:LeaveOrganization",
      "Resource": "*",
      "Condition": { "StringNotEquals": { "aws:PrincipalAccount": ["111122223311"] } }
    },
    {
      "Sid": "DenyDisableCloudTrail",
      "Effect": "Deny",
      "Action": ["cloudtrail:DeleteTrail", "cloudtrail:StopLogging", "cloudtrail:PutEventSelectors"],
      "Resource": "*"
    }
  ]
}
EOF
)

POLICY_ID=$(aws organizations create-policy \
  --content "$POLICY_DOC" \
  --description "Root guardrails: block LeaveOrganization and CloudTrail tampering" \
  --name "root-guardrails" --type SERVICE_CONTROL_POLICY \
  --query 'Policy.PolicySummary.Id' --output text)
```

The created SCP starts in `ENABLED` state but does NOTHING until
attached. An unattached ENABLED SCP is inert.

## Step 3 — Attachment to root / OU / account

```bash
# Root (affects EVERY member account)
aws organizations attach-policy --policy-id "$POLICY_ID" --target-id r-xxxx

# OU (affects accounts under that OU and child OUs)
aws organizations attach-policy --policy-id "$POLICY_ID" --target-id ou-xxxx-yyyy

# Single account
aws organizations attach-policy --policy-id "$POLICY_ID" --target-id 111122223311
```

**Hard limit:** 5 SCPs (soft-quota, request increase) attached
per entity (root, OU, or account) — `FullAWSAccess` counts
toward the limit.

## Step 4 — SCP inheritance (intersection of parent and child)

Inheritance is intersection. The effective SCP at an account is
the set of actions allowed by EVERY SCP attached to the root,
every parent OU in the chain, and the account itself.

```text
Root [SCP_R1, SCP_R2]
 └ OU_A [SCP_A1]
    └ OU_A1 [SCP_A1_1]
       └ Account 1111 [SCP_ACCT_1]

Effective SCP at Account 1111 =
  intersection of: SCP_R1, SCP_R2, SCP_A1, SCP_A1_1, SCP_ACCT_1
  plus union of:    all explicit Deny statements across the chain
```

**Action allowed** requires an Allow in EVERY SCP in the chain
(or absence of any SCP at a level, which means "Allow *").
**Action denied** if ANY SCP carries an explicit Deny.

## Step 5 — Allow list vs Deny list strategy

| Decision factor | Deny-list | Allow-list |
|---|---|---|
| Default posture | Allow (block known bad) | Deny (permit known good) |
| `FullAWSAccess` | Keep attached | Detach (AFTER Allow-list attached) |
| Drift risk | New services auto-allowed | New services auto-denied |
| Onboarding friction | Low | High (each service needs Allow) |
| Best for | Established orgs | Regulated industries, compliance |

**Allow-list example (effective ONLY if FullAWSAccess is
detached from the same entity):**

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "AllowApprovedServices",
    "Effect": "Allow",
    "Action": ["ec2:*", "s3:*", "rds:*", "iam:*", "logs:Describe*"],
    "Resource": "*"
  }]
}
```

## Step 6 — FullAWSAccess managed policy

`FullAWSAccess` (`p-FullAWSAccess`) is the AWS-managed SCP that
permits every action. It is attached to root, every OU, and
every account at organization creation.

| Action | Effect |
|---|---|
| Keep `FullAWSAccess` attached | Entity behaves as if no SCP (default Allow) |
| Detach `FullAWSAccess` WITHOUT replacement | Account locks out of every API (deny-by-default) — DO NOT |
| Detach `FullAWSAccess` AFTER attaching Allow-list SCP | Allow-list becomes the new ceiling |

```bash
# Correct sequence for Allow-list strategy at an OU
aws organizations attach-policy --policy-id p-ALLOWLIST --target-id ou-xxxx-yyyy
aws organizations detach-policy --policy-id p-FullAWSAccess --target-id ou-xxxx-yyyy

# Verify FullAWSAccess is gone
aws organizations list-policies-for-target \
  --target-id ou-xxxx-yyyy --filter SERVICE_CONTROL_POLICY \
  --query 'Policies[?Name==`FullAWSAccess`]'   # should be empty
```

## Step 7 — SCP evaluation (explicit Deny wins)

```text
1. Gather every SCP attached along the hierarchy to the account.
2. If ANY SCP carries an explicit "Deny" for the action+condition,
   the call is DENIED — regardless of every other Allow.
3. Otherwise, EVERY SCP along the chain must "Allow" the action
   (intersection) for the call to PASS the SCP filter.
4. If the call passes the SCP filter, IAM is then evaluated.
5. The call succeeds only if IAM ALLOWS and no boundary DENIES.
```

**Hard rule:** an explicit Deny in any SCP along the chain is
final. It cannot be overridden by an Allow in another SCP, an
IAM Allow, or a resource-based policy.

## Step 8 — Tag policy integration

Tag policies (`TAG_POLICIES`) standardize tag keys, values, and
capitalization across the org. Enable separately from SCPs:

```bash
aws organizations enable-policy-type --root-id r-xxxx --policy-type TAG_POLICIES
aws organizations create-policy --type TAG_POLICIES --name "mandatory-tag-policy" \
  --description "Enforce Environment and Owner tags" --content "$TAG_POLICY_DOC"
```

```json
{
  "tags": {
    "Environment": {
      "TagKey": { "Value": "Environment" },
      "EnforcedFor": ["ec2:instance", "s3:bucket"],
      "AllowedValues": ["dev", "staging", "production"]
    },
    "Owner": { "TagKey": { "Value": "Owner", "CaseSensitive": true } }
  }
}
```

Without `enforced_for`, tag policies are audit-only (non-
blocking). Add resource types to `enforced_for` to make non-
compliant `CreateTags` / `UntagResources` calls fail.

## Step 9 — Backup policy integration

Backup policies (`BACKUP_POLICY`) deploy AWS Backup plans across
the org based on resource tags. Enable, create, attach:

```bash
aws organizations enable-policy-type --root-id r-xxxx --policy-type BACKUP_POLICIES
aws organizations create-policy --type BACKUP_POLICY --name "org-backup-plan" \
  --content "$BACKUP_POLICY_DOC"
```

A backup policy applies the SAME plan to every matching resource
in every account under the target root/OU. Tag-based selection
(`StringEquals` on `aws:ResourceTag/...`) is the canonical
selector. See `references/policy-types-and-delegation.md` for a
complete backup plan JSON.

## Step 10 — AI services opt-out policy

AI services opt-out policies (`AISERVICES_OPT_OUT_POLICY`)
prevent AWS from using account content to train or improve AI
services. It is organization-wide and all-or-nothing per
service.

```bash
aws organizations create-policy --type AISERVICES_OPT_OUT_POLICY \
  --name "opt-out-all-ai-services" \
  --description "Opt out of all AI services content use" \
  --content '{"services":{"default":{"opt_out_policy":{"@odata.type":"#AWS.OptOutPolicy#ServicesOptOutPolicyDefault","opt_out_enabled_at_level":"account"}}}}'

aws organizations attach-policy --policy-id <policy-id> --target-id r-xxxx
```

The `default` key applies the opt-out to every AI service,
present and future. There is no per-account opt-in override.

## Step 11 — Multi-OU deployment & policy simulation

**Multi-OU rollout:** attach the SCP at the highest OU that
should inherit it. Child OUs inherit automatically.

```text
Root
 ├─ OU_Sandbox     [FullAWSAccess kept — Deny-list SCP]
 ├─ OU_Prod
 │   ├─ OU_Prod_Data [Allow-list + FullAWSAccess detached]
 │   └─ OU_Prod_Apps [Deny-list SCP]
 └─ OU_BreakGlass  [FullAWSAccess kept, NO restrictive SCP]
```

**Verify effective policy at any target:**

```bash
aws organizations list-policies-for-target --target-id 111122223311 \
  --filter SERVICE_CONTROL_POLICY --query 'Policies[*].{Name:Name,Id:Id}' --output table
aws organizations list-parents --child-id 111122223311   # trace OU chain
```

**Policy simulation:** the IAM `simulate-custom-policy` /
`simulate-principal-policy` APIs simulate IAM, NOT SCPs. Use
them as a pre-attach hint; the source of truth is post-attach
CloudTrail observation.

```bash
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::111122223311:role/SCPTestRole \
  --action-names organizations:LeaveOrganization cloudtrail:DeleteTrail \
  --query 'EvaluationResults[*].{Action:EvalActionName,Decision:EvalDecision}' --output table
```

## Step 12 — SCP exceptions (break-glass accounts)

Two safe patterns:

**Pattern A: break-glass OU.** Carve out an OU whose SCP chain
does NOT include the restrictive Deny. Place break-glass
accounts in that OU.

**Pattern B: Condition-based exemption.** Use `StringNotEquals`
on `aws:PrincipalAccount` or `aws:PrincipalARN` inside the Deny
statement.

```json
{
  "Effect": "Deny", "Action": "iam:DeleteRole", "Resource": "*",
  "Condition": { "StringNotEquals": { "aws:PrincipalAccount": "111122223311" } }
}
```

**NEVER** use `aws:UserAgent` or `aws:Referer` — these are
attacker-controllable via HTTP headers.

## Step 13 — CloudTrail for SCP-denied actions

SCP-denied API calls surface in CloudTrail as
`eventType: AwsApiCall` with
`errorCode: Client.UnauthorizedOperation` and a diagnostic in
`additionalEventData` indicating the SCP match.

```bash
# CloudTrail Logs Insight query for SCP-blocked calls (last 24h)
aws logs start-query \
  --log-group-name <org-trail-log-group> \
  --start-time $(($(date +%s) - 86400))000 \
  --end-time   $(date +%s)000 \
  --query-string 'fields @timestamp, eventName, awsAccountId, userIdentity.arn
| filter errorCode = "UnauthorizedOperation"
| filter organizationalAccessCheckDecision = "Denied"
| sort @timestamp desc | limit 50'
```

Without an Organization-level CloudTrail trail, SCP denials are
NOT centrally visible — each member account logs to its own
trail.

## Step 14 — Organizations delegated administrator

```bash
aws organizations register-delegated-administrator \
  --account-id 111122223311 --service-principal access-analyzer.amazonaws.com

aws organizations list-delegated-administrators

aws organizations deregister-delegated-administrator \
  --account-id 111122223311 --service-principal access-analyzer.amazonaws.com
```

The delegated administrator gains read/list access to member
accounts for the named service principal. The delegated admin
CANNOT create/attach SCPs — only the management account can.
Common delegations: Access Analyzer, Audit Manager, AWS Backup,
Firewall Manager, GuardDuty, Security Hub.

## Step 15 — Recent features

**Recent AWS features (2023-2026):**

- **Effective-SCP visualization (2023-2024):** Organizations
  console renders the effective-SCP intersection at every
  account. Scriptable via `list-policies-for-target` +
  `list-parents`.
- **Backup policy support for Aurora, FSx, stacked resources
  (2023-2024):** Tag-based selection matches
  `aws:ResourceTag/*` with `StringLike` for prefix matching.
- **AI services opt-out expansion (2023-2025):** New AI services
  auto-fall-under the `default` key when
  `opt_out_enabled_at_level: account` is set.
- **Tag policy enforcement for EC2 network interfaces and EBS
  snapshots (2024-2025):** `enforced_for` accepts
  `ec2:network-interface` and `ec2:snapshot`.
- **CloudTrail `organizations:EffectiveApiName` (2024-2025):**
  Deny events now include the SCP statement Sid that triggered
  the Deny.
- **Delegated administrator expansion (2024-2025):** New
  delegable principals (Audit Manager, Resource Explorer 2,
  Systems Manager QuickSetup). Each is service-scoped — none
  grant SCP-write.

## NEVER do these things

1. **NEVER detach `FullAWSAccess` without first attaching an
   Allow-list SCP.** The account locks out of every AWS API
   (including break-glass). Always attach the Allow-list first.

2. **NEVER rely on an SCP to GRANT permissions.** SCPs only
   filter. An `Allow: ec2:*` SCP has zero effect unless IAM
   also allows `ec2:*`.

3. **NEVER assume the management account is constrained by
   SCPs.** The management account is exempt from every SCP.

4. **NEVER mix Allow-list and Deny-list strategy at the same
   entity while `FullAWSAccess` is still attached.** The
   Allow-list is silently redundant.

5. **NEVER use `aws:UserAgent` or `aws:Referer` for break-glass
   Condition exemptions.** These keys are attacker-controllable.
   Use `aws:PrincipalAccount` or `aws:PrincipalARN` (immutable).

6. **NEVER put a Deny at root without first testing break-glass.**
   Carve out the break-glass OU or Condition exemption BEFORE
   attaching at root.

7. **NEVER rely on `simulate-custom-policy` alone for SCP
   validation.** It simulates IAM, not Organizations. Source of
   truth is post-attach CloudTrail observation.

8. **NEVER expect an SCP `Resource` element to be honored.**
   SCPs ignore `Resource` — every statement applies org-wide.
   Use `Condition` with `aws:ResourceTag/*` for scope.

9. **NEVER attach more than 5 SCPs to a single entity without a
   limit-increase request.** The default soft-quota is 5,
   inclusive of `FullAWSAccess`.

10. **NEVER rely on a delegated administrator to create or
    attach SCPs.** Delegation is read/list-only for the
    Organizations policy API.

## Output format

```text
ORGANIZATIONS_POLICY: <policy-name> (<policy-id>) [<type>] → <target-type>:<target-id>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Organization "All features" enabled
  [✓|✗] Caller in management account: <account-id>
  [✓|✗] Policy type enabled: SERVICE_CONTROL_POLICY (ENABLED)
  [✓|✗] Policy JSON validated: <simulate-principal-policy result>
  [✓|✗] Policy created: <policy-id> — ENABLED
  [✓|✗] Policy attached: <policy-id> → <target-type>:<target-id>
  [✓|✗] Strategy: Deny-list (FullAWSAccess kept) | Allow-list (FullAWSAccess detached)
  [✓|✗] FullAWSAccess at target: KEPT | DETACHED (replacement Allow-list: <policy-id>)
  [✓|✗] Break-glass path: <OU path or Condition key>
  [✓|✗] CloudTrail org trail: <trail-name> — Logging
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws organizations describe-policy --policy-id <policy-id>
  aws organizations list-policies-for-target --target-id <target-id> --filter SERVICE_CONTROL_POLICY
  aws organizations list-parents --child-id <target-id>
  aws iam simulate-principal-policy --policy-source-arn <role-arn> --action-names <action>
```

### Worked example — root guardrails Deny-list SCP with break-glass

```text
ORGANIZATIONS_POLICY: root-guardrails (p-aaa1bbb2) [SERVICE_CONTROL_POLICY] → root:r-xxxx
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Organization feature set: ALL
  [✓] Caller in management account: 123456789012
  [✓] Policy type enabled: SERVICE_CONTROL_POLICY (ENABLED)
  [✓] Policy JSON validated: implicitDeny on blocked actions
  [✓] Policy created: p-aaa1bbb2 — ENABLED
  [✓] Attachment target exists: root:r-xxxx
  [✓] Policy attached: p-aaa1bbb2 → r-xxxx
  [✓] Strategy: Deny-list (FullAWSAccess kept)
  [✓] FullAWSAccess status at target: KEPT
  [✓] Break-glass path: OU_BreakGlass — Deny NOT inherited
  [✓] CloudTrail org trail: org-management-trail — Logging
  [✓] Tags: Governance=root-guardrails, Owner=cloudops
VERIFICATION_COMMANDS:
  aws organizations describe-policy --policy-id p-aaa1bbb2
  aws organizations list-policies-for-target --target-id r-xxxx --filter SERVICE_CONTROL_POLICY
  aws organizations list-parents --child-id 111122223311
  aws iam simulate-principal-policy --policy-source-arn arn:aws:iam::111122223311:role/SCPTestRole --action-names organizations:LeaveOrganization
```

## Error handling

### Account locked out after FullAWSAccess detach

- An Allow-list SCP was not attached BEFORE detaching
  `FullAWSAccess`, OR the Allow-list did not include break-glass
  actions. Recover from the management account: re-attach
  `FullAWSAccess` (or attach the Allow-list), then retry.

### AttachPolicy fails with quota error

- The target already has 5 SCPs attached (inclusive of
  `FullAWSAccess`). Detach an unused SCP or request a quota
  increase via Support. The limit is per-entity.

### SCP attached but no effect

- Either (a) the SCP is `DISABLED` (enable with `update-policy`),
  (b) for an Allow-list strategy `FullAWSAccess` is still
  attached at the same entity (detach it), or (c) the action is
  not permitted by IAM in the member account (SCPs only filter).

### simulate-custom-policy shows Allowed but the call is blocked

- `simulate-custom-policy` simulates IAM, NOT Organizations. The
  actual SCP effect is invisible to it. Verify via
  `list-policies-for-target` along the hierarchy and a post-
  attach CloudTrail observation.

### Tag policy not blocking non-compliant tags

- The `enforced_for` list does not include the resource type.
  Add the resource type (e.g., `ec2:instance`) and re-attach.
  Without `enforced_for`, tag policies are audit-only.

## Domain

AWS CloudOps / AWS Organizations Governance — Service Control
Policies, Tag Policies, Backup Policies, AI Services Opt-Out
Policies, and Delegated Administrator Administration.

## AWS documentation

- **Organizations SCPs** — https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps.html
- **SCP strategies** — https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps_strategies.html
- **SCP inheritance** — https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps_inheritance.html
- **FullAWSAccess managed policy** — https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps_full.html
- **Tag policies** — https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_tag-policies.html
- **Backup policies** — https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_backup.html
- **AI services opt-out policies** — https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_ai-opt-out.html
- **Policy simulation** — https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_testing-policies.html
- **Delegated administrator** — https://docs.aws.amazon.com/organizations/latest/userguide/orgs_delegate_policies.html
- **CloudTrail organizations trail** — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/creating-trail-organization.html
