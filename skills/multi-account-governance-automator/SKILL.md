---
name: multi-account-governance-automator
description: Designs AWS multi-account governance automation spanning Organizations (OU hierarchy, account creation, SCP guardrail/throttle/deny strategies), Control Tower (landing zone, preventive + detective guardrails, Account Factory Factory), delegated administration (audit + log-archive accounts, GuardDuty/Security Hub/Config delegated admin), AWS Config multi-account aggregator, CloudTrail organization trail, Security Hub aggregator, IAM Identity Center (permission sets, SSO across accounts), account vending machine (Control Tower Account Factory or Service Catalog + Lambda baseline-stack), AWS Resource Explorer (cross-account search index), and RAM cross-account resource sharing. Emits AUTOMATED with deployment plan or MANUAL_STEP_REQUIRED with the specific gap (e.g., root email + billing alarm + SCP inheritance order). Use when standing up or hardening a multi-account AWS organization.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline plan authoring. Live deployment uses aws organizations create-organization, create-organizational-unit, create-account, create-policy, attach-policy, move-account, enable-policy-type, aws controltower create-landing-zone, create-account, aws configservice put-configuration-aggregator, put-aggregation-authorization, aws cloudtrail create-organization-trail (or update), aws...
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '4'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Governance
  task_type: automate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: AUTOMATED | MANUAL_STEP_REQUIRED
  when_to_use: Standing up a new multi-account AWS organization, designing an OU hierarchy and SCP baseline, deploying or hardening a Control Tower landing zone, wiring GuardDuty/Security Hub/Config as delegated administrators in an audit account, centralizing CloudTrail and Config aggregation, rolling out IAM Identity Center permission sets across member accounts, building an account vending machine, scoping SCP guardrails vs throttle vs deny, or hardening RAM cross-account shares.
  when_not_to_use: Single-account hardening with no cross-account component (use iam-hardening skill)., Tag governance in isolation (use tag-governance-automator — SCP TagPolicy is its surface)., Incident response automation (use incident-response-automator — containment, not governance)., Cost optimization across an org (use FinOps skills — this skill is structure + posture, not spend).
  activation_triggers: multi-account governance, OU hierarchy design, SCP baseline guardrail, Control Tower landing zone, Account Factory vending, Config aggregator cross-account, Security Hub delegated admin, CloudTrail organization trail, IAM Identity Center permission set, Resource Explorer cross-account index, RAM resource share cross-account
  invocation_schema: 'Input: either (a) a governance requirement ("set up a 50-account org with audit + log-archive", "design SCP guardrails that block root account actions", "deploy a Control Tower landing zone with GuardDuty delegated to audit"), OR (b) an existing Organizations / Control Tower / Config aggregator / Identity Center configuration to audit and harden. Output: deterministic GOVERNANCE block per requirement — STRUCTURE/CONTROLS/DELEGATION/SHARING/VERDICT — where VERDICT is AUTOMATED (deployment plan complete with all gates passing) or MANUAL_STEP_REQUIRED (specific gap cited, e.g., missing SCP inheritance review, stale service control policy, unaggregated member account).'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: AWS Organizations, OU hierarchy, SCP, service control policy, Control Tower, landing zone, guardrails, Account Factory, delegated administration, audit account, log archive, Config aggregator, CloudTrail organization trail, Security Hub aggregator, GuardDuty delegated admin, IAM Identity Center, permission set, account vending machine, SCP strategy, Resource Explorer, RAM resource share
  tags: aws-organizations, control-tower, scp, governance, iam-identity-center, config-aggregator, security-hub, cloudtrail, automate
---

# Multi-Account Governance Automator

## What this skill does

Designs automated AWS multi-account governance across four layers:
**structure** (Organizations OU tree + accounts + Control Tower landing
zone), **controls** (SCPs and guardrails that constrain what accounts can
do), **delegation** (security + logging services centralized in audit and
log-archive accounts via delegated administration), and **visibility**
(Config aggregator, Security Hub aggregator, CloudTrail org trail, Resource
Explorer). The fifth layer — **sharing** — covers RAM and Identity Center
for controlled cross-account resource and access sharing.

The verdict is binary: **AUTOMATED** when the design covers all four
layers, includes a documented SCP inheritance order, a tested landing-zone
or baseline-stack deployment, scoped delegated-admin roles, and an
aggregation coverage check across every member account; **MANUAL_STEP_REQUIRED**
when any layer has a gap (e.g., a member account not in the Config
aggregator, an SCP attached to the wrong OU, Identity Center without a
fallback break-glass path).

## Quick navigation

| # | Section | Jump when |
|---|---|---|
| 1 | [Pre-flight gate](#pre-flight-governance-spec-gate) | Starting any new org design — blocks unsafe specs |
| 2 | [Decision tree](#decision-tree--landing-surface) | Control Tower vs raw Organizations vs Landing Zone v2 |
| 3 | [OU hierarchy](#ou-hierarchy) | Designing the org tree + SCP inheritance |
| 4 | [SCP strategies](#scp-strategies--guardrail-vs-throttle-vs-deny) | Writing effective service control policies |
| 5 | [Control Tower](#control-tower-landing-zone) | Landing zone, guardrails, Account Factory |
| 6 | [Delegated administration](#delegated-administration) | Audit account, GuardDuty/SH/Config delegation |
| 7 | [Config aggregator](#aws-config-multi-account-aggregator) | Cross-account compliance visibility |
| 8 | [CloudTrail org trail](#cloudtrail-organization-trail) | Centralized API logging |
| 9 | [Security Hub aggregator](#security-hub-aggregator) | Cross-account findings |
| 10 | [IAM Identity Center](#iam-identity-center) | Permission sets, SSO, break-glass |
| 11 | [Account vending machine](#account-vending-machine) | Automated account creation with baseline |
| 12 | [Resource Explorer + RAM](#resource-explorer--ram-cross-account) | Cross-account search + sharing |
| 13 | [STRICT output contract](#output-format-strict-output-contract) | The exact GOVERNANCE block the skill emits |
| 14 | [NEVER anti-patterns](#never-these-things) | The hardcoded list of governance taboos |
| 15 | [Expert heuristic](#expert-heuristic-callouts) | Non-obvious behaviors that change the design |
| 16 | [Recent AWS features](#recent-aws-features-2024-2026) | Landing Zone v2, CT customizations, Resource Explorer |

## Mindset

**One-line takeaway:** multi-account governance is a *blast-radius control*
system — the OU tree and SCPs determine what an attacker (or careless
admin) can reach from any compromised account. A flat org with no SCPs
gives every account the same blast radius as the management account; a
tiered org with deny-list SCPs at the root and allow-list SCPs at the
workload OU shrinks blast radius to one account.

- **SCP inheritance is cumulative and intersectional.** A policy attached
  to the root intersects with every policy attached down the OU chain to
  the account. An `Allow *` at the root does NOT override a `Deny` at a
  child OU — `Deny` always wins.
- **The management account is NOT governed by SCPs.** SCPs apply to
  member accounts only. Protect it with MFA, break-glass procedures, and
  zero standing access — never as a workload account.
- **Control Tower guardrails are SCPs + Config rules + Lambda.** "Strongly
  recommended" guardrails are SCPs at the root; "elective" guardrails are
  SCPs at specific OUs.

## Pre-flight: governance spec gate (run before generation)

| Attribute | Required | Effect on plan |
|---|---|---|
| `org_design_intent` | YES | New org / migrate-to-Control-Tower / harden existing |
| `account_count_target` | YES | Determines OU depth and SCP fan-out |
| `compliance_framework` | Recommended | PCI/SOC/HIPAA/FedRAMP drives mandatory SCP set |
| `existing_landing_zone` | For audit mode | When provided, skip generation and run the layer gates |
| `audit_account_id` | Recommended | Required for delegation layer gate |
| `log_archive_account_id` | Recommended | Required for CloudTrail centralization |

**If the spec is incomplete**, output the MANUAL_STEP_REQUIRED block:

```text
STRUCTURE: <unknown>
CONTROLS: <unknown>
DELEGATION: <unknown>
SHARING: <unknown>
VERDICT: MANUAL_STEP_REQUIRED
REASON: Spec is missing required fields (<list>).
REQUIRED:
  - org_design_intent (new | migrate | harden)
  - account_count_target (integer)
REMEDIATION: Provide intent and target account count. Example:
  "stand up a 50-account org with audit + log-archive, PCI compliance"
  maps to org_design_intent=new, account_count_target=50,
  compliance_framework=PCI.
```

**Live-account pre-flight checks (skip for offline authoring):**
1. Verify Organizations is enabled: `aws organizations describe-organization`.
2. Verify all features are enabled (not just consolidated billing):
   `aws organizations describe-organization --query 'Organization.FeatureSet'` must be `ALL`.
3. Verify the management account root has MFA + no access keys.
4. Verify Control Tower is available (look for
   `aws controltower list-landing-zones` returning non-empty, or plan to create).

## Decision tree — landing surface

```
START
  ├─ greenfield org, want AWS-managed baseline? ──► Control Tower Landing Zone
  ├─ greenfield org, want full control? ─────────► Raw Organizations + custom SCPs + Code Pipeline baseline
  ├─ existing org + already on Control Tower? ────► Harden: Landing Zone v2 drift detection, custom SCPs
  ├─ existing org + raw Organizations? ───────────► Migrate to CT (if eligible) OR add CT-equivalent baseline
  └─ (unrecognized intent) ───────────────────────► MANUAL_STEP_REQUIRED with mapping hint
```

- **Control Tower:** preferred for greenfield. Provisions audit +
  log-archive accounts, root + OU SCPs, Account Factory, Identity Center,
  and a CloudTrail org trail in one orchestrated deployment.
- **Raw Organizations + custom:** preferred when you need a non-CT
  management region, custom account baselines, or a CI/CD-driven model.
- **Landing Zone v2 (2024-2025):** if already on CT, upgrade for drift
  detection, customizable guardrails, and lifecycle controls.

## OU hierarchy

Design the OU tree before any SCP work. Three canonical patterns:

### Pattern A — Functional (small orgs, <20 accounts)
```
root
├── Security (audit, log-archive)
├── SharedServices (network, IAM, CI/CD)
├── Workloads-Prod
├── Workloads-NonProd
└── Sandboxes
```

### Pattern B — Business-unit + environment (medium orgs, 20-200)
```
root
├── Security
├── Infrastructure
├── BusinessUnit-A
│   ├── Prod / NonProd / Sandbox
├── BusinessUnit-B
│   ├── Prod / NonProd
└── Suspended (quarantine OU for compromised accounts)
```

### Pattern C — OU-per-tenant (SaaS, hundreds-thousands)
```
root
├── Platform
├── Tenants-Prod / Tenants-NonProd
```

**Rules:** one OU per environment per BU (never mix prod/nonprod in one
account). Always have a `Suspended` OU with a Deny-all SCP for
compromised accounts. Keep OU depth <= 5.

```bash
ROOT_ID=$(aws organizations list-roots --query 'Roots[0].Id' --output text)
SEC_OU=$(aws organizations create-organizational-unit \
  --parent-id $ROOT_ID --name Security \
  --query 'OrganizationalUnit.Id' --output text)
```

## SCP strategies — guardrail vs throttle vs deny

### 1. Guardrail (prevent specific dangerous actions)
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "GuardrailDenyLeaveOrg",
      "Effect": "Deny",
      "Action": ["organizations:LeaveOrganization"],
      "Resource": "*"
    },
    {
      "Sid": "GuardrailDenyRootActions",
      "Effect": "Deny",
      "NotAction": ["iam:CreateVirtualMFADevice", "iam:EnableRootMFA", "iam:Get*"],
      "Resource": "*",
      "Condition": {"StringLike": {"aws:PrincipalArn": ["arn:aws:iam::*:root"]}}
    }
  ]
}
```
Attach at the **root** — every account inherits.

### 2. Throttle (limit scale, not block)
```json
{
  "Sid": "ThrottleRegions",
  "Effect": "Deny",
  "Action": ["ec2:RunInstances", "rds:CreateDBInstance"],
  "Resource": "*",
  "Condition": {"StringNotEquals": {"aws:RequestedRegion": ["us-east-1", "eu-west-1"]}}
}
```
Use to constrain regions, instance types, or service quotas across an OU.

### 3. Deny-list (explicitly forbid services)
```json
{
  "Sid": "DenyUnusedServices",
  "Effect": "Deny",
  "Action": ["alexaforbusiness:*", "qldb:*", "macie2:*"],
  "Resource": "*"
}
```

**SCP evaluation order:** Root -> parent OU -> child OU -> account. Deny
always wins over Allow. Multiple SCPs at the same level are intersected.
A policy at the root applies to ALL member accounts (NOT the management
account).

```bash
aws organizations create-policy --type SERVICE_CONTROL_POLICY \
  --name guardrail-baseline \
  --content file://guardrail-scp.json
aws organizations attach-policy --policy-id <id> --target-id <root-id>
```

## Control Tower landing zone

Control Tower orchestrates a full governance baseline in one deployment.

**What it provisions:** two foundational accounts (`audit` for Config
aggregator + Security Hub + GuardDuty delegated admin; `log-archive` for
CloudTrail + Config history S3 buckets), guardrails (root-level preventive
SCPs + Config detective rules), Account Factory (Service Catalog product
that vends new accounts with baseline auto-deployed), and IAM Identity
Center (SSO across member accounts).

### Landing Zone v2 (2024-2025)
Landing Zone v2 creation command and capability notes (drift detection, customizable guardrails, Account Factory lifecycle controls): moved verbatim to [references/control-tower-landing-zone.md](references/control-tower-landing-zone.md).
See that reference for the full LZ v2 architecture and failure modes.

### Create a new account via Account Factory
Account Factory account-creation command and baseline-inheritance notes: moved verbatim to [references/control-tower-landing-zone.md](references/control-tower-landing-zone.md).
What the landing zone provisions is summarised above; the full workflow lives in the reference.

## Delegated administration

Centralize security and logging services in the audit account. NEVER run
GuardDuty / Security Hub / Config admin from the management account —
the management account should hold no workload.

Delegated-admin enablement commands (GuardDuty, Security Hub, Config aggregator): moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Always delegate to the audit account — see the NEVER list below.

Detective / Macie / Access Analyzer follow the same
`enable-organization-admin-account` pattern. Detective requires GuardDuty
as a prerequisite.

## AWS Config multi-account aggregator

The aggregator lives in the audit account. Use
`OrganizationAggregationSource` (NOT `AccountAggregationSources` list) —
org source auto-discovers new member accounts; account sources require
manual add per account.

**Verify coverage:** for every member account, ensure the Config recorder
is ON and delivering. A member without a recorder contributes zero
compliance data to the aggregator — silent gap.

Config recorder coverage verification commands: moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
IsRecording must be true and LastStatus SUCCESS in every member account.

## CloudTrail organization trail

Organization trail creation command: moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
The gotchas (org bucket policy, KMS) remain below.

**Gotchas:** the log-archive S3 bucket needs an org-level bucket policy
allowing `s3:PutObject` from every member account's
`cloudtrail.amazonaws.com` service principal — use `aws:PrincipalOrgID`
condition (never enumerate account IDs). The KMS key needs a key policy
allowing member accounts to `kms:GenerateDataKey` for CloudTrail — same
`aws:PrincipalOrgID` pattern. One org trail covers all members + all
regions. Do NOT also create per-account trails — duplicate events, double
cost.

## Security Hub aggregator

Security Hub aggregator creation command: moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Aggregation semantics (region linking, cross-region lag) remain below.

Findings from member accounts in all linked regions aggregate to the
audit account. The aggregator runs every 30 minutes by default. Verify
every member account has Security Hub enabled — a member with Hub
disabled does not send findings (silent gap).

## IAM Identity Center

Identity Center (formerly AWS SSO) is the preferred cross-account access
layer. NEVER use cross-account IAM role assumption as the primary access
model at scale.

Identity Center permission-set creation and assignment commands: moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Keep the break-glass path noted below.

**Break-glass path:** always have at least one permission set assigned to
an emergency-only group that grants `AdministratorAccess` on the
management account. Store credentials in a sealed envelope. Test
quarterly. Identity Center outages otherwise lock you out of the org.

## Account vending machine

Three patterns, in order of preference:

1. **Control Tower Account Factory (preferred):** `aws controltower
   create-account`. Auto-deploys baseline, enrolls in Identity Center,
   attaches guardrails.
2. **Service Catalog + Lambda (not on CT):** SC product backed by
   CloudFormation that creates the account, deploys baseline resources,
   enrolls in the aggregator. Trigger via `ProvisionProduct`.
3. **Organizations `create-account` + CodePipeline (raw):** Pipeline
   waits for `AccountStatus=ACTIVE`, assumes the new account's
   `OrganizationAccountAccessRole`, deploys the baseline via StackSets.

Account-vending commands (Account Factory and alternatives): moved verbatim to [references/control-tower-landing-zone.md](references/control-tower-landing-zone.md).
Pattern preferences and the required new-account baseline remain below.

**Required baseline in every new account:** CloudTrail (verify, do not
re-create), Config recorder + delivery channel, Security Hub enabled,
default VPC removed or hardened, AWS Backup vault, SNS topic for
account-level alerts, cross-account admin IAM role.

## Resource Explorer + RAM cross-account

### AWS Resource Explorer (2024-2025)
Resource Explorer setup commands (local + aggregator indexes) and use cases: moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Note the 36-hour cold-start caveat before relying on it.

### RAM cross-account resource sharing
```bash
aws ram create-resource-share \
  --name share-transit-gateway \
  --resource-arns arn:aws:ec2:us-east-1:<account>:transit-gateway/tgw-xxx \
  --principals <member-account-id> \
  --allow-external-principals false
```
Use for Transit Gateway sharing, License Manager, Route 53 Resolver
rules, subnets. Default `allow-external-principals=false` restricts to
org members only.

## Output format (STRICT output contract)

```text
STRUCTURE:
  Org status: <all-features | consolidated-billing-only>
  OU depth: <integer>
  Foundational accounts: audit=<id>, log-archive=<id>
  Management account MFA: <yes/no>
CONTROLS:
  - [PASS|FAIL] Root-level guardrail SCP attached
  - [PASS|FAIL] SCP denies organizations:LeaveOrganization
  - [PASS|FAIL] SCP denies root-account actions except IAM MFA setup
  - [PASS|FAIL] Region-throttle SCP attached at workload OU
  - [PASS|FAIL] SCP inheritance reviewed (Deny wins over Allow)
DELEGATION:
  - [PASS|FAIL] GuardDuty delegated to audit account <id>
  - [PASS|FAIL] Security Hub delegated to audit account <id>
  - [PASS|FAIL] Config aggregator in audit account (org source, AllRegions)
  - [PASS|FAIL] CloudTrail org trail to log-archive account
SHARING:
  - [PASS|FAIL] IAM Identity Center with permission sets
  - [PASS|FAIL] Break-glass path documented + tested
  - [PASS|FAIL] Resource Explorer aggregator index
  - [PASS|FAIL] RAM shares scoped to org (allow-external-principals=false)
VERDICT: AUTOMATED | MANUAL_STEP_REQUIRED
FINDINGS:
  - [INFO|WARN|HIGH|CRITICAL] <observation>
REMEDIATION:
  1. <step 1>
  2. <step 2>
```

### Worked example — AUTOMATED full design
```text
STRUCTURE:
  Org status: all-features
  OU depth: 3 (root -> BU -> environment)
  Foundational accounts: audit=111111111111, log-archive=222222222222
  Management account MFA: yes (virtual MFA, no access keys)
CONTROLS:
  - [PASS] Guardrail SCP "deny-leave-org" attached at root r-abc0
  - [PASS] SCP denies organizations:LeaveOrganization
  - [PASS] SCP denies root-account actions except iam:CreateVirtualMFADevice
  - [PASS] Region throttle SCP at Workloads-Prod OU (us-east-1, eu-west-1 only)
  - [PASS] SCP inheritance reviewed — Deny at child OU overrides root Allow
DELEGATION:
  - [PASS] GuardDuty delegated to audit account 111111111111
  - [PASS] Security Hub delegated to audit account 111111111111 (CIS + Foundational)
  - [PASS] Config aggregator OrgConfigAggregator in audit account (org source, AllRegions=true)
  - [PASS] CloudTrail org-trail delivering to log-archive S3 bucket org-trail-logs-2222
SHARING:
  - [PASS] IAM Identity Center with AWSAdministratorAccess (1h) + AWSReadOnlyAccess (4h)
  - [PASS] Break-glass path: EmergencyAdmin permission set, sealed envelope, tested 2026-07-15
  - [PASS] Resource Explorer aggregator index in audit account, view CrossAccountView
  - [PASS] RAM shares scoped to org (allow-external-principals=false on all 4 shares)
VERDICT: AUTOMATED
FINDINGS:
  - [INFO] All 47 member accounts enrolled in GuardDuty, Security Hub, Config aggregator
  - [WARN] Detective not enabled — enable if investigation graph is a requirement
REMEDIATION:
  1. Enable Detective: aws detective enable-organization-admin-account --admin-account-id 111111111111
```

### Worked example — MANUAL_STEP_REQUIRED (SCP gap)
Full MANUAL_STEP_REQUIRED worked example: moved verbatim to [references/worked-examples.md](references/worked-examples.md).
The AUTOMATED example above is the primary contract demonstration.

## NEVER (these things)

- NEVER run GuardDuty, Security Hub, or Config admin from the management
  account. The management account is the highest-value target — coupling
  security tooling to it means a compromise of the management account
  also blinds the security team. Delegate to the audit account.

- NEVER attach an SCP to a member account directly when the intent is
  org-wide. Attach at the root for org-wide; at an OU for org-subtree.
  Account-level SCPs do not scale and produce drift.

- NEVER assume `Allow *` at the root overrides a `Deny` at a child OU.
  SCP evaluation is intersectional — Deny always wins. Operators who
  debug "why can't this account run EC2" often miss a Deny SCP three
  levels up the OU tree.

- NEVER rely on cross-account IAM assume-role as the primary access
  model at org scale. It does not federate with the corporate IdP, has
  no central permission management, and rotates credentials poorly. Use
  IAM Identity Center.

- NEVER skip the break-glass path. Identity Center outages (or a
  misconfigured IdP federation) can lock you out of the entire org.
  Always have an emergency permission set on the management account,
  tested quarterly, credentials in a sealed envelope.

## Expert heuristic callouts

Expert heuristic callouts (SCP condition scoping, management-account quirks, latencies, ARN regionality, silent failures, drift gaps): moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load before designing SCPs or account-creation automation.

## Pre-flight safety checks

Pre-flight safety checks (confirmation gate, dry-run SCP attachment, management-account hardening, SCP snapshots, aggregator verification): moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
The CONFIRM gate is mandatory before any state-changing operation.

## Edge-case handling

Edge-case catalog (member leaves org, SCP conflicts, drift, aggregator coverage gaps): moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Consult when the design hits a non-standard org state.

## Recent AWS features (2024-2026)

Recent AWS features (2024-2026): moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Check before recommending Resource Explorer, RAM, or LZ v2 capabilities.

## Domain

AWS CloudOps / Multi-Account Governance Automation.

## AWS documentation

- **AWS Organizations** — https://docs.aws.amazon.com/organizations/latest/userguide/
- **AWS Control Tower** — https://docs.aws.amazon.com/controltower/latest/userguide/
- **AWS Config** — https://docs.aws.amazon.com/config/latest/developerguide/
- **AWS CloudTrail** — https://docs.aws.amazon.com/awscloudtrail/latest/userguide/
- **AWS Security Hub** — https://docs.aws.amazon.com/securityhub/latest/userguide/
- **AWS IAM Identity Center** — https://docs.aws.amazon.com/singlesignon/latest/userguide/
- **AWS Resource Explorer v2** — https://docs.aws.amazon.com/resource-explorer-2/latest/userguide/
- **AWS RAM** — https://docs.aws.amazon.com/ram/latest/userguide/
- **AWS Multi-Account Strategy (WAF)** — https://docs.aws.amazon.com/wellarchitected/latest/framework/a-foundation-multiple-accounts.html

## References (load on demand)

- [references/scp-strategies.md](references/scp-strategies.md) — SCP pattern library (guardrail, throttle, deny-list, allow-list, deny-all) with JSON and debugging.
- [references/control-tower-landing-zone.md](references/control-tower-landing-zone.md) — LZ v2 architecture, Account Factory workflow, drift detection, account vending commands.
- [references/advanced-patterns.md](references/advanced-patterns.md) — Expert heuristic callouts, edge-case catalog, Resource Explorer setup, recent AWS features (2024-2026).
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — Delegated-admin, Config, CloudTrail, Security Hub, Identity Center commands and pre-flight safety checks.
- [references/worked-examples.md](references/worked-examples.md) — Secondary worked example (MANUAL_STEP_REQUIRED SCP gap).

