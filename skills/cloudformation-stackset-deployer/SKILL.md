---
name: cloudformation-stackset-deployer
description: 'Provisions AWS CloudFormation StackSets with production defaults: StackSet creation (template, parameters, capabilities), permission model (SELF_MANAGED admin+execution roles vs SERVICE_MANAGED with Organizations trusted access), deployment targets (OUs, accounts, regions), operation preferences (failure tolerance, max concurrent accounts/regions), drift detection per instance and StackSet-level, StackSet vs nested stacks, managed execution, CloudFormation IaC generator. Emits a READY_TO_DEPLOY checklist. Use when deploying a template across many accounts and/or regions, choosing self vs service-managed, scoping OU targets, tuning blast radius, or enabling drift detection. Triggers: create stackset, cloudformation stackset, service-managed stackset, self-managed stackset, StackSet Organizations, stackset drift detection, IaC generator.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with cloudformation, organizations, and iam access; AWS Organizations must have CloudFormation trusted access enabled for the SERVICE_MANAGED permission model. Works with Terraform aws_cloudformation_stack_set / aws_cloudformation_stack_set_instance resources and CloudFormation AWS::CloudFormation::StackSet templates.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: DevTools
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, cloudformation, stackset, cloudops, deploy, devtools, provisioning, multi-account, organizations, drift-detection
  dependencies: aws-orchestrator
  keywords: aws, cloudformation, stackset, stack set, cloudops, deploy, provisioning, multi-account, multi-region, organizations, self-managed, service-managed, drift detection, stack instances, operation preferences, failure tolerance, max concurrent, nested stacks, iac generator, infrastructure as code
  when_to_use: Invoke when the user wants to create or update a CloudFormation StackSet to deploy a single template across many AWS accounts and/or regions, choose between SELF_MANAGED and SERVICE_MANAGED permission models, target organizational units for automatic member-account deployment, configure operation preferences (failure tolerance, max concurrent accounts/regions), enable StackSet or per-instance drift detection, decide between StackSets and nested stacks, or generate CloudFormation templates from existing AWS resources via the IaC generator. Do NOT invoke for single-account single-region stacks (use aws cloudformation deploy directly), for drift detection on a standalone stack (use cloudformation-drift-troubleshooter), or for raw stack failures (use cloudformation-stack-troubleshooter).
---

# CloudFormation StackSet Deployer

An AWS CloudOps agent skill that provisions AWS CloudFormation
StackSets with correct defaults. The skill walks the operator
through permission model selection, deployment target scoping,
operation preferences tuning, and drift detection, captures the
template+parameters and organization context, explains why each
default matters, and emits a READY_TO_DEPLOY checklist with copy-
pasteable verification commands.

## Activation keywords

create stackset, cloudformation stackset, service-managed
stackset, self-managed stackset, StackSet Organizations, StackSet
drift detection, stack instances, deploy template multiple
accounts, operation preferences, nested stacks vs stacksets, IaC
generator CloudFormation.

## STRICT output contract

When this skill is invoked with a StackSet provisioning request
(template, targets, regions, permission model, or partial config),
the agent MUST respond with the READY_TO_DEPLOY checklist from the
"Output format" section using the literal all-caps labels
`STACKSET:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface with prose, headings, or
disclaimers — emit the block as the first response lines. This
contract is what assertion-based evals and provisioning pipelines
rely on; deviating breaks automation silently.

If any prerequisite is missing, the verdict is
`PREREQUISITES_MISSING` with a specific gap citation (marked
`[✗]`), and `READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Permission model (SELF_MANAGED vs SERVICE_MANAGED) | Boundary call |
| Step 2 — Deployment targets (OUs, accounts, regions) | Scope |
| Step 3 — StackSet creation (template, parameters, capabilities) | Provisioning core |
| Step 4 — Operation preferences (failure tolerance, concurrency) | Blast radius |
| Step 5 — Stack instances (deploy, managed execution) | Instance lifecycle |
| Step 6 — Drift detection (per-instance and StackSet-level) | Governance |
| Step 7 — StackSets vs nested stacks | Architecture decision |
| Step 8 — Update and delete operations | Lifecycle |
| Step 9 — Recent features (StackSet drift, IaC generator) | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/permission-models-and-roles.md | IAM role deep dive |
| references/operation-preferences-and-drift.md | Op prefs + drift detail |

## Mindset

**One-line takeaway:** A StackSet deploys ONE CloudFormation
template across MANY accounts and/or regions from ONE
administrator account. SERVICE_MANAGED integrates with AWS
Organizations for automatic future-account inclusion; SELF_MANAGED
requires explicit account lists and IAM role handshakes per target
account. Operation preferences control blast radius — failure
tolerance + max concurrency are the two dials.

Three misconceptions dominate StackSet misdesign:

- **"StackSets and nested stacks are interchangeable."** A nested
  stack is a child inside ONE parent stack in ONE account/region.
  A StackSet is a multi-account/multi-region deployment wrapper.
  Use nested stacks for decomposition within one stack; use
  StackSets for fan-out across accounts/regions.

- **"SELF_MANAGED is simpler."** It is not, for any org with more
  than a few accounts. SELF_MANAGED requires an administration role
  in the admin account AND an execution role (with matching trust
  policy) in EVERY target account. New accounts are NOT auto-
  included. SERVICE_MANAGED leverages Organizations trusted access —
  no per-account role setup and new accounts in targeted OUs are
  included automatically.

- **"Default operation preferences are fine."** Defaults
  (`FailureToleranceCount=0`, `MaxConcurrentCount=1`) are too
  conservative for large fan-outs. Tune failure tolerance so a
  single account failure does not halt the deployment, and tune
  max concurrency to control the parallel blast radius.

## Configuration dependency graph (novel heuristic)

StackSet configurations are NOT independent. Several depend on
trusted access being enabled first; several are immutable after
creation; several silently break downstream member-account stacks.
Use this graph to sequence provisioning and to debug "why are my
stack instances stuck in OUTDATED?" later.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Permission model | SERVICE_MANAGED requires Organizations trusted access enabled | **CANNOT be changed after StackSet creation** — must delete and recreate to switch | service-linked role assumption in member accounts |
| Administration role (SELF_MANAGED) | IAM role AWSCloudFormationStackSetAdministrationRole in admin account with trust to cloudformation.amazonaws.com | role ARN set at create-time and used on every operation | assume the execution role in each target account |
| Execution role (SELF_MANAGED) | IAM role in EVERY target account (AWSCloudFormationStackSetExecutionRole) with trust to admin account ID | missing execution role in a target → `StackInstance` goes to `INOPERABLE` | CloudFormation creates the member stack |
| Deployment targets (SERVICE_MANAGED) | Organizations OU id (ou-xxx) or root id (r-xxx); OrganizationalUnitIds list | future accounts added to the OU are auto-deployed; removed accounts get stack instances deleted | automatic member-account enrollment |
| Deployment targets (SELF_MANAGED) | list of 12-digit account IDs | new accounts NOT auto-included — must run `create-stack-instances` again | explicit account fan-out |
| Regions | list of region names | region list is per-deployment-operation; can differ across deployments | per-account × per-region stack instances |
| Operation preferences | none — defaults apply if omitted | failure tolerance + max concurrency set per-operation, NOT per-StackSet | blast radius control on create/update/delete |
| Capabilities | CAPABILITY_IAM / CAPABILITY_NAMED_IAM / CAPABILITY_AUTO_EXPAND if template creates IAM or uses macros | omitting required capability → `InsufficientCapabilities` error on every operation | IAM-bearing template deployment |
| Parameters | template parameter declarations | parameters set per-deployment-operation; can override per-account via DeploymentTargets | template customization per target |
| StackSet drift detection | StackSet exists; both models supported | must be enabled explicitly via `detect-stack-set-drift`; NOT retroactive for past drift | StackSet-level drift status |
| Stack instance drift | stack instance exists | each instance has its own drift status; detected on-demand or via managed execution | per-instance remediation |

**The immutable rows are the ones a baseline model misses.** The
permission model is set at StackSet creation and CANNOT be changed
without deleting and recreating the StackSet. The administration
role name is similarly immutable. The procedure below forces an
explicit decision on each before the `create-stack-set` call.

**Cross-dependency gotchas:**
- SELF_MANAGED cannot be "upgraded" to SERVICE_MANAGED — must
  delete and recreate.
- SERVICE_MANAGED always skips the management (formerly "master")
  account. Use a SELF_MANAGED StackSet or standalone stack for it.
- Regions × accounts = cartesian product. N accounts × M regions =
  N×M stack instances.
- Disabling Organizations trusted access after a SERVICE_MANAGED
  StackSet exists breaks all future operations on that StackSet.

## Expert heuristic: SELF_MANAGED role handshake lifecycle

The SELF_MANAGED permission model is the #1 source of "why won't my
stack instance deploy?" issues. A baseline model says "create the
roles and go"; this heuristic explains the actual trust chain.

```text
Administrator account:
  → AWSCloudFormationStackSetAdministrationRole
     trust: cloudformation.amazonaws.com
     policy: sts:AssumeRole on arn:aws:iam::<target>:role/AWSCloudFormationStackSetExecutionRole

For EACH target account:
  → AWSCloudFormationStackSetExecutionRole
     trust: arn:aws:iam::<admin-account-id>:root
     policy: cloudformation:* + iam:PassRole

On create-stack-instances:
  → CloudFormation assumes administration role → assumes execution role
    → creates member stack in target account

Common failures:
  → execution role missing/wrong name in target → INOPERABLE
  → trust policy missing admin account ID → AccessDenied
  → SCP blocking cloudformation → silent skip
```

**Key implication:** every target account must have the execution
role pre-provisioned (via a bootstrap StackSet or manual IAM).

## Expert heuristic: SERVICE_MANAGED trusted access setup

SERVICE_MANAGED is simpler at scale but requires one-time
Organizations trusted-access enablement that a baseline model
often omits.

```text
One-time enablement (management account):
  aws organizations enable-aws-service-access \
    --service-principal cloudformation.amazonaws.com

Verify:
  aws organizations list-aws-service-access-for-organization \
    --service-principal cloudformation.amazonaws.com

Result:
  → CloudFormation creates AWSServiceRoleForCloudFormationStackSetsOrgNS
    SLR in the management account
  → Member accounts get a service-linked role when targeted
  → Trust path: CloudFormation → Organizations → member account SLR
  → No admin/execution role setup required
```

**Key implication:** if trusted access is later disabled, all
SERVICE_MANAGED StackSets become read-only until re-enabled. Treat
trusted access as a permanent dependency.

## Expert heuristic: operation preferences blast radius tuning

Operation preferences look like a minor knob; they are the single
most important blast-radius control on a StackSet deployment. A
baseline model accepts the defaults; this heuristic explains tuning.

```text
FailureToleranceCount / FailureTolerancePercentage
  → number (or %) of instances that can fail BEFORE halting the operation
  → DEFAULT: 0 (any failure halts) — TOO conservative for large fan-outs
  → Recommendation: set so ≤5% of instances can fail without halting

MaxConcurrentCount / MaxConcurrentPercentage
  → number (or %) of instances deployed IN PARALLEL
  → DEFAULT: 1 (sequential) — TOO slow for large fan-outs
  → Recommendation: 5-10 for typical orgs

Count and Percentage variants are MUTUALLY EXCLUSIVE per operation.
RegionConcurrencyType: SEQUENTIAL (default) or PARALLEL.
RegionOrder: only for SEQUENTIAL (e.g., ['us-east-1','us-west-2']).
```

**Production pattern:** `FailureTolerancePercentage=5`,
`MaxConcurrentPercentage=20`, `RegionConcurrencyType=SEQUENTIAL`,
`RegionOrder=[primary, secondary]`. Tolerate 5% failure, run 20%
of accounts in parallel per region, deploy regions sequentially.

**Safe pattern:** `FailureToleranceCount=0`, `MaxConcurrentCount=1`.
Halt on ANY failure, deploy ONE account at a time.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites.
If any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Administrator account | Runs create-stack-set | `aws sts get-caller-identity` |
| Template body or URL | Template to deploy; >51,200 bytes MUST be in S3 | local file or S3 URL |
| Permission model decided | IMMUTABLE after creation | SELF_MANAGED vs SERVICE_MANAGED |
| Organizations trusted access (SERVICE_MANAGED) | Without it, `InvalidOperationException` | `aws organizations list-aws-service-access-for-organization --service-principal cloudformation.amazonaws.com` |
| Administration role (SELF_MANAGED) | CloudFormation assumes this to fan out | `aws iam get-role --role-name AWSCloudFormationStackSetAdministrationRole` |
| Execution role in EVERY target (SELF_MANAGED) | Without it, instances are INOPERABLE | `aws iam get-role --role-name AWSCloudFormationStackSetExecutionRole` |
| Target accounts or OU IDs | Deployment scope | account list or `aws organizations list-organizational-units-for-parent` |
| Regions list | Account × region pairs | list of enabled regions |
| Capabilities identified | IAM/macro templates require ack | CAPABILITY_IAM / CAPABILITY_NAMED_IAM / CAPABILITY_AUTO_EXPAND |
| Parameters resolved | Must be supplied at create-stack-set | key/value list |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Permission model (SELF_MANAGED vs SERVICE_MANAGED)

The first decision is the permission model. **Immutable after
StackSet creation** — to switch, delete and recreate.

**Decision tree:**

```text
Organizations enabled + CloudFormation trusted access?
├── YES → targets are OUs (auto-include future accounts)?
│    ├── YES → SERVICE_MANAGED  (recommended)
│    │         No per-account roles; new accounts auto-deployed
│    │         Management account SKIPPED (use standalone stack)
│    └── NO  → SERVICE_MANAGED with OrganizationalUnitIds=["r-xxx"]
└── NO  → SELF_MANAGED  (only option without Organizations)
          Admin role + execution role in EVERY target account
          New accounts NOT auto-included
```

| Feature | SELF_MANAGED | SERVICE_MANAGED |
|---|---|---|
| Organizations required | No | Yes (trusted access) |
| Per-account role setup | Yes (admin + execution roles) | No (service-linked role) |
| Auto-include new accounts | No — call `create-stack-instances` | Yes — new accounts in OU auto-deployed |
| Management account deployment | Supported | NOT supported (skipped) |
| Account filtering | AccountIds list | OrganizationalUnitIds + AccountFilterType (INTERSECTION/DIFFERENCE/TARGET/UNION) |
| Best for | Single-account multi-region, non-Org | Any org using AWS Organizations |

## Step 2 — Deployment targets (OUs, accounts, regions)

Deployment targets define WHICH accounts and WHICH regions receive
stack instances. The format depends on the permission model.

**SERVICE_MANAGED deployment targets:**

```bash
aws cloudformation create-stack-instances \
  --stack-set-name my-stackset \
  --deployment-targets OrganizationalUnitIds="ou-xxx-xxxxxxxx" \
  --regions "us-east-1,us-west-2,eu-west-1" \
  --operation-preferences FailureTolerancePercentage=5,MaxConcurrentPercentage=20
```

- `OrganizationalUnitIds`: OU IDs (ou-xxx-xxxxxxxx) or root (r-xxx).
  Deploys to ALL accounts under the OU.
- `AccountFilterType`: INTERSECTION (default), DIFFERENCE (exclude),
  TARGET (only), UNION — combined with `AccountFilters` for
  fine-grained targeting (e.g., deploy to OU but exclude sandboxes).

**SELF_MANAGED deployment targets:**

```bash
aws cloudformation create-stack-instances \
  --stack-set-name my-stackset \
  --deployment-targets Accounts="111111111111,222222222222,333333333333" \
  --regions "us-east-1,eu-west-1" \
  --operation-preferences FailureToleranceCount=1,MaxConcurrentCount=5
```

- `Accounts`: explicit list of 12-digit account IDs. Each account
  MUST have the execution role pre-provisioned.

**Regions** apply to all target accounts (cartesian product).
RegionConcurrencyType controls PARALLEL vs SEQUENTIAL (with
RegionOrder) region deployment.

**Common mistake:** targeting root (r-xxx) with SERVICE_MANAGED and
being surprised the management account is skipped. It is ALWAYS
skipped in SERVICE_MANAGED.

## Step 3 — StackSet creation (template, parameters, capabilities)

Once the permission model is decided and the template is ready,
create the StackSet.

```bash
aws cloudformation create-stack-set \
  --stack-set-name my-stackset \
  --template-body file://template.yaml \
  --parameters ParameterKey=ExampleParam,ParameterValue=value \
  --capabilities CAPABILITY_IAM \
  --permission-model SERVICE_MANAGED \
  --auto-deployment Enabled=true,RetainStacksOnAccountRemoval=false \
  --managed-execution Active=true
```

For templates >51,200 bytes, use `--template-url https://s3.amazonaws.com/my-bucket/templates/template.yaml` instead of `--template-body`.

**Key flags:**
- `--permission-model`: SELF_MANAGED (default) or SERVICE_MANAGED.
  IMMUTABLE after creation.
- `--administration-role-arn` / `--execution-role-name`: required
  for SELF_MANAGED.
- `--auto-deployment`: SERVICE_MANAGED only. `Enabled=true` auto-
  deploys to new accounts in targeted OUs.
  `RetainStacksOnAccountRemoval=false` deletes stacks when accounts
  leave the OU (recommended for hygiene).
- `--managed-execution Active=true`: enables StackSet drift
  detection and automatic reconciliation of targeting changes
  (SERVICE_MANAGED only).
- `--capabilities`: required if the template creates IAM resources
  (`CAPABILITY_IAM`) or uses macros (`CAPABILITY_AUTO_EXPAND`).
  Without it, every operation fails with `InsufficientCapabilities`.

## Step 4 — Operation preferences (failure tolerance, concurrency)

Operation preferences are passed on EVERY create/update/delete-
stack-instances and update-stack-set call. They are NOT stored on
the StackSet itself.

| Field | Type | Description |
|---|---|---|
| `FailureToleranceCount` | integer | Instances that can fail before halting |
| `FailureTolerancePercentage` | integer (0-100) | Same as count, as % of total |
| `MaxConcurrentCount` | integer | Instances deployed in parallel |
| `MaxConcurrentPercentage` | integer (0-100) | Same as count, as % of total |
| `RegionConcurrencyType` | SEQUENTIAL \| PARALLEL | Regions sequential or parallel |
| `RegionOrder` | list of region names | Order when SEQUENTIAL |

**Rules:** Count and Percentage are mutually exclusive per operation.
RegionOrder is ignored when PARALLEL. Defaults:
FailureToleranceCount=0, MaxConcurrentCount=1, SEQUENTIAL.

**Production recommendation:**

```bash
--operation-preferences \
  FailureTolerancePercentage=5,MaxConcurrentPercentage=20,\
  RegionConcurrencyType=SEQUENTIAL,RegionOrder=["us-east-1","us-west-2","eu-west-1"]
```

Tolerates 5% failure, runs 20% of accounts in parallel per region,
deploys regions sequentially starting with us-east-1.

## Step 5 — Stack instances (deploy, managed execution)

A stack instance is the deployment of the StackSet's template in
ONE account × ONE region. After create-stack-set, NO instances
exist yet — you must call create-stack-instances.

**Create stack instances (SERVICE_MANAGED):**

```bash
aws cloudformation create-stack-instances \
  --stack-set-name my-stackset \
  --deployment-targets OrganizationalUnitIds="ou-xxx-xxxxxxxx" \
  --regions "us-east-1,us-west-2,eu-west-1" \
  --operation-preferences FailureTolerancePercentage=5,MaxConcurrentPercentage=20
```

**Wait for operation:**

```bash
aws cloudformation describe-stack-set-operation \
  --stack-set-name my-stackset \
  --operation-id <operation-id>
```

Status: `RUNNING` → `SUCCEEDED` | `FAILED` | `STOPPING` | `STOPPED`.

**Common mistake:** calling create-stack-set and assuming the
template is deployed. It is NOT. create-stack-set registers the
StackSet; create-stack-instances is a separate call that actually
deploys.

## Step 6 — Drift detection (per-instance and StackSet-level)

StackSets support TWO levels of drift detection.

**Per-instance drift (always available):**

```bash
aws cloudformation detect-stack-set-drift \
  --stack-set-name my-stackset \
  --operation-preferences MaxConcurrentCount=5

aws cloudformation describe-stack-set \
  --stack-set-name my-stackset \
  --query StackSet.DriftStatus
```

`StackSet.DriftStatus` values: `DRIFTED` | `IN_SYNC` |
`NOT_CHECKED` | `UNKNOWN`.

**StackSet-level drift (managed execution, SERVICE_MANAGED):**

For SERVICE_MANAGED StackSets with `ManagedExecution.Active=true`,
CloudFormation continuously detects drift on stack instances and
auto-reconciles drifted instances on the next `update-stack-set`.

**Manual drift remediation:**

```bash
# Reset a drifted instance (deletes and recreates)
aws cloudformation update-stack-instances \
  --stack-set-name my-stackset \
  --deployment-targets Accounts="111111111111" \
  --regions "us-east-1"
```

**Common mistake:** enabling `ManagedExecution.Active=true` without
realizing it AUTO-RECONCILES drift on the next update. If your
workflow depends on manual drift review, set `Active=false` and run
`detect-stack-set-drift` on a schedule.

## Step 7 — StackSets vs nested stacks

A common architecture decision: when to use a StackSet vs nested
stacks vs a single flat stack.

| Criterion | Single stack | Nested stacks | StackSet |
|---|---|---|---|
| Scope | 1 account, 1 region | 1 account, 1 region | N accounts, M regions |
| Use case | Simple resource group | Decompose a complex template | Fan out one template across accounts/regions |
| Composition | Inline resources | `AWS::CloudFormation::Stack` children | One template, parameterized |
| Update model | One stack | Parent updates propagate to children | `update-stack-set` propagates to all instances |
| Best for | Single-environment deployments | Templates >500 resources (CFN limit) | Multi-account governance, baseline deployments |

**Rule of thumb:**
- 1 account, 1 region → single stack or nested stacks.
- N accounts OR M regions for the SAME template → StackSet.
- Compose a large template within one account → nested stacks.
- Deploy a baseline (GuardDuty, Config, IAM roles) across the org →
  StackSet.

**Anti-pattern:** using a StackSet to deploy a complex multi-
resource application that should be a single nested-stack
deployment. StackSets are for fan-out of the SAME template, not
for composition.

## Step 8 — Update and delete operations

**Update the StackSet (propagates to all instances):**

```bash
aws cloudformation update-stack-set \
  --stack-set-name my-stackset \
  --template-url https://s3.amazonaws.com/my-bucket/template-v2.yaml \
  --parameters ParameterKey=ExampleParam,ParameterValue=newvalue \
  --operation-preferences FailureTolerancePercentage=5,MaxConcurrentPercentage=20
```

- `update-stack-set` propagates the new template/parameters to ALL
  existing stack instances, respecting operation preferences.
- For SERVICE_MANAGED + managed execution, drifted instances are
  auto-reconciled as part of the update.

**Delete specific instances:**

```bash
aws cloudformation delete-stack-instances \
  --stack-set-name my-stackset \
  --deployment-targets Accounts="111111111111" \
  --regions "us-east-1" \
  --retain-stacks false
```

`--retain-stacks false` (default) deletes underlying stacks; `true`
orphans them (remain but unmanaged).

**Delete the StackSet (after all instances removed):**

```bash
aws cloudformation delete-stack-set --stack-set-name my-stackset
```

You MUST delete all stack instances first (`delete-stack-instances`),
then delete the StackSet. Calling `delete-stack-set` while instances
exist fails.

## Step 9 — Recent features

**Recent AWS features (2023-2026):**

- **StackSet-level drift detection (2023-2024):** StackSets expose
  `DriftStatus` at the StackSet level (aggregated from instances).
  Combined with managed execution, drift is detected continuously
  and reconciled automatically on updates.

- **Managed execution for SERVICE_MANAGED (2023-2024):**
  `ManagedExecution.Active=true` enables continuous drift detection
  AND automatic reconciliation of account-targeting changes (when
  accounts join/leave a targeted OU, instances are created/deleted
  automatically).

- **Detailed status for stack instances (2023-2024):**
  `StackInstance.ComprehensiveStatus` exposes granular status
  (`PENDING`, `RUNNING`, `SUCCEEDED`, `FAILED`, `CANCELLED`,
  `INOPERABLE`, `OUTDATED`) per instance.

- **AccountFilterType for SERVICE_MANAGED (2023-2024):**
  `INTERSECTION` (default), `DIFFERENCE`, `TARGET`, `UNION` —
  enables fine-grained targeting within an OU (e.g., "deploy to OU
  but exclude sandbox accounts").

- **CloudFormation IaC generator (2023-2025):** Generates
  CloudFormation templates from existing AWS resources. Use
  `create-generated-template` to scan resources and produce a
  template deployable via StackSets. Useful for "lift and shift"
  of existing resources into a StackSet-managed baseline.

- **Per-resource drift detail (2024-2025):** `detect-stack-resource-
  drift` now surfaces the specific resource that drifted, not just
  the instance-level status.

- **RegionConcurrencyType PARALLEL (2024-2025):** Operation
  preferences support `RegionConcurrencyType=PARALLEL` for faster
  multi-region deployments.

## NEVER do these things

1. **NEVER create a StackSet as SELF_MANAGED and later try to
   switch it to SERVICE_MANAGED.** The permission model is
   immutable. You must delete the StackSet (which deletes all
   stack instances) and recreate. Decide once, up front.

2. **NEVER call `create-stack-set` and assume the template is
   deployed.** create-stack-set only registers the StackSet. You
   must call `create-stack-instances` separately to actually deploy
   to target accounts and regions.

3. **NEVER target the organization root with SERVICE_MANAGED and
   expect the management account to be deployed.** SERVICE_MANAGED
   always skips the management account. Use a SELF_MANAGED StackSet
   or a standalone stack for it.

4. **NEVER omit `--capabilities` if the template creates IAM
   resources.** Without `CAPABILITY_IAM` (or
   `CAPABILITY_NAMED_IAM` for named roles), every operation fails
   with `InsufficientCapabilities`. Macros require
   `CAPABILITY_AUTO_EXPAND`.

5. **NEVER disable Organizations trusted access while
   SERVICE_MANAGED StackSets exist.** Disabling trusted access
   makes all SERVICE_MANAGED StackSets read-only — you cannot
   create, update, or delete instances until trusted access is
   re-enabled. Treat it as a permanent dependency.

6. **NEVER use default operation preferences for large fan-outs.**
   Defaults halt on any failure and deploy one account at a time —
   too conservative for >10 accounts. Tune explicitly per operation.

7. **NEVER call `delete-stack-set` while stack instances still
   exist.** Run `delete-stack-instances` for every targeted
   account/region first, then delete the StackSet.

8. **NEVER assume `ManagedExecution.Active=true` only detects
   drift.** It also AUTO-RECONCILES drifted instances on the next
   `update-stack-set`. For manual drift review, set `Active=false`.

9. **NEVER set both FailureToleranceCount and
   FailureTolerancePercentage on the same operation** (same for
   MaxConcurrentCount vs MaxConcurrentPercentage). They are mutually
   exclusive.

10. **NEVER use a StackSet where nested stacks are the right tool.**
    StackSets are for fan-out across accounts/regions. For
    decomposing a large template within ONE account and region, use
    nested stacks.

11. **NEVER assume templates >51,200 bytes can be passed inline.**
    Upload to S3 and use `--template-url`.

## Output format

```text
STACKSET: <stack-set-name> (template: <template-source>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Permission model: SELF_MANAGED | SERVICE_MANAGED
  [✓|✗] Organizations trusted access: Enabled (SERVICE_MANAGED) | N/A (SELF_MANAGED)
  [✓|✗] Administration role: <admin-role-arn> (SELF_MANAGED) | N/A (SERVICE_MANAGED SLR)
  [✓|✗] Execution role: <execution-role-name> in each target account (SELF_MANAGED) | N/A (SERVICE_MANAGED SLR)
  [✓|✗] Template source: <file-path | s3-url> (<size>; S3 required if >51200 bytes)
  [✓|✗] Capabilities: CAPABILITY_IAM | CAPABILITY_NAMED_IAM | CAPABILITY_AUTO_EXPAND | NONE
  [✓|✗] Parameters: <key=value list>
  [✓|✗] Deployment targets: <OU IDs | account list> with AccountFilterType=<type>
  [✓|✗] Regions: <region list> (RegionConcurrencyType=<SEQUENTIAL|PARALLEL>, RegionOrder=<order>)
  [✓|✗] Operation preferences: FailureTolerance<Count|Percentage>=<n>, MaxConcurrent<Count|Percentage>=<n>
  [✓|✗] Auto-deployment: Enabled=true, RetainStacksOnAccountRemoval=false (SERVICE_MANAGED) | N/A
  [✓|✗] Managed execution: Active=true|false (drift detection + auto-reconcile on update)
  [✓|✗] Drift detection: detect-stack-set-drift scheduled | managed-execution continuous
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws cloudformation describe-stack-set --stack-set-name <name>
  aws cloudformation list-stack-instances --stack-set-name <name> --output table
  aws cloudformation describe-stack-set-operation --stack-set-name <name> --operation-id <op-id>
  aws organizations list-aws-service-access-for-organization --service-principal cloudformation.amazonaws.com  # SERVICE_MANAGED
```

### Worked example — SERVICE_MANAGED StackSet for an OU across 3 regions

```text
STACKSET: baseline-iam-roles (template: s3://my-bucket/templates/baseline-iam.yaml)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Permission model: SERVICE_MANAGED
  [✓] Organizations trusted access: Enabled
  [✓] Administration role: N/A (SERVICE_MANAGED SLR: AWSServiceRoleForCloudFormationStackSetsOrgNS)
  [✓] Execution role: N/A (SERVICE_MANAGED SLR assumed via trusted access)
  [✓] Template source: s3://my-bucket/templates/baseline-iam.yaml (18,432 bytes)
  [✓] Capabilities: CAPABILITY_IAM
  [✓] Parameters: Environment=production, AuditRoleArn=arn:aws:iam::111111111111:role/audit
  [✓] Deployment targets: OrganizationalUnitIds=ou-abc-12345678 (all accounts under Security OU)
  [✓] Regions: us-east-1, us-west-2, eu-west-1 (RegionConcurrencyType=SEQUENTIAL, RegionOrder=[us-east-1,us-west-2,eu-west-1])
  [✓] Operation preferences: FailureTolerancePercentage=5, MaxConcurrentPercentage=20
  [✓] Auto-deployment: Enabled=true, RetainStacksOnAccountRemoval=false
  [✓] Managed execution: Active=true (drift detection + auto-reconcile)
  [✓] Drift detection: managed-execution continuous
  [✓] Tags: Owner=platform, CostCenter=infra
VERIFICATION_COMMANDS:
  aws cloudformation describe-stack-set --stack-set-name baseline-iam-roles
  aws cloudformation list-stack-instances --stack-set-name baseline-iam-roles --output table
  aws organizations list-aws-service-access-for-organization --service-principal cloudformation.amazonaws.com
```

## Error handling

### `StackInstance` status is `INOPERABLE`
- **SELF_MANAGED:** the execution role is missing or has a broken
  trust policy in that target account. Verify the role exists in
  the target account.
- **SERVICE_MANAGED:** an SCP is blocking CloudFormation in that
  account, or the account was removed from the OU. Verify OU
  membership: `aws organizations list-parents --child-id <account>`.

### `InvalidOperationException` on create-stack-set
- **SERVICE_MANAGED:** Organizations trusted access is not enabled.
  Run: `aws organizations enable-aws-service-access --service-principal cloudformation.amazonaws.com`.

### `InsufficientCapabilities` error
- Template creates IAM/macros but `--capabilities` was not passed.
  Add `CAPABILITY_IAM` (or `CAPABILITY_NAMED_IAM`, `CAPABILITY_AUTO_EXPAND`).

### StackSet drift status is `DRIFTED` and not reconciling
- **SERVICE_MANAGED + managed execution:** ensure
  `ManagedExecution.Active=true` and trigger `update-stack-set`.
- **SELF_MANAGED or managed execution off:** run
  `detect-stack-set-drift`, then `update-stack-instances` to reset.

## Domain

AWS CloudOps / CloudFormation StackSet Multi-Account Multi-Region
Provisioning & Governance.

## AWS documentation

- **StackSets User Guide** — https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/what-is-cfnstacksets.html
- **Self-managed permissions** — https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stacksets-prereqs-self-managed.html
- **Service-managed permissions** — https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stacksets-orgs-enable-trusted-access.html
- **Operation preferences** — https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stacksets-concepts.html#stacksets-concepts-operation-preferences
- **StackSet drift detection** — https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stacksets-drift.html
- **Managed execution** — https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stacksets-managed-execution.html
- **IaC generator** — https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/generate-IaC.html
