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

**Live-account pre-flight (skip if offline plan):**
1. `inspector2 describe-organization-configuration` — capture
   `autoEnable.ec2/ecr/lambda`, `maxAccountLimitReached`.
2. `inspector2 list-delegated-admin-accounts` — capture delegated
   admin account ID(s).
3. `inspector2 list-members --only-associated` — capture members
   with `relationshipStatus: ENABLED`.
4. `inspector2 list-coverage` — coverage report per region.
5. `ec2 describe-instances --filters "Name=instance-state-name,Values=running"`
   — running instances for EC2 gap analysis.
6. `ssm describe-instance-information` — SSM agent `PingStatus:
  Online` (deep inspection requires online SSM).
7. `ecr describe-repositories` + `ecr put-image-scanning-configuration`
   — rescan-on-push state per repository.
8. `lambda list-functions` — runtime for Lambda scan eligibility.

**Malformed input:** emit `VERDICT: ERROR` with reason and remediation.

| Attribute | Effect on operation |
|---|---|
| `autoEnable.ec2: false` at org level | New members do NOT auto-enable EC2. Update org config or enable per-member. |
| `maxAccountLimitReached: true` | Org hit the member cap (default 1000). BLOCKED until members disassociated. |
| Delegated admin mismatch | `enable-delegated-admin-account` for a non-delegated account returns `ConflictException`. BLOCKED. |
| `relationshipStatus: DISABLED` for a member | Member in the org but Inspector disabled. ENABLE required via delegated admin. |
| `PingStatus: ConnectionLost` (EC2) | Deep inspection cannot scan. BLOCKED for deep-inspection operations. |
| `scanOnPush: false` (ECR) | Images scanned only on manual `start-image-scan`. INFO. |
| Lambda runtime `provided.al2023` | Supported but custom layers may need explicit `lambda:GetLayerVersion` grant. INFO. |

## Process — operation planning (apply in order)

### Step 0: Expert knowledge — non-obvious Inspector behaviors

- **Org-mode enable is one-way for member accounts.** Once a member
  is associated (`relationshipStatus: ENABLED`), the member CANNOT
  self-disable; only the delegated admin can disassociate it.
- **Auto-enable only applies to NEW member accounts.** When the org
  is configured with `autoEnable`, existing members keep their
  pre-existing state. Audit each member via
  `batch-get-member-ec2-deep-inspection-state` and `list-members`.
- **EC2 deep inspection is opt-in on top of standard scanning.**
  Standard covers network reachability and OS-level CVEs; deep adds
  package inventory via the SSM association
  `AmazonInspector-ManageAWSAgent`. Instances opt out via
  `batch-update-ec2-deep-inspection-state`.
- **ECR rescan-on-push is configured at the repository.** Update
  ECR `put-image-scanning-configuration` with `scanOnPush: true`.
  `ecr-enhanced` pulls the Inspector agent for deep package
  inventory; `basic` uses the native ECR CVE list.
- **Lambda code vulnerability scanning requires runtime support.**
  Supported (2026): `python3.x`, `nodejs.x`, `java11/17/21`,
  `provided.al2023`. Unsupported (`dotnet`, `ruby`, `go` on
  `provided.al2`) are silently skipped. Inspector needs
  `lambda:GetLayerVersion` to scan layers.
- **SBOM export targets S3 with a KMS key.** Asynchronous:
  `start-sbom-export` returns a `reportId`; completion lands in the
  bucket. The bucket policy must grant `s3:PutObject` and KMS key
  must grant `kms:GenerateDataKey` to the Inspector service
  principal.
- **Coverage gap analysis is region-by-region.** A resource appears
  in `list-coverage` for the region scanned. Cross-region
  aggregation requires AWS Security Hub or a custom aggregator.
- **Inspector charges by scan per resource per region.** Disabling
  unused regions avoids cost. Surface expected cost in NOTES.
- **Delegated admin must be in the same Organizations root.** OU
  moves do not revoke delegation — disassociation requires explicit
  `disable-delegated-admin-account` from the management account.
- **Network reachability scans run from AWS.** Inspector analyzes
  Security Groups and route tables for internet exposure. Host-agent
  scanning (standard + deep) requires the Inspector agent via SSM.
- **Lambda scanning is per version, not per alias.** `$LATEST` is
  scanned; published versions scanned once. For continuous coverage,
  re-publish on changes.
- **ECR enhanced scan is rate-limited per repository.** Concurrent
  `start-image-scan` calls are serialized. Use `scanOnPush: true`
  rather than batched manual scans for high-volume registries.

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

### Enable Inspector for EC2 + ECR + Lambda (standalone account)

```bash
aws inspector2 enable \
  --account-ids 111111111111 \
  --client-token "$(date +%s)" \
  --resource-types EC2 ECR LAMBDA \
  --region us-east-1
```

Lambda code vulnerability scanning is enabled alongside LAMBDA;
no separate flag needed.

### Configure delegated admin for Organizations-wide coverage

```bash
# From the Organizations MANAGEMENT account
aws inspector2 enable-delegated-admin-account \
  --delegated-admin-account-id 222222222222 \
  --client-token "$(date +%s)"

# From the DELEGATED ADMIN account, set auto-enable defaults
aws inspector2 update-organization-configuration \
  --auto-enable '{ec2: true, ecr: true, lambda: true}' \
  --client-token "$(date +%s)"
```

`autoEnable` applies ONLY to NEW member accounts. Existing members
keep their pre-config state.

### Associate a member account (from delegated admin)

```bash
aws inspector2 associate-member \
  --account-id 333333333333 \
  --client-token "$(date +%s)"
```

The member must already be in the org. After association,
`list-members` returns `relationshipStatus: ENABLED`.

### Enable EC2 deep inspection (org-level default)

```bash
# From the delegated admin
aws inspector2 update-organization-configuration \
  --auto-enable '{ec2: true, ecr: true, lambda: true}' \
  --ec2-deep-inspection-configuration '{
    "enabled": true,
    "packageNameFilters": ["kernel", "openssl"]
  }'
```

Instances opt in/out via `batch-update-ec2-deep-inspection-state
--instance-ids i-aaa i-bbb --scan-state ENABLED`. The SSM
association `AmazonInspector-ManageAWSAgent` must be `ACTIVE`.

### Enable ECR rescan-on-push for a repository

```bash
aws ecr put-image-scanning-configuration \
  --repository-name prod-app \
  --image-scanning-configuration scanOnPush=true \
  --region us-east-1
```

Inspector uses this setting. Without `scanOnPush: true`, Inspector
scans only on `start-image-scan`. Enhanced scans (`ecr-enhanced`)
pull the Inspector agent for deep package inventory.

### Verify Lambda code vulnerability scanning is active

```bash
aws inspector2 list-coverage \
  --filter-criteria 'RESOURCE_TYPE=_EQUALS=LAMBDA_FUNCTION' \
  --region us-east-1 \
  --output table
```

Coverage rows with `scanType: LAMBDA_CODE` are scanned. Functions
in unsupported runtimes (`dotnet6`, `ruby`) are absent — surface as
a gap.

### Start SBOM export (CycloneDX format)

```bash
aws inspector2 start-sbom-export \
  --report-format CYCLONEDX_1_5 \
  --s3-destination '{
    "bucketName": "inspector-sbom-prod",
    "kmsKeyArn": "arn:aws:kms:us-east-1:111111111111:key/abcd1234",
    "keyPrefix": "sbom/us-east-1/"
  }' \
  --resource-filter-criteria '{
    "accountId": [{"comparison": "EQUALS", "value": "111111111111"}],
    "resourceType": [{"comparison": "EQUALS", "value": "AWS_ECR_CONTAINER_IMAGE"}]
  }' \
  --client-token "$(date +%s)"
```

Returns a `reportId`. Poll via `list-sbom-export --report-id <id>`
until `status: COMPLETED`. The S3 object appears at
`s3://<bucket>/<keyPrefix><reportId>.json`.

## Diagnostic flows

### EC2 instance shows 0% coverage

1. `inspector2 list-coverage --filter-criteria
   'RESOURCE_ID=_EQUALS=i-0123456789abcdef0'` — capture `scanStatus`,
   `scanType`, `errorMessage`.
2. Common failures:
   - `AGENT_NOT_INSTALLED`: install the SSM agent; wait 15-30 min.
   - `AGENT_OFFLINE`: SSM agent `PingStatus: ConnectionLost`. Reboot
     the agent or instance.
   - `DEEP_INSPECTION_NOT_ACTIVE`: SSM association
     `AmazonInspector-ManageAWSAgent` missing or `Associated: false`.
     Create the association via SSM State Manager.
   - `UNSUPPORTED_OS`: rare with 2026 coverage; check release notes.
3. Remediation: install SSM agent / create association / update OS.
   Re-scan is automatic after the next scan window.

### ECR repository shows no scans

1. `ecr describe-image-scanning-configuration --repository-name <name>`
   — capture `scanOnPush`.
2. `ecr describe-images --repository-name <name> --image-ids
   imageTag=latest --query 'imageDetails[0].imageScanStatus'`.
3. Common failures:
   - `scanOnPush: false` and no manual `start-image-scan`: enable
     `scanOnPush` or run `start-image-scan`.
   - `imageScanStatus: FAILED`: image size or manifest error.
   - Region does not support `ecr-enhanced`: fall back to `basic`.
4. Remediation: `put-image-scanning-configuration` /
   `start-image-scan` / move the repository to a supported region.

### Lambda function not scanned

1. `inspector2 list-coverage --filter-criteria
   'RESOURCE_TYPE=_EQUALS=LAMBDA_FUNCTION'` — check if the function
   appears.
2. `lambda get-function-configuration --function-name <name>` —
   capture `runtime`.
3. Common failures:
   - Unsupported runtime (`dotnet6`, `ruby`): Inspector skips.
   - Layers lacking Inspector principal: add `lambda:GetLayerVersion`
     to the layer policy.
   - Function is a published version only: scan applies to `$LATEST`.
4. Remediation: switch runtime (if feasible), add layer permission,
   or accept as a known gap.

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

```text
OPERATION: enable-delegated-admin
VERDICT: READY
TARGET: delegated-admin-account-id 222222222222
PRE_CHECKS:
  - [PASS] Caller is the Organizations management account 111111111111
  - [PASS] list-delegated-admin-accounts returns no existing
    delegated admin for Inspector
  - [PASS] Target account 222222222222 is a member of the org in
    the same root
STEPS:
  1. CONFIRM: About to enable-delegated-admin-account setting
     account 222222222222 as the delegated admin. Only the
     delegated admin can manage member enable/disable afterwards.
     Proceed? (yes/no)
  2. aws inspector2 enable-delegated-admin-account \
       --delegated-admin-account-id 222222222222 \
       --client-token 1723305600
POST_VERIFY:
  - list-delegated-admin-accounts returns 222222222222 with
    status: ENABLED
  - describe-organization-configuration succeeds from the delegated
    admin account
STATE: pending — delegated admin ACTIVE within ~30 seconds
NOTES:
  - Org-mode is one-way: member accounts cannot self-disable.
  - Run update-organization-configuration separately to set
    autoEnable defaults for new member accounts.
```

### Worked example — diagnose EC2 coverage gap (BLOCKED)

```text
OPERATION: diagnose-coverage
VERDICT: BLOCKED
TARGET: account 111111111111 region us-east-1 EC2
PRE_CHECKS:
  - [PASS] batch-get-account-status returns state: ENABLED for EC2
    in us-east-1
  - [FAIL] 3 of 12 instances report AGENT_OFFLINE in list-coverage
    (i-aaa, i-bbb, i-ccc). SSM PingStatus ConnectionLost. Inspector
    requires the SSM agent online; deep inspection requires
    AmazonInspector-ManageAWSAgent ACTIVE.
  - [PASS] 9 of 12 instances report COMPLETED scan in last 24h
STEPS: (none — pre-checks failed; this is a diagnosis)
POST_VERIFY: (none)
STATE: FAILED — 3 instances offline for Inspector scanning
NOTES:
  - Remediation: install/restart the SSM agent on i-aaa, i-bbb,
    i-ccc. Verify the instance profile includes
    AmazonSSMManagedInstanceCore. Re-scan is automatic once
    PingStatus returns Online.
  - For deep inspection, verify the
    AmazonInspector-ManageAWSAgent SSM association is Associated:
    true on each instance.
```

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

- **Lambda code vulnerability scanning (2025)**: Inspector scans
  Lambda function code (Python, Node.js, Java) for CVEs in
  application dependencies; enabled via `enable --resource-types
  LAMBDA`. No separate flag is needed.
- **Inspector SBOM export (2024)**: export CycloneDX 1.5 or SPDX 2.3
  SBOM per account/region to a customer-owned S3 bucket with KMS
  encryption; `start-sbom-export` is asynchronous, status via
  `list-sbom-export`.
- **EC2 deep inspection (2024, refined 2025)**: package-level
  inventory scanning via the SSM association
  `AmazonInspector-ManageAWSAgent`; supports `packageNameFilters`.
  Instances opt in/out via `batch-update-ec2-deep-inspection-state`.
- **ECR enhanced scan (2024)**: deep package inventory beyond the
  native ECR CVE list; enabled via `ecr-enhanced` scan type.
- **Inspector for AWS Organizations (2023, refined 2024)**:
  delegated-admin model with `autoEnable` defaults; org-level
  member limit (default 1000 member accounts).
- **Inspector integration with AWS Security Hub (2025)**: findings
  auto-publish to Security Hub for cross-region and cross-account
  aggregation.
- **Inspector Network Reachability (2024)**: analyzes Security
  Group and route table state for internet exposure; no agent
  required.

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
