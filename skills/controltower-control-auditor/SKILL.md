---
name: controltower-control-auditor
description: >-
  Audits AWS Control Tower landing-zone state, enabled controls (preventive,
  detective, proactive), guardrail enforcement integrity, and account-factory
  baseline health. Detects landing-zone drift, disabled mandatory controls,
  SCP and Config-Rule modifications, missing execution roles, and Config
  recorder gaps. Emits a deterministic verdict (DRIFT | DISABLED_CONTROL |
  CONFIG_GAP | OK) per OU or landing zone with enumerated findings and CLI
  remediation. Use when reviewing Control Tower posture, checking guardrail
  enforcement, auditing landing-zone drift, validating control enablement, or
  inspecting account-factory baselines before governance reviews.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline classification of Control Tower
  audit snapshots. Live-account audits use aws controltower
  list-enabled-controls, aws controltower get-enabled-control, aws
  organizations list-policies, and aws configservice
  describe-config-recorders (AWS CLI v2, SSO or key-based credentials).
keywords:
  - Control Tower
  - landing zone
  - guardrails
  - controls
  - SCP
  - preventive controls
  - detective controls
  - proactive controls
  - control drift
  - landing zone drift
  - account factory
  - AWSControlTowerExecutionRole
  - mandatory controls
  - strongly recommended controls
  - organizational units
  - governance
  - compliance
tags: [control-tower, governance, landing-zone, guardrails, scp, config-rules, compliance, audit]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Governance
  verdict_shape: "DRIFT | DISABLED_CONTROL | CONFIG_GAP | OK"
  when_to_use: >-
    Reviewing Control Tower governance posture, checking for landing-zone
    drift, auditing guardrail enforcement, validating mandatory control
    enablement, inspecting account-factory baselines, or verifying Config
    recorder health across managed accounts.
  activation_triggers:
    - "audit control tower"
    - "check landing zone drift"
    - "control tower guardrails"
    - "enabled controls status"
    - "control drift detection"
    - "account factory baseline"
    - "mandatory controls disabled"
    - "SCP drift control tower"
    - "config recorder gap"
    - "AWSControlTowerExecutionRole missing"
  invocation_schema: >-
    Input: either (a) a Control Tower audit snapshot (landing-zone state,
    enabled-controls list, SCP verification, Config recorder status, account-
    factory info), OR (b) a landing-zone identifier or OU ARN for live-account
    audit. Output: deterministic LANDING_ZONE/OU/VERDICT/REASON/FINDINGS/
    REMEDIATION block, where VERDICT ∈ {DRIFT, DISABLED_CONTROL, CONFIG_GAP,
    OK, ERROR}.
---

# Control Tower Control Auditor

## Mindset

**One-line takeaway:** a control showing `ENABLED` in Control Tower does NOT
mean it is enforcing — the underlying SCP may be modified, the Config Rule
may be deleted, or the Config recorder may be silently off. The audit must
cross-reference the enforcement mechanism, not trust the Control Tower
registry state alone.

Control Tower is the governance backbone of an AWS Organization. It deploys
guardrails as three control types — preventive (SCP-based), detective
(Config-Rule-based), and proactive (CloudFormation-hook-based) — across OUs.
- **DRIFT** is the highest-severity verdict because it is **silent**: the
  control appears enabled but enforcement is broken. An operator staring at
  the console sees nothing wrong.
- **DISABLED_CONTROL** is visible: a mandatory control is FAILED or absent.
  Someone can see and act on it.
- **CONFIG_GAP** is a supporting-infrastructure failure (Config recorder off,
  execution role missing) that silently degrades detective controls.

## Quick reference — verdict thresholds

| Condition | Verdict | Step |
|---|---|---|
| Landing zone drift detected (StackSet modified) | **DRIFT** | Step 1 |
| Landing zone state FAILED | **DRIFT** | Step 1 |
| Enabled control: SCP content modified outside CT | **DRIFT** | Step 2 |
| Enabled control: Config Rule deleted for detective control | **DRIFT** | Step 2 |
| Enabled control: CloudFormation hook removed for proactive control | **DRIFT** | Step 2 |
| Mandatory control with status FAILED or missing from enabled list | **DISABLED_CONTROL** | Step 3 |
| Config recorder disabled in any managed account | **CONFIG_GAP** | Step 4 |
| Config aggregation to audit account broken | **CONFIG_GAP** | Step 4 |
| AWSControlTowerExecutionRole missing or trust policy broken | **CONFIG_GAP** | Step 5 |
| Account Factory baseline StackSet instances missing | **CONFIG_GAP** | Step 6 |
| All controls ENABLED + SUCCEEDED, no drift, Config healthy | **OK** | Step 7 |

## Pre-flight: landing zone metadata gate

Before evaluating individual controls, classify the landing zone itself.
Several attributes short-circuit the audit.

| Attribute | Value | Effect |
|---|---|---|
| Landing zone state | `ACTIVE` | Proceed with full audit. |
| Landing zone state | `PROCESSING` | An update or operation is in progress. Flag as operational risk but proceed if controls are stable. |
| Landing zone state | `FAILED` | The last landing zone operation failed — controls may be partially deployed. Jump to Step 1 → **DRIFT**. |
| Landing zone drift status | `DRIFTED` | Baseline StackSets have been modified. Jump to Step 1 → **DRIFT**. |
| Organization features | `ALL_FEATURES` required | If SCPs are NOT enabled at the org root, preventive controls cannot deploy. Flag as **CONFIG_GAP**. |
| Landing zone version | `< 3.0` | Legacy landing zone. Newer mandatory controls may be absent from the catalog. Note as operational risk. |

**If the audit snapshot is malformed** (missing enabled-controls list, missing
landing zone state), output:

```text
LANDING_ZONE: <name>
VERDICT: ERROR
REASON: Audit snapshot is incomplete — cannot classify without enabled-controls list and landing-zone state.
REMEDIATION: Collect data with: aws controltower list-enabled-controls --targetIdentifier <ou-arn>, aws controltower get-landing-zone --landing-zone-identifier <id>.
```

## Process — Classification logic (apply in order, aggregate worst)

### Step 0: Expert knowledge — non-obvious Control Tower behaviors

Each of these changes a verdict if ignored:

- **Mandatory controls CANNOT be disabled through the Control Tower API.**
  The `disable-control` API returns `ValidationException` for mandatory
  controls. A mandatory control showing FAILED or absent from the enabled list
  means the landing zone was modified outside Control Tower (SCP removed via
  Organizations API, StackSet instance deleted, or a failed enable-control
  operation). This is not a user choice — it is a landing-zone integrity break.

- **SCP modification does NOT change the control's status in Control Tower.**
  If someone edits the SCP content via `aws organizations update-policy`, the
  Control Tower control STILL shows `SUCCEEDED`. Only a drift detector run
  catches the mismatch — and it is **periodic**, not real-time. A drifted
  preventive control can appear healthy for hours. The audit MUST
  cross-reference the actual SCP content against the expected baseline.

- **Detective controls silently die when Config is disabled.** There is no
  error, no alert. The Config Rule simply stops evaluating. Control Tower
  shows the control as `ENABLED`. The only signal is the absence of Security
  Hub findings — which looks like "everything is compliant" (a dangerous false
  positive). Always check `describe-config-recorders` independently.

- **AWSControlTowerExecutionRole is the ONLY management path into member
  accounts.** Control Tower assumes this role to deploy StackSets, enable new
  controls, and update baselines. If the role is deleted or its trust policy
  is modified to remove `controltower.amazonaws.com`, the account becomes
  **stranded** — Control Tower cannot manage it. The failure surfaces only
  when the next control operation is attempted (enable/disable/update), not
  immediately.

- **Landing zone upgrades FAIL on drifted StackSets.** When AWS releases a new
  landing zone version, the upgrade applies CloudFormation updates to the
  managed StackSets. If StackSet instances have drift (template or parameter
  mismatch), the update skips or fails on those instances. Landing-zone drift
  must be remediated BEFORE any upgrade attempt.

- **Preventive controls do NOT protect the management account.** SCPs are
  evaluated per API call, but the management account (formerly master account)
  is exempt from SCP evaluation by design. A preventive control enabled at the
  root OU does not restrict the management account. This is expected — the
  management account is governed by IAM policies and root MFA, not by SCPs.

- **Proactive controls are bypassed by direct API calls.** Proactive controls
  are implemented as CloudFormation hooks. If a resource is created via direct
  SDK call (not through CloudFormation), the proactive control is not
  evaluated. Terraform and CDK are safe (they synthesize to CloudFormation),
  but raw `aws ec2 run-instances` bypasses the hook entirely.

- **Detective findings flow through Security Hub.** Control Tower detective
  controls emit compliance results via Security Hub. If Security Hub is
  disabled in the audit account or a member account, findings are lost even
  though Config Rules continue evaluating. The control shows ENABLED but the
  output channel is broken.

- **Config aggregation to the audit account is a single dependency.** Control
  Tower configures an AWS Config aggregator in the audit account pulling from
  all managed accounts. If the aggregator is deleted, centralized detective
  visibility is lost — local Config Rules in member accounts still run, but
  the audit account cannot aggregate or report. The control shows ENABLED but
  the governance view is blind.

- **Control operations can get stuck.** `aws controltower
  list-control-operations` shows enable/disable/update history. A control
  operation stuck in `IN_PROGRESS` for more than 30 minutes usually indicates
  a stuck CloudFormation stack or a missing execution role in the target
  account. Treat a stuck operation as a partial-disable — the control may not
  be enforcing.

### Step 1: Landing zone drift (highest priority — silent enforcement break)

Evaluate landing-zone-level drift first. This is higher priority than
individual control drift because a drifted landing zone affects ALL controls
and ALL managed accounts.

**Landing zone drift signals:**
- Landing zone drift status is `DRIFTED`.
- Baseline StackSets (`AWSControlTowerBP`, `AWSControlTowerSecurityResources`,
  `AWSControlTowerLoggingResources`) show stack-instance drift.
- Landing zone state is `FAILED` (the last setup or update operation failed —
  controls may be partially deployed).

If any of these are true, classify as **DRIFT** and note the drift source. Do
not proceed to Step 2 for individual controls unless the landing-zone drift
is isolated to specific accounts — in that case, audit unaffected OUs
separately.

### Step 2: Control-level drift (enforcement mechanism modified)

For each control with `Status: SUCCEEDED`, verify the underlying enforcement
mechanism is intact:

**Preventive controls (SCP-backed):**
- The SCP named `AWSControlTowerGuardrail<ControlName>` must be attached to
  the target OU.
- The SCP content must match the expected Control Tower baseline. If the
  content hash differs, the SCP was modified outside Control Tower → **DRIFT**.
- If the SCP is absent from the OU (detached via Organizations API), the
  preventive control is not enforcing → **DRIFT**.

**Detective controls (Config-Rule-backed):**
- The Config Rule named `AWSControlTower<ControlName>` must exist in each
  managed account under the OU.
- If the Config Rule is deleted in any account → **DRIFT**.
- If the Config Rule exists but its scope (trigger) has been modified →
  **DRIFT**.

**Proactive controls (CloudFormation-hook-backed):**
- The CloudFormation hook must be registered in each managed account.
- If the hook is removed → **DRIFT**.

### Step 3: Mandatory control enforcement

For each mandatory control expected on the target OU:

- **Status: SUCCEEDED** → control is enforcing. OK for this dimension.
- **Status: FAILED** → the enable-control operation failed; the SCP/Config
  Rule was not deployed → **DISABLED_CONTROL**. This is a landing-zone
  integrity break because mandatory controls cannot be disabled through the
  API — a FAILED status means the deployment mechanism broke.
- **Missing from the enabled-controls list entirely** → the control was
  removed via an out-of-band operation (SCP deleted, StackSet instance
  removed) → **DISABLED_CONTROL**.
- **Status: IN_PROGRESS for > 30 minutes** → the operation is stuck; treat
  as not-enforcing → **DISABLED_CONTROL**.

**Mandatory vs strongly recommended vs elective:** only flag DISABLED_CONTROL
for mandatory and strongly recommended controls. An elective control that is
disabled is a governance note, not a verdict driver — the operator chose to
disable it.

### Step 4: Config service health

Detective controls depend on AWS Config. If Config is unhealthy, detective
controls silently stop evaluating — the most dangerous failure mode.

- **Config recorder disabled** in any managed account → **CONFIG_GAP**.
  `aws configservice describe-config-recorders` returns
  `recordingGroup: {}` or `status.recording: false`.
- **Config aggregation to audit account broken** → **CONFIG_GAP**. Check
  `aws configservice describe-configuration-aggregators` for the audit
  account aggregator — if missing or failing, centralized detective visibility
  is lost.
- **Config delivery channel broken** → **CONFIG_GAP**. If the delivery S3
  bucket is deleted or the delivery role is missing, Config records changes
  but cannot deliver them for evaluation.

### Step 5: Execution role health

Control Tower deploys and updates resources in managed accounts by assuming
`AWSControlTowerExecutionRole`.

- **Role missing in any managed account** → **CONFIG_GAP**. The account is
  stranded — Control Tower cannot deploy StackSets or enable new controls.
- **Trust policy modified** (no longer trusts `controltower.amazonaws.com` from
  the management account) → **CONFIG_GAP**. Same effect as missing.
- **Role permissions modified** (inline policy removed or tightened) →
  **CONFIG_GAP**. Control Tower operations may partially fail depending on
  which permissions are missing.

### Step 6: Account Factory baseline health

Each managed account receives baseline CloudFormation stacks from Control
Tower's StackSets:

- **StackSet `AWSControlTowerBP` instances missing** → **CONFIG_GAP**. The
  account lacks the baseline IAM roles, S3 buckets, and Lambda functions that
  controls depend on.
- **Stack instances with drift** (template or parameter mismatch) → already
  caught by Step 1 as landing-zone drift. Do not double-report.

### Step 7: Aggregation — worst finding wins

The final verdict is the **maximum severity** across all findings, where
DRIFT > DISABLED_CONTROL > CONFIG_GAP > OK:

```text
verdict = max(landing_zone_drift, control_drift, control_disabled, config_gap, execution_role_gap, baseline_gap)
```

If no findings are produced, the verdict is **OK**.

## Output format (per landing zone or OU)

```text
LANDING_ZONE: <landing-zone name or id>
OU: <ou-arn, or "ALL" for landing-zone-level audit>
VERDICT: DRIFT | DISABLED_CONTROL | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and step number>
FINDINGS:
  - [DRIFT] <finding description (Step N)>
  - [CONFIG_GAP] <finding description (Step N)>
  - [OK] <dimension that passed>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

### Worked example — preventive control with SCP drift

```text
LANDING_ZONE: production-landing-zone
OU: arn:aws:organizations::111111111111:ou/o-abcd/ou-workloads
VERDICT: DRIFT
REASON: Preventive control AWS-GR_RESTRICTED_COMMON_PORTS shows SUCCEEDED but
the backing SCP was modified outside Control Tower — the Deny on port 22 (SSH)
was removed, allowing inbound SSH despite the guardrail (Step 2).
FINDINGS:
  - [DRIFT] SCP "AWSControlTowerGuardrailRestrictedCommonPorts" content
    mismatch: Deny on port 22 removed (Step 2)
  - [OK] Config recorder enabled in all managed accounts
  - [OK] AWSControlTowerExecutionRole present in all accounts
REMEDIATION:
  1. Restore the SCP from the Control Tower baseline:
     aws controltower update-enabled-control --controlIdentifier <arn>
     --parameters '[...]' (re-applies the canonical SCP)
  2. OR re-deploy the SCP via Control Tower by disabling and re-enabling the
     control:
     aws controltower disable-control --controlIdentifier <arn> --targetIdentifier <ou-arn>
     aws controltower enable-control --controlIdentifier <arn> --targetIdentifier <ou-arn>
  3. Audit CloudTrail for `organizations:UpdatePolicy` events on the SCP to
     identify who modified it.
```

## Anti-Patterns — NEVER

- NEVER trust a control's `SUCCEEDED` status as proof of enforcement. SCPs
  can be modified after deployment without Control Tower detecting it in real
  time. Always cross-reference the enforcement mechanism (SCP content, Config
  Rule existence) against the expected baseline.

- NEVER treat a `FAILED` mandatory control as an intentional disable. Mandatory
  controls cannot be disabled through the Control Tower API — a FAILED status
  means the deployment mechanism broke (SCP deployment failed, StackSet stack
  failed, execution role missing). It is a landing-zone integrity break, not a
  governance choice.

- NEVER assume the absence of Security Hub findings means "all compliant."
  If the Config recorder is disabled, detective controls silently stop
  evaluating. Zero findings may mean zero evaluation, not zero violations.

- NEVER skip checking `AWSControlTowerExecutionRole` in member accounts. This
  role is the ONLY access path Control Tower has. A missing role silently
  strands the account — no new controls can be enabled, no baselines updated.
  The failure surfaces only on the next operation attempt.

- NEVER attempt a landing-zone upgrade when drift is detected. The upgrade
  applies CloudFormation updates to StackSet instances. Drifted instances may
  cause the upgrade to fail or skip those accounts. Remediate drift first,
  then upgrade.

- NEVER confuse Control Tower detective controls with standalone Config
  conformance packs. A conformance pack deployed independently does not have
  Control Tower lifecycle management — it will not appear in
  `list-enabled-controls` and cannot be enabled/disabled via Control Tower.
  They are separate governance layers.

- NEVER assume SCPs protect the management account. The management account is
  exempt from SCP evaluation by design. A preventive control at the root OU
  does not restrict the management account. This is expected behavior, not a
  gap.

- NEVER treat a proactive control as a complete guardrail. Proactive controls
  are CloudFormation hooks — they only evaluate resources deployed through
  CloudFormation. Direct API calls, SDK scripts, and console actions bypass
  the hook entirely. Proactive controls supplement but do not replace
  preventive controls.

- NEVER ignore the Config aggregation layer. Control Tower deploys an
  aggregator in the audit account that pulls Config data from all managed
  accounts. If the aggregator is deleted, the audit account loses centralized
  visibility even though local Config Rules still run. The control shows
  ENABLED but the governance view is blind.

- NEVER recommend manually editing the SCP or StackSet backing a Control Tower
  control. Always remediate through the Control Tower API
  (disable-control + enable-control, or update-enabled-control) so the
  lifecycle is tracked and the drift detector resets.

- NEVER classify a strongly recommended or elective control in DISABLED state
  as DISABLED_CONTROL. Those control categories are intentionally optional.
  Flag them as governance notes but do not drive the verdict from optional
  controls.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (enable-control, disable-control, update-enabled-control), emit:
  `CONFIRM: About to <action> on control <arn> targeting OU <ou-arn>. This
  affects enforcement for <N> accounts. Proceed? (yes/no)`
- **Snapshot the current state** before remediation:
  `aws controltower list-enabled-controls --targetIdentifier <ou-arn> > /tmp/ct-baseline-$(date +%s).json`
- **For disable + re-enable (drift remediation):** disable-control removes the
  SCP from the OU. During the window between disable and re-enable, the
  preventive control is NOT enforcing. Schedule this during a maintenance
  window and minimize the gap.
- **Verify the execution role exists** in all target accounts before issuing
  enable-control. If the role is missing, the operation will fail after
  several minutes of CloudFormation retries.
- **Check for in-progress operations** on the target OU:
  `aws controltower list-control-operations --filter targetIdentifier=<ou-arn>`.
  Control Tower does not support concurrent operations on the same OU —
  stacking enable/disable calls produces `ConflictException`.

## Remediation guidance

### For DRIFT — landing-zone drift (Step 1)

1. Identify the drifted StackSet(s) via CloudFormation drift detection:
   `aws cloudformation detect-stack-set-drift --stack-set-name AWSControlTowerBP`.
2. Remediate through Control Tower, NOT through direct StackSet/SCP edits:
   `aws controltower update-landing-zone --landing-zone-identifier <id>
   --landing-zone-version <latest>`. This re-applies the canonical baseline.
3. If the update fails (due to resource conflicts), engage AWS Support —
   manual StackSet repair is error-prone and may corrupt the landing zone.
4. After remediation, verify drift status is clear before scheduling any
   landing-zone version upgrade.

### For DRIFT — control-level drift (Step 2)

1. **Preventive (SCP modified):** disable and re-enable the control to
   re-deploy the canonical SCP:
   `aws controltower disable-control --controlIdentifier <arn> --targetIdentifier <ou-arn>`
   then
   `aws controltower enable-control --controlIdentifier <arn> --targetIdentifier <ou-arn>`
2. **Detective (Config Rule deleted):** same disable/re-enable cycle. Control
   Tower re-deploys the Config Rule via StackSet.
3. **Proactive (hook removed):** same disable/re-enable cycle.
4. Audit CloudTrail for the out-of-band modification: search for
   `organizations:UpdatePolicy`, `config:DeleteConfigRule`, or
   `cloudformation:DeregisterType` events from non-Control-Tower principals.
5. **IMPORTANT:** During the disable window, the control is NOT enforcing.
   For preventive controls, this opens a policy gap. Schedule during a
   maintenance window and verify completion promptly.

### For DISABLED_CONTROL — mandatory control failed or missing (Step 3)

1. Check the control operation history for the failure reason:
   `aws controltower list-control-operations --filter controlIdentifier=<arn>,targetIdentifier=<ou-arn>`
2. Common failure causes: execution role missing in target account, SCP
   quota exceeded (max SCPs per OU), StackSet deployment conflict.
3. Fix the root cause, then retry:
   `aws controltower enable-control --controlIdentifier <arn> --targetIdentifier <ou-arn>`
4. If the control cannot be enabled due to quota, detach an elective SCP to
   free a slot. Control Tower has a quota of approximately 300 controls per
   OU (preventive + detective combined).

### For CONFIG_GAP — Config recorder disabled (Step 4)

1. Re-enable Config in the affected account:
   `aws configservice start-configuration-recorder --configuration-recorder-name default`
2. Verify the delivery bucket exists and the delivery role has permissions:
   `aws configservice describe-delivery-channels`.
3. If the aggregation is broken, recreate the aggregator in the audit account:
   `aws configservice put-configuration-aggregator ...`

### For CONFIG_GAP — execution role missing (Step 5)

1. The role must be recreated from the Account Factory baseline. The simplest
   method is to trigger a StackSet instance update:
   `aws cloudformation update-stack-instances --stack-set-name AWSControlTowerBP
   --accounts <account-id> --regions <region>`
2. The trust policy must allow:
   `"Service": "controltower.amazonaws.com"` with `sts:AssumeRole`.
3. Verify after recreation:
   `aws iam get-role --role-name AWSControlTowerExecutionRole`

### For OK

1. No remediation required for the current posture.
2. Recommend periodic drift checks (weekly at minimum) — Control Tower drift
   detection is periodic, not real-time.
3. Verify the landing zone version is current:
   `aws controltower get-landing-zone` and compare `latestAvailableVersion`.

## Recent AWS features (2024-2026)

- **Control Tower extensible controls (2024-2025):** Control Tower now supports enabling third-party and custom detective controls beyond the built-in guardrails. Auditors should inventory all enabled controls (built-in + extensible) and verify that preventive controls are not silently overridden by SCP modifications.
- **Landing Zone version updates (v3.3+, 2024-2025):** Each Landing Zone version adds new mandatory controls and SCP updates. Auditors should verify that the landing zone version is current — outdated versions may lack controls for newly launched AWS services.
- **External governance (2024):** Control Tower can now be managed programmatically via APIs and CloudFormation. Auditors should verify that API-driven changes to controls are tracked via CloudTrail and that drift detection covers programmatic modifications.
- **Proactive controls:** Control Tower introduced proactive controls that validate resource configurations before deployment. Auditors should verify that proactive controls are enabled for critical resource types.

## Domain

AWS CloudOps / Control Tower Governance & Compliance.
