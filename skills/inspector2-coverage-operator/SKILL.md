---
name: inspector2-coverage-operator
description: Operates Amazon Inspector v2 coverage across an AWS Organization or single account — enables / disables Inspector per account and region, manages EC2 coverage (SSM agent, deep inspection), ECR coverage (image scanning, rescan on push), Lambda coverage (code scanning, dependencies), surfaces coverage gaps (uncovered resources, SSM-missing instances, disabled regions), configures delegated admin for org-wide coverage, and operates the latest capabilities (Lambda code vulnerability scanning, SBOM export, EC2 deep inspection, ECR enhanced scan). Runs deterministic pre-checks (delegated admin, members, region activation, SSM online, ECR config, Lambda eligibility), emits the exact inspector2:Enable / Disable / UpdateOrganizationConfiguration CLI behind a CONFIRM gate, and verifies coverage post-apply. Emits a verdict (READY | BLOCKED | COMPLETED). Use when enabling Inspector, diagnosing coverage gaps, configuring delegated admin, exporting SBOMs, or rolling out Lambda code scanning.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline plan classification. Live-account operations use aws inspector2 enable, disable, update-organization-configuration, describe-organization-configuration, list-coverage, list-members, batch-get-member-ec2-deep-inspection-state, update-ec2-deep-inspection-configuration, list-usage-totals, batch-update-ec2-deep-inspection-state, list-filters, enable-delegated-admin-account...
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '4'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Security
  task_type: operate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY | BLOCKED | COMPLETED
  when_to_use: Enabling Inspector v2 per account or region, configuring delegated admin for Organizations-wide coverage, diagnosing EC2 coverage gaps (SSM agent missing, deep inspection not enabled), ECR scanning coverage (rescan-on-push, enhanced scan), Lambda function code vulnerability scanning enablement, exporting SBOMs for audit, or verifying that 100% of in-scope resources are covered.
  activation_triggers: enable Inspector, disable Inspector, Inspector v2 coverage, EC2 scanning coverage, ECR scanning coverage, Lambda scanning coverage, Lambda code vulnerability, Inspector delegated admin, Inspector member accounts, Inspector organization scan, Inspector coverage gap, SSM agent missing Inspector, deep inspection EC2, EC2 deep inspection, SBOM export, software bill of materials, Inspector enable region, batch update EC2 deep inspection
  invocation_schema: 'Input: either (a) an Inspector operation intent (enable, disable, enable-delegated-admin, update-org-config, associate-member, update-ec2-deep-inspection, enable-lambda-code-scan, configure-ecr-rescan, export-sbom, diagnose-coverage) with target account/region, resource scope, and scan types (EC2 / ECR / Lambda / Member); OR (b) a live coverage report from `aws inspector2 list-coverage` for diagnosis. Output: deterministic OPERATION/VERDICT/PRE_CHECKS/STEPS/POST_VERIFY block per operation, where VERDICT is one of READY, BLOCKED, COMPLETED.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Amazon Inspector v2, Inspector, vulnerability scanning, EC2 scanning, ECR scanning, Lambda scanning, code vulnerability, SBOM export, software bill of materials, deep inspection, SSM agent, coverage gap, delegated admin, AWS Organizations, member account, network reachability, package vulnerability, container image scanning, Inspector delegated admin, Inspector coverage
  tags: aws-inspector2, security, operate, vulnerability-scanning, ec2-coverage, ecr-coverage, lambda-coverage, delegated-admin, sbom-export, code-vulnerability, organizations, ssm-agent
---

# Inspector v2 Coverage Operator

## What this skill does

Executes Amazon Inspector v2 coverage operations correctly and safely —
enable/disable Inspector per account and region, configure delegated
admin for Organizations, manage EC2 coverage (deep inspection, SSM
agent enrollment), ECR coverage (rescan-on-push, enhanced scan
frequency), Lambda coverage (function code + dependency scanning),
export SBOMs, and diagnose coverage gaps. Runs deterministic
pre-checks before any state-changing CLI, emits the exact
`inspector2:*` CLI sequence behind a CONFIRM gate, and verifies
coverage state after apply. Every operation surfaces the resource
type (EC2 / ECR / Lambda), the scan type, and the org-vs-standalone
mode so the operator knows the scope.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **§ Quick reference** | Verdict thresholds + pre-check priority + coverage baselines | Before any operation |
| **§ Mindset** | Org mode vs standalone, resource type matrix, SSM coupling | Understanding the coverage model |
| **§ Pre-flight** | Delegated admin + member + region activation gate | Before executing any CLI |
| **§ Process** | Per-operation planning: enable, delegated admin, member, EC2, ECR, Lambda, SBOM, diagnose | When choosing which operation |
| **§ Common patterns** | Enable org-wide, EC2 deep inspection, ECR rescan, Lambda code scan, SBOM export | Boilerplate lookup |
| **§ Output format** | Structured output template with VERDICT, COMMANDS, POST_VERIFY | Formatting the response |
| **§ Anti-Patterns** | NEVER list — common mistakes | Review before risky operations |

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `BLOCKED` | One or more pre-checks failed (account not in Organizations, region not opt-in, delegated admin already set to another account, SSM agent offline, member not associated, ECR in a region Inspector disabled, Lambda layer without scan permission) | List failures, do NOT execute |
| `READY` | All pre-checks passed; awaiting CONFIRM gate | Emit exact CLI sequence, wait for operator yes |
| `COMPLETED` | Operation applied and post-verification passed (Inspector status ENABLED for the resource types in the target region, member ACTIVE, deep inspection activated, Lambda code scan enabled, SBOM export COMPLETED) | Emit describe output, coverage count, gap list |

**Priority order for pre-checks (all must pass for READY):**

1. **Delegated admin state** — `describe-organization-configuration`
   returns whether the org is configured for auto-enable. If
   `autoEnable` is `false`, individual member enable is required.
2. **Account membership** — for `enable` on a member account, the
   account must be in the Organizations root/OU and associated
   (`list-members` returns `relationshipStatus: ENABLED`).
3. **Region opt-in** — the region must be Inspector-supported and
   opt-in.
4. **Resource-type scan eligibility** — EC2 requires SSM agent
   (online within 30 min); ECR requires the repository in a
   region where ECR scanning is enabled; Lambda requires a supported
   runtime (Python, Node.js, Java, Docker).
5. **Delegated admin uniqueness** — only one delegated admin per
   org; `enable-delegated-admin-account` against a non-delegated
   account BLOCKS.
6. **Deep inspection state** —
   `batch-get-member-ec2-deep-inspection-state` must show `ACTIVE`
   for deep inspection to scan package inventory. The agent must
   have the SSM association `AmazonInspector-ManageAWSAgent`.
7. **ECR rescan-on-push** — without `scanOnPush: true`, images are
   only scanned on `start-image-scan`.
8. **Lambda code scan permission** — Lambda layers require the
   Inspector principal `lambda:GetLayerVersion`.

**Coverage baselines (2026):**
- New EC2 instance with SSM agent online: appears in `list-coverage`
  within ~15-30 minutes after enable.
- New ECR image with `scanOnPush: true`: scan completes in 1-5 min.
- New Lambda function in supported runtime: code scan completes in
  5-30 min after first invocation or manual trigger.
- SBOM export: minutes (single account/region) to hours (org-wide).

## Mindset

Three Inspector v2 realities drive every operation:

- **Org mode and standalone mode are mutually exclusive.** Once
  delegated admin is configured, individual member enable/disable is
  performed BY THE DELEGATED ADMIN ACCOUNT, not by the member itself.
  Enabling Inspector from a member under org mode returns
  `ConflictException`. Verify `describe-organization-configuration`
  before any member-level operation.

- **Resource-type coverage is independent.** EC2, ECR, and Lambda
  coverage are toggled separately at the org level
  (`autoEnable.ec2/ecr/lambda`). `update-organization-configuration`
  sets defaults for new member accounts; existing members keep their
  state. A frequent mistake is enabling EC2 at the org level and
  assuming ECR and Lambda auto-enable — they don't.

- **Deep inspection requires SSM agent + association.** Standard EC2
  scanning runs the Inspector agent via SSM; deep inspection adds
  package-level inventory via the SSM association
  `AmazonInspector-ManageAWSAgent`. Without that association `ACTIVE`,
  deep inspection silently no-ops even if
  `update-ec2-deep-inspection-configuration` succeeded.

## Pre-flight: delegated admin + member + region activation gate

`describe-organization-configuration` returns the org-level Inspector
state including `autoEnable`, `maxAccountLimitReached`, and the
delegated admin account ID.

Probe commands moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand before live-account execution.

**Malformed input:** emit `VERDICT: ERROR` with reason and remediation.

Moved verbatim to [references/error-handling.md](references/error-handling.md).
Load on demand when a pre-check fails or a resource shows a coverage gap.

## Process — operation planning (apply in order)

### Step 0: Expert knowledge — non-obvious Inspector behaviors

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand for expert behaviors, edge cases, and recent features.

### Step 1: Pre-check gate — BLOCKED if any check fails

Run ALL pre-checks. If ANY fails, verdict is BLOCKED with failures
in PRE_CHECKS. Do NOT execute.

**For ALL operations:**
1. Region is Inspector-supported and opt-in.
2. Caller IAM role holds the required `inspector2:*` permission.
3. Account is in Organizations (org-mode operations) OR is a
   standalone account (non-org operations).

**For enable (single account / region):**
4. `describe-organization-configuration` returns
   `autoEnable: false` for the resource type OR the account is
   standalone.
5. The account is not already ENABLED for the resource type in the
   target region.
6. EC2: at least one SSM-managed instance exists in the region.
7. ECR: at least one repository exists.
8. Lambda: at least one function in a supported runtime exists.

**For enable-delegated-admin:**
4. Caller is the Organizations management account.
5. No existing delegated admin (or being replaced explicitly).
6. Target account is a member of the org and in the same root.

**For update-organization-configuration:**
4. Caller is the existing delegated admin account.
5. New `autoEnable` values do not disable already-ENABLED members
   (existing members keep their state).
6. `maxAccountLimitReached: false`.

**For associate-member:**
4. Caller is the delegated admin.
5. Target account is in the org.
6. Target account is not already associated.

**For update-ec2-deep-inspection-configuration:**
4. Caller is the delegated admin (org-level) or a standalone admin.
5. SSM association `AmazonInspector-ManageAWSAgent` is ACTIVE on
   target instances.
6. Target instances have `PingStatus: Online` from SSM.

**For enable-lambda-code-scan (via update-org-config or per-account):**
4. Functions in a supported runtime (python3.x, nodejs.x,
   java11/17/21, provided.al2023).
5. Inspector principal has `lambda:GetLayerVersion` on layers used.
6. Functions in regions where Lambda scanning is supported.

**For export-sbom:**
4. Target S3 bucket grants `s3:PutObject` to the Inspector service
   principal.
5. KMS key `Enabled` and grants `kms:GenerateDataKey` to Inspector.
6. Bucket and key in the same region as the export scope.
7. No concurrent SBOM export for the same scope (one active export
   per account/region/format).

**For diagnose-coverage:**
5. `list-coverage` returns the coverage report for the region.
6. `batch-get-account-status` returns the per-resource-type state.
7. `list-members` (org-mode) returns associated member states.

### Step 2: READY — emit operation plan

Emit `VERDICT: READY` with exact CLI sequence + CONFIRM gate:
- Exact AWS CLI command with all flags populated.
- Expected duration (15-30 min for EC2 first scan, 1-5 min for ECR,
  5-30 min for Lambda).
- Expected side-effects (Inspector agent installed via SSM, member
  ENABLED, deep inspection scanning begins, SBOM export to S3).
- CONFIRM gate prompt.

### Step 3: Execute behind CONFIRM gate

- **MANDATORY CONFIRMATION GATE.** Before any state-changing CLI
  (`enable`, `disable`, `enable-delegated-admin-account`,
  `update-organization-configuration`, `associate-member`,
  `update-ec2-deep-inspection-configuration`,
  `batch-update-ec2-deep-inspection-state`,
  `start-sbom-export`, `cancel-sbom-export`), emit CONFIRM prompt.
  Do NOT execute until confirmed.
- Snapshot current state via `batch-get-account-status --output json
  > /tmp/inspector2-$(date +%s).json` for enable/disable;
  `describe-organization-configuration` for org-config changes;
  `list-sbom-export` for SBOM operations.
- Execute the CLI.
- For org-level changes, validate propagation to member accounts
  (`batch-get-member-ec2-deep-inspection-state` within 5-10 min).

### Step 4: Post-verification — COMPLETED

ALL checks must pass for `COMPLETED`:
1. For enable: `batch-get-account-status` returns `state: ENABLED`
   for the resource type in the target region.
2. For delegated admin: `list-delegated-admin-accounts` returns the
   new account with `status: ENABLED`.
3. For org-config: `describe-organization-configuration` returns
   the updated `autoEnable` values.
4. For member associate: `list-members` returns the new account
   with `relationshipStatus: ENABLED`.
5. For EC2 deep inspection:
   `batch-get-member-ec2-deep-inspection-state` returns `ACTIVE`.
6. For Lambda code scan: `list-coverage` returns Lambda resources
   with `scanType: LAMBDA_CODE` and `scanStatus: COMPLETED` (5-30
   min after enable).
7. For SBOM export: `list-sbom-export` returns `reportId` with
   `status: COMPLETED`; verify the S3 object exists in the bucket.

If ANY verification fails, emit `VERDICT: ERROR` — do not claim COMPLETED.

## Common patterns (boilerplate)

Moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when formatting a secondary example or CLI pattern.

## Diagnostic flows

Moved verbatim to [references/error-handling.md](references/error-handling.md).
Load on demand when a pre-check fails or a resource shows a coverage gap.

## Output format (per operation)

```text
OPERATION: <enable | disable | enable-delegated-admin | update-org-config | associate-member | update-ec2-deep-inspection | enable-lambda-code-scan | configure-ecr-rescan | export-sbom | diagnose-coverage>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <account-id / region / instance-id / repository / function / sbom-report-id>
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. <CLI command with flags populated>
  2. <wait command>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
STATE: <Inspector enable state per resource type, member relationship status, deep inspection state, SBOM export status>
NOTES: <org-mode vs standalone, resource-type matrix, scan-type coverage, SSM agent / S3 / KMS caveats, cost impact>
```

### Worked example — enable EC2 + ECR + Lambda (READY)

```text
OPERATION: enable
VERDICT: READY
TARGET: account 111111111111 region us-east-1
PRE_CHECKS:
  - [PASS] Region us-east-1 is Inspector-supported and opt-in
  - [PASS] describe-organization-configuration returns autoEnable:
    false for all resource types (standalone enable is valid)
  - [PASS] batch-get-account-status returns state: DISABLED for EC2,
    ECR, and LAMBDA in us-east-1
  - [PASS] Caller IAM role holds inspector2:Enable
  - [PASS] 12 running EC2 instances, 4 ECR repositories, 8 Lambda
    functions in supported runtimes
STEPS:
  1. CONFIRM: About to enable Inspector v2 for EC2, ECR, and Lambda
     in account 111111111111 region us-east-1. This will install the
     Inspector agent on 12 EC2 instances via SSM, enable ECR scanning
     on 4 repositories, and start Lambda code scanning on 8
     functions. Cost accrues per scan per resource per region.
     Proceed? (yes/no)
  2. aws inspector2 enable --account-ids 111111111111 \
       --client-token 1723305600 \
       --resource-types EC2 ECR LAMBDA \
       --region us-east-1
POST_VERIFY:
  - (pending execution)
  - batch-get-account-status returns state: ENABLED for EC2, ECR,
    LAMBDA within ~5 minutes
  - First EC2 scan within 15-30 min; ECR within 1-5 min; Lambda
    within 5-30 min
STATE: pending — Inspector ENABLED within ~5 minutes
NOTES:
  - Standalone enable (autoEnable is false at org level or org-mode
    not configured).
  - Resource-type coverage is independent — each scans on its own
    cadence.
  - Cost accrues per scan per resource per region. Verify budget
    via list-usage-totals before broad enablement.
```

### Worked example — enable delegated admin (READY)

Moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when formatting a secondary example or CLI pattern.

### Worked example — diagnose EC2 coverage gap (BLOCKED)

Moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when formatting a secondary example or CLI pattern.

## STRICT output contract

### Required output structure

Every response MUST begin with this block — no preamble, no
conversational opening:

```text
OPERATION: <enable | disable | enable-delegated-admin | update-org-config | associate-member | update-ec2-deep-inspection | enable-lambda-code-scan | configure-ecr-rescan | export-sbom | diagnose-coverage>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <account-id / region / instance-id / repository / function / sbom-report-id>
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. CONFIRM: About to <operation> on target <target> in account <account> region <region>. This will <consequence>. Proceed? (yes/no)
  2. <exact CLI command with every flag populated — no placeholders>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
STATE: <Inspector enable state per resource type, member relationship status, deep inspection state, SBOM export status>
NOTES: <org-mode vs standalone rationale, scan-type caveats, SSM/S3/KMS prerequisites, cost impact>
```

### FORBIDDEN output patterns

- NEVER start with conversational preamble ("Let me analyze…") — the VERDICT block is the FIRST line, always. Use uppercase verdict values only (`READY`, `BLOCKED`, `COMPLETED`).
- NEVER omit PRE_CHECKS — every pre-check must appear with `[PASS]` or `[FAIL]` and a specific reason for each failure.
- NEVER enable Inspector for EC2 without surfacing the SSM-agent dependency and the cost-per-scan-per-resource caveat in NOTES.
- NEVER list a CLI command with placeholder flags in a READY plan — every flag must be populated with actual values from the input data.
- NEVER claim COMPLETED without every POST_VERIFY line showing `[PASS]`, and never omit the CONFIRM gate as the first STEPS entry for state-changing operations.

## Anti-Patterns — NEVER do these things

- NEVER call `enable-delegated-admin-account` from a member account. The call must come from the Organizations management account; member accounts receive `AccessDeniedException`. If a delegated admin already exists, the call returns `ConflictException` — surface the existing delegated admin account in NOTES.
- NEVER assume `autoEnable: true` at the org level flips existing members. Auto-enable applies ONLY to NEW member accounts. Existing members retain their pre-update state; audit and remediate each separately via `list-members`.
- NEVER enable EC2 deep inspection without verifying the SSM association `AmazonInspector-ManageAWSAgent` is `ACTIVE`. Deep inspection silently no-ops on instances without the association.
- NEVER start an SBOM export without verifying the target S3 bucket grants `s3:PutObject` and the KMS key grants `kms:GenerateDataKey` to the Inspector service principal. The export silently fails with `status: FAILED`.
- NEVER diagnose coverage from a single region's `list-coverage` and conclude org-wide coverage. Inspector coverage is per-region; aggregation requires AWS Security Hub or a custom aggregator. List regions covered and NOT covered in NOTES.

## Pre-flight safety checks

- **MANDATORY CONFIRMATION GATE** before any state-changing CLI.
- **Snapshot before enable/disable** (`batch-get-account-status
  --output json > /tmp/inspector2-$(date +%s).json`) for diff
  against post-apply state.
- **Verify SSM agent online** before EC2 coverage operations.
- **Verify S3 + KMS** for SBOM export before `start-sbom-export`.
- **Estimate cost** via `list-usage-totals` before broad enablement.

## Expert heuristic: standalone vs org-mode enable

```
ORG-MODE (org has delegated admin)
   ├─ Enabling from a member account?
   │    └─ YES → BLOCKED — delegated admin must perform enable
   ├─ Enabling from delegated admin?
   │    └─ YES → use update-organization-configuration
   │         (autoEnable applies to NEW members only)
   │         (existing members keep state; remediate per-member)
   ├─ Need to enable a specific resource type NOW?
   │    └─ Use enable --account-ids <list> --resource-types <list>
   │         from the delegated admin account
STANDALONE (no org, or org-mode not configured)
   ├─ Use enable --account-ids <self> --resource-types <list>
   ├─ ec2 / ecr / lambda independent — set each explicitly
   └─ No delegated admin, no member association
```

**Per-resource-type prerequisites:**

| Resource Type | What to check |
|---|---|
| `EC2` standard | SSM agent installed, `PingStatus: Online`, instance profile with `AmazonSSMManagedInstanceCore` |
| `EC2` deep | Above + SSM association `AmazonInspector-ManageAWSAgent` ACTIVE |
| `ECR` basic | Repository in a supported region; native ECR CVE list |
| `ECR` enhanced | `ecr-enhanced` scan type; Inspector agent pulls deep package inventory |
| `LAMBDA_FUNCTION` | Supported runtime (python/node/java/provided.al2023); layers grant `lambda:GetLayerVersion` |
| `LAMBDA_CODE` | Enabled alongside LAMBDA resource type; scans code + dependencies |

**Coverage polling intervals:** EC2 standard 15-30 min; EC2 deep
30-60 min after SSM association ACTIVE; ECR 1-5 min (basic) / 5-15 min
(enhanced); Lambda code 5-30 min after enable.

ALWAYS pair enable operations with a follow-up coverage audit (24-48
hours later) — operators frequently enable Inspector and assume
coverage is at 100%, missing the SSM-agent-offline instances.

## Recent AWS features (2024-2026)

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand for expert behaviors, edge cases, and recent features.

## References (load on demand)

- [references/worked-examples.md](references/worked-examples.md) — secondary worked examples and CLI boilerplate patterns moved from this SKILL.md
- [references/error-handling.md](references/error-handling.md) — pre-flight attribute effects and per-resource diagnostic flows moved from this SKILL.md
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — live-account pre-flight command listing moved from this SKILL.md
- [references/advanced-patterns.md](references/advanced-patterns.md) — Step-0 expert knowledge and recent AWS features moved from this SKILL.md
- [references/ecr-ec2-lambda-coverage-guide.md](references/ecr-ec2-lambda-coverage-guide.md) — per-resource-type scan mechanics and coverage gaps
- [references/org-mode-and-delegated-admin-guide.md](references/org-mode-and-delegated-admin-guide.md) — org-mode enablement and delegated admin semantics

## Domain

AWS CloudOps / Amazon Inspector v2 Coverage and Enablement Operations.

## AWS documentation

- **Amazon Inspector User Guide** — https://docs.aws.amazon.com/inspector/latest/user/inspector_v2.html
- **Inspector Enablement** — https://docs.aws.amazon.com/inspector/latest/user/enable-disable-inspector.html
- **Inspector Organizations** — https://docs.aws.amazon.com/inspector/latest/user/designating-admin.html
- **Inspector Coverage** — https://docs.aws.amazon.com/inspector/latest/user/findings.html
- **EC2 Deep Inspection** — https://docs.aws.amazon.com/inspector/latest/user/ec2-deep-inspection.html
- **ECR Scanning** — https://docs.aws.amazon.com/inspector/latest/user/ecr-scanning.html
- **Lambda Scanning** — https://docs.aws.amazon.com/inspector/latest/user/lambda-scanning.html
- **SBOM Export** — https://docs.aws.amazon.com/inspector/latest/user/sbom-export.html
- **API Reference** — https://docs.aws.amazon.com/inspector/latest/user/inspector-v2-api.html
- **AWS CLI inspector2 reference** — https://docs.aws.amazon.com/cli/latest/reference/inspector2/
- **Inspector Pricing** — https://aws.amazon.com/inspector/pricing/

