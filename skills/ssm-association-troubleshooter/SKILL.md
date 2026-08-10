---
name: ssm-association-troubleshooter
description: >-
  Diagnoses AWS Systems Manager (SSM) association failures via a
  systematic 5-symptom decision tree: association status Failed,
  TimedOut, instance not appearing in SSM (not managed),
  association never runs (wrong schedule or targets), and document
  execution fails mid-run. Maps each symptom to root cause via
  diagnostic commands (describe-instance-information,
  list-associations, describe-association-executions,
  describe-association-execution-targets, SSM agent logs), common
  causes (invalid parameters, document not found, S3 bucket access
  denied, SSM agent unreachable, instance offline, network
  connectivity, IAM role missing AmazonSSMManagedInstanceCore,
  cron expression wrong, tag mismatch, association enabled=False,
  rate limiting, script error, platform unsupported), and
  specific fixes. Emits ROOT_CAUSE_FOUND with a fix plan,
  NEED_MORE_INFO with the next diagnostic, or ESCALATE with the
  escalation path. Use when an SSM association is failing,
  timing out, not running, or producing errors.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). No AWS CLI required for offline diagnosis. Live-
  account troubleshooting uses aws ssm describe-instance-information,
  list-associations, describe-association, describe-association-
  executions, describe-association-execution-targets, list-association-
  versions, describe-instance-associations-status, describe-document,
  describe-activations, list-command-invocations, aws ec2 describe-
  instances, describe-instance-profile, and IAM/CloudTrail queries
  (AWS CLI v2, SSO or key-based credentials). SSM agent logs at
  /var/log/amazon/ssm/amazon-ssm-agent.log on the host.
keywords:
  - Systems Manager
  - SSM
  - SSM Association
  - association failed
  - association TimedOut
  - association never runs
  - SSM Agent
  - PingStatus
  - ConnectionLost
  - Inactive
  - AmazonSSMManagedInstanceCore
  - association execution
  - document execution
  - SSM Document
  - patch baseline
  - hybrid activation
  - SSM VPC endpoints
  - ssmmesages
  - ec2messages
  - cron expression
  - association targets
  - instance profile
  - S3 output bucket
  - rate limiting
tags: [ssm, systems-manager, management, troubleshoot, association, agent, diagnostic]
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Management
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE"
  when_to_use: >-
    Diagnosing an SSM association that is failing, timing out,
    never running, or producing errors mid-execution. Covers the
    five primary symptom categories: association status Failed,
    TimedOut, instance not appearing in SSM (unmanaged),
    association never runs (schedule/target mismatch), document
    execution fails (script/permission/platform). Use when an
    association shows red in the console, an instance is missing
    from SSM, a patch or inventory run failed, or a custom
    document run produced errors.
  activation_triggers:
    - "SSM association failed"
    - "association TimedOut"
    - "association never runs"
    - "association not running"
    - "instance not in SSM"
    - "instance not managed"
    - "SSM agent unreachable"
    - "SSM ConnectionLost"
    - "association execution failed"
    - "document execution fails"
    - "patch association failed"
    - "inventory association failed"
    - "association wrong schedule"
    - "association targets wrong"
    - "association enabled false"
    - "SSM rate limiting"
    - "IAM role missing SSM"
    - "AmazonSSMManagedInstanceCore"
    - "hybrid activation"
    - "SSM VPC endpoints"
  invocation_schema: >-
    Input: either (a) an association-id or association name with
    observed symptom (Failed / TimedOut / never-runs / document-
    error / instance-missing), optionally with execution-id, OR
    (b) live-account diagnostic output from describe-instance-
    information, describe-association-executions, etc. Output:
    deterministic DIAGNOSIS block per association — SYMPTOM/
    ROOT_CAUSE/EVIDENCE/FIX/VERDICT — where VERDICT is
    ROOT_CAUSE_FOUND (cause identified + fix actionable),
    NEED_MORE_INFO (specific next diagnostic cited), or ESCALATE
    (requires AWS Support or out-of-band action).
---

# SSM Association Troubleshooter

## Mindset

An SSM association runs only when three independent layers are healthy —
**IAM** (instance can talk to SSM), **connectivity** (instance reaches SSM
endpoints), and **agent** (SSM Agent running and current). Most association
failures are one of these three layers masquerading as an association problem.
Diagnose the layer first, then the association-specific config.

- **The 3-layer health check is the upstream gate.** If the instance is not pinging SSM (ConnectionLost, Inactive, missing from console), no association can run. Diagnose IAM, then connectivity, then agent — in that order.
- **`describe-association-executions` is the source of truth.** The console shows a status enum; the API returns detailed execution output including per-target results, error messages, and S3 output URIs.
- **Association status and document execution status are different.** `Success` association status means the document started; it does NOT mean the script inside succeeded. Always cross-reference `describe-association-execution-targets`.

## Quick navigation

| You want to... | Go to |
|---|---|
| Run the 3-layer health check first (recommended) | Step 1 |
| Diagnose association status: Failed | Step 2 |
| Diagnose association status: TimedOut | Step 3 |
| Diagnose instance not appearing in SSM | Step 4 |
| Diagnose association never runs | Step 5 |
| Diagnose document execution fails mid-run | Step 6 |
| Map symptom to root cause quickly | Appendix B |
| Avoid misdiagnosis pitfalls | Anti-Patterns |

## Critical rules at a glance

1. **Run the 3-layer health check FIRST.** Before any association-specific diagnosis, confirm: (1) IAM role has `AmazonSSMManagedInstanceCore`, (2) instance can reach SSM endpoints (`ssm.`, `ec2messages.`, `ssmmessages.`), (3) agent is running and current.
2. **Use `describe-association-executions`, not the console.** The console aggregates; the API returns per-target detail including the actual error message, S3 output URI, and execution-id.
3. **Association status `Success` does NOT mean the script succeeded.** A `Success` association status means the document orchestration started; per-target `Failed` is a separate field. Always read `describe-association-execution-targets`.
4. **Patch `Scan` vs `Install` matters.** An `AWS-ApplyPatchBaseline` association with `Operation=Scan` reports compliance but does NOT install patches. A "failing" patch association may simply be running Scan against a non-compliant host.
5. **Hybrid activations have a different diagnosis path than EC2.** `mi-*` instances are registered via activation code/ID; their IAM role comes from the activation, not an EC2 instance profile. Do not run `ec2 describe-instances` for `mi-*`.

## Pre-flight: data requirements

| Input | Source | Why |
|---|---|---|
| Association-id or name | Console / `list-associations` | Drives `describe-association-executions` |
| Observed symptom | Console status / alert | Routes to the right diagnostic branch |
| Instance-id(s) | Console / association targets | Needed for `describe-instance-information` |
| Region | Console | Required for all CLI calls |
| Execution-id (if available) | Console / API | For per-target drill-down |
| Recent CLI output (if any) | `describe-instance-information`, etc. | Speeds up diagnosis |
| SSM agent log excerpt (if any) | `/var/log/amazon/ssm/amazon-ssm-agent.log` | For agent-side errors |

**If the input is malformed** (no association-id, no instance-id, ambiguous
symptom), emit:

```text
DIAGNOSIS: <reference>
SYMPTOM: unknown
VERDICT: NEED_MORE_INFO
GAP: Cannot start diagnosis — required inputs missing.
     Re-supply: association-id or name, the observed symptom
     (Failed / TimedOut / never-runs / document-error / instance-missing),
     and at least one instance-id or target.
```

## Process — Diagnostic decision tree (apply in order)

### Step 0: Expert knowledge — non-obvious SSM behaviors

- **`describe-instance-information` only shows instances SSM already knows about.** A freshly launched EC2 instance with no IAM profile will NOT appear. Diff `ec2 describe-instances` (full set) against `ssm describe-instance-information` (managed subset) to find coverage gaps.
- **`PingStatus: Active` is heartbeat, not health.** Active only means the agent pinged SSM in the last ~5 minutes. Does NOT mean associations are running or the document can execute. Always pair with `LastPingDateTime`.
- **Association `Status` is orchestration status, not document result.** `Status: Success` means SSM started the document. Per-target `Status: Failed` (in `describe-association-execution-targets`) is where the script error lives.
- **`AWS-ApplyPatchBaseline` has two Operations: `Scan` and `Install`.** `Scan` records compliance but does not patch. A "failing" patch association may be a `Scan` correctly reporting NON_COMPLIANT.
- **`Patch Group` is a TAG, not an association property.** Case-sensitive tag key `Patch Group` (with space, capital G) links instance to baseline. Without it, instance uses default regional baseline silently.
- **`AmazonSSMManagedInstanceCore` is the modern role policy.** The deprecated `AmazonEC2RoleforSSM` lacks `ssmmessages:*` (Session Manager). A "managed" instance on legacy policy may run associations but cannot run Session Manager.
- **Hybrid activation `mi-*` instances use the activation role, not an EC2 profile.** Different remediation path than EC2.
- **Three VPC endpoints required for fully-private SSM:** `ssm`, `ssmmessages`, `ec2messages`. Missing any one produces `ConnectionLost` even with correct IAM and healthy agent.
- **SSM enforces per-instance command concurrency limit (default 1).** A second concurrent command returns `InvalidInstanceId` or `TargetNotConnected`. Diagnose as transient back-off, not coverage failure.
- **`AWS-UpdateSSMAgent` is the auto-update association.** Without it, agent only updates on instance stop/start or manual command. Missing it is root cause of most `IsLatestVersion: false` findings.
- **`scheduleExpression` uses `rate()` or `cron()`.** SSM uses AWS cron syntax requiring `?` in either day-of-month or day-of-week. `cron(0 2 * * *)` is INVALID; use `cron(0 2 * * ? *)`.
- **Targets are evaluated at execution time, not creation time.** Tag-based targets match whatever currently has the tag — retagging mid-run changes the target set silently.
- **Document parameters are validated at execution time.** A reference to a deleted parameter (e.g., an S3 bucket that no longer exists) produces `Failed` only when the association runs — not at creation.
- **Association versions are immutable; SSM keeps up to 99.** To "revert," update the document-version reference or recreate with old parameters.

### Step 1: The 3-layer SSM health check (run FIRST)

Before any association-specific diagnosis, confirm all three layers. A
failing layer invalidates all downstream diagnosis.

**Layer 1 — IAM (instance profile has AmazonSSMManagedInstanceCore):**

```bash
aws ec2 describe-instances --instance-ids <instance-id> \
  --query 'Reservations[*].Instances[*].IamInstanceProfile.Arn' --output text
aws iam list-attached-role-policies --role-name <role-name> --output text
```

For hybrid `mi-*` instances, check the activation role:
```bash
aws ssm describe-instance-information \
  --instance-information-filter-list Key=InstanceIds,ValueSet=<mi-id> \
  --query 'InstanceInformationList[*].IamRoleARN' --output text
aws ssm describe-activations --filters Key=RegistrationStatus,Values=Registered
```

**Layer 2 — Connectivity (instance can reach SSM endpoints):**

For private-subnet instances, confirm the three required VPC endpoints:
```bash
aws ec2 describe-vpc-endpoints \
  --filters Name=vpc-id,Values=<vpc-id> \
  Name=service-name,Values=com.amazonaws.<region>.ssm,com.amazonaws.<region>.ssmmessages,com.amazonaws.<region>.ec2messages \
  --query 'VpcEndpoints[*].[ServiceName,State]' --output table
```

**Layer 3 — Agent (running and current):**

```bash
aws ssm describe-instance-information \
  --instance-information-filter-list Key=InstanceIds,ValueSet=<instance-id> \
  --query 'InstanceInformationList[*].[PingStatus,LastPingDateTime,AgentVersion,IsLatestVersion,PlatformType]' --output table
```

Flags: `ConnectionLost`/`Inactive` = Layer 1 or 2 failure. `IsLatestVersion: false` = agent out of date. `LastPingDateTime` > 1 hour = flapping agent.

**If any layer fails, fix the layer FIRST.** Most association failures
resolve when coverage is restored. Specifically:
- Layer 1 fails → attach `AmazonSSMManagedInstanceCore` to instance profile (EC2) or re-activate with new role (`mi-*`).
- Layer 2 fails → deploy VPC endpoints or fix security group outbound.
- Layer 3 fails → restart agent or update via `AWS-UpdateSSMAgent`.

**On-host agent status** (if instance is reachable via SSH/SSM):
```bash
# Linux
systemctl status amazon-ssm-agent
sudo ssm-cli get-agent-connection-status --region <region>
# Windows
Get-Service AmazonSSMAgent
```

### Step 2: Diagnose association status: Failed

**Symptom:** association `Status: Failed`.

```bash
aws ssm describe-association-executions --association-id <association-id> \
  --query 'Executions[0].[ExecutionId,Status,StatusMessage,ExecutionTime]' --output table
aws ssm describe-association-execution-targets --association-id <association-id> \
  --execution-id <execution-id> \
  --query 'Targets[*].[Status,StatusMessage,ResourceId,OutputSource.S3Url]' --output table
```

Fetch detailed output from S3 if `OutputSource` is configured.

```bash
aws ssm list-association-versions --association-id <association-id> \
  --query 'AssociationVersions[*].[Version,Date,CreatedBy]' --output table
```

| Cause | Diagnostic signal | Fix |
|---|---|---|
| Invalid parameters | `StatusMessage: Invalid parameters` | Fix parameters; document schema may have changed |
| Document not found | `StatusMessage: Document does not exist` | Document deleted or name typo; recreate or fix reference |
| S3 bucket access denied | `StatusMessage: AccessDenied on s3:PutObject` | Add `s3:PutObject` for output bucket to instance role |
| Instance profile missing permissions | `StatusMessage: AccessDenied` on target API | Add required action to instance role |
| Document version drift | `StatusMessage: schema drift` | Pin document-version or update association to match |

**VERDICT:** ROOT_CAUSE_FOUND when StatusMessage + S3 output identifies a
specific cause; NEED_MORE_INFO when message is generic and S3 output is
empty (fetch agent log — Appendix A in references).

### Step 3: Diagnose association status: TimedOut

**Symptom:** association `Status: TimedOut`.

Check instance reachability NOW (the timeout may be transient): run
`describe-instance-information` for PingStatus. If `ConnectionLost`/`Inactive`,
run the 3-layer check (Step 1). If reachable, check command-level timeout via
`list-command-invocations`.

```bash
aws ssm list-command-invocations --instance-id <instance-id> \
  --query 'CommandInvocations[*].[CommandId,Status,StatusDetails]' --output table
```

| Cause | Diagnostic signal | Fix |
|---|---|---|
| SSM Agent unreachable | `PingStatus: ConnectionLost` or `Inactive` | Run 3-layer check; fix IAM, endpoints, or restart agent |
| Instance offline | `ec2 describe-instances` shows `stopped`/`terminated` | Start or recreate instance |
| Network connectivity lost | Agent unreachable but EC2 reachable; endpoints missing/SG blocking | Deploy endpoints / fix SG |
| Script hangs (deadlock, infinite loop) | Instance healthy, agent running, command never completes | Review document script; add `timeoutSeconds` |
| `ExecutionTimeout` too short | `StatusDetails: Timeout` immediately | Increase document `ExecutionTimeout` |

**VERDICT:** ROOT_CAUSE_FOUND when 3-layer check identifies a specific layer
failure or script-hang signal is clear; NEED_MORE_INFO if instance is
reachable and agent is current (fetch agent log).

### Step 4: Diagnose instance not appearing in SSM (not managed)

**Symptom:** instance missing from SSM console / Fleet Manager /
`describe-instance-information`.

Confirm the instance exists in EC2 and is running. Check for IAM instance
profile, VPC endpoints, and SSM agent status.

```bash
aws ec2 describe-instances --instance-ids <instance-id> \
  --query 'Reservations[*].Instances[*].[State.Name,LaunchTime,IamInstanceProfile.Arn]' --output table
aws ec2 describe-vpc-endpoints --filters Name=vpc-id,Values=<vpc-id> \
  --query 'VpcEndpoints[?contains(ServiceName,`.ssm.`)].[ServiceName,State]' --output table
```

| Cause | Diagnostic signal | Fix |
|---|---|---|
| No IAM instance profile | `describe-instances` returns empty `IamInstanceProfile.Arn` | Attach profile with `AmazonSSMManagedInstanceCore` |
| Profile missing `AmazonSSMManagedInstanceCore` | `list-attached-role-policies` does not include it | Attach `AmazonSSMManagedInstanceCore` |
| Legacy policy only (`AmazonEC2RoleforSSM`) | Role has deprecated policy only | Replace with `AmazonSSMManagedInstanceCore` |
| Private subnet without VPC endpoints | No `ssm.`, `ssmmessages.`, or `ec2messages.` endpoints | Deploy all three interface endpoints |
| SSM Agent not installed/running | `ssm-cli get-agent-connection-status` fails | Install agent for OS / `systemctl start amazon-ssm-agent` |
| Hybrid activation expired | `describe-activations` shows `Expired: true` | Create new activation; re-register instance |
| Instance launched < 5 min ago | Agent has not bootstrapped yet | Wait 5-10 minutes; do not flag as UNMANAGED |

### Step 5: Diagnose association never runs (wrong schedule or targets)

**Symptom:** association exists and is `Enabled` but has no executions.

Confirm association State, targets match current instances, and
schedule expression syntax is valid (AWS cron with `?` in DOM or DOW).

```bash
aws ssm describe-association --association-id <association-id> \
  --query 'AssociationDescription.[Name,State,ScheduleExpression,LastExecutionDate,NextExecutionDate]' --output table
aws ssm describe-association-executions --association-id <association-id> \
  --query 'Executions[*].[ExecutionId,Status,ExecutionTime]' --output table
```

| Cause | Diagnostic signal | Fix |
|---|---|---|
| Schedule expression wrong | Malformed `cron()` or `rate()`; both DOM and DOW set (no `?`) | Fix syntax; use `?` in one of DOM/DOW |
| Targets don't match any instance | Tag key/value mismatch; `Targets` returns empty | Fix tag values or retag instances |
| Association `State: Disabled` | `State: Disabled` on `describe-association` | `update-association-state` to `Enabled` |
| Rate-limiting | Many associations on same instance; throttling in CloudTrail | Stagger schedules; reduce concurrency |
| Targeting wrong instance-id | Typo in `Key=InstanceIds,Values=<wrong-id>` | Fix target list |

### Step 6: Diagnose document execution fails mid-run

**Symptom:** association orchestration succeeds but per-target `Status: Failed`.

```bash
aws ssm describe-association-execution-targets --association-id <association-id> \
  --execution-id <execution-id> \
  --query 'Targets[*].[Status,StatusMessage,ResourceId,OutputSource.S3Url]' --output table
# Fetch S3 output (actual script stdout/stderr)
aws s3 cp <s3-url> -
```

If `OutputSource` is empty, the instance role lacks `s3:PutObject` — verify
via `simulate-principal-policy`.

```bash
aws iam simulate-principal-policy --policy-source-arn <instance-role-arn> \
  --action-names s3:PutObject s3:GetObject \
  --resource-arns arn:aws:s3:::<output-bucket>/*
aws ssm describe-document --name <document-name> \
  --query 'Document.[LatestVersion,DefaultVersion,PlatformTypes]' --output table
```

| Cause | Diagnostic signal | Fix |
|---|---|---|
| Script error (syntax, logic) | `StandardErrorContent` shows error | Fix the document script |
| Permission denied | `AccessDenied` in script output | Add required action to instance role |
| Platform unsupported | `PlatformTypes` does not include instance OS | Use different document or extend platform support |
| Document references missing resource | `ResourceNotFound` in output | Recreate or fix reference |
| Document version drift | `DefaultVersion` changed; association pinned to old | Update association `DocumentVersion` |
| Script exceeds `timeoutSeconds` | `StatusDetails: Timeout` mid-execution | Increase timeout or split document |
| Reboot mid-script (Windows) | Script restarts instance; subsequent steps fail | Split document; use `aws:rebootInstance` explicitly |

**VERDICT:** ROOT_CAUSE_FOUND when S3 output / standard error identifies a
specific failure; NEED_MORE_INFO when output is empty (fetch SSM agent log
from the host — see references).

**SSM agent log locations:**
| OS | Path |
|---|---|
| Linux (most) | `/var/log/amazon/ssm/amazon-ssm-agent.log` |
| Linux (AL2023 / snap) | `/var/snap/amazon-ssm-agent/current/amazon-ssm-agent.log` |
| Windows | `C:\ProgramData\Amazon\SSM\Logs\amazon-ssm-agent.log` |

## Output format

```text
DIAGNOSIS: <reference>
ASSOCIATION: <association-id or name>
INSTANCE: <instance-id or "multiple-targets">
SYMPTOM: Failed | TimedOut | NotManaged | NeverRuns | DocumentError
ROOT_CAUSE: <specific cause cited>
EVIDENCE:
  - <diagnostic signal 1>
  - <diagnostic signal 2>
LAYER_CHECK:
  - IAM: <PASS | FAIL — reason>
  - Connectivity: <PASS | FAIL — reason>
  - Agent: <PASS | FAIL — reason>
FIX:
  - <action 1 with CLI snippet>
  - <action 2 ...>
VERIFICATION:
  - <command to confirm fix>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
NEXT_STEP: <if NEED_MORE_INFO, the specific next diagnostic>
ESCALATION_PATH: <if ESCALATE, the recommended path>
```

### Worked example — ROOT_CAUSE_FOUND, Failed association

```text
DIAGNOSIS: patch-association-prod
ASSOCIATION: 0123456789abcdef0123456789abcdef0123456789abcdef0
INSTANCE: i-0abc123def456789a
SYMPTOM: Failed
ROOT_CAUSE: Instance role lacks s3:PutObject on the S3 output bucket;
            association execution failed writing command output.
EVIDENCE:
  - describe-association-executions Status=Failed, StatusMessage="AccessDenied on s3:PutObject for arn:aws:s3:::ssm-output-prod/..."
  - simulate-principal-policy returned Denied for s3:PutObject on arn:aws:s3:::ssm-output-prod/*
LAYER_CHECK:
  - IAM: FAIL — instance role has AmazonSSMManagedInstanceCore but NOT s3:PutObject on ssm-output-prod
  - Connectivity: PASS — PingStatus Active, agent v3.2.x
  - Agent: PASS — IsLatestVersion true
FIX:
  - Add an inline policy granting s3:PutObject on arn:aws:s3:::ssm-output-prod/*:
    aws iam put-role-policy --role-name <instance-role> --policy-name SsmOutputPut --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":"s3:PutObject","Resource":"arn:aws:s3:::ssm-output-prod/*"}]}'
  - Re-run the association:
    aws ssm start-associations-once --association-ids 0123456789abcdef0123456789abcdef0123456789abcdef0
VERIFICATION:
  - aws ssm describe-association-executions --association-id 0123456789abcdef0123456789abcdef0123456789abcdef0 --query 'Executions[0].Status'
  - Expect: Success
VERDICT: ROOT_CAUSE_FOUND
NEXT_STEP: None
ESCALATION_PATH: None
```

### Worked example — NEED_MORE_INFO, TimedOut

```text
DIAGNOSIS: nightly-inventory-missing
ASSOCIATION: 1234567890abcdef1234567890abcdef1234567890abcdef1
INSTANCE: i-0fedcba9876543210
SYMPTOM: TimedOut
ROOT_CAUSE: Pending diagnosis — instance is reachable (PingStatus Active)
            and agent is current, but the document hangs mid-execution.
            Need SSM agent log to identify the hung plugin.
EVIDENCE:
  - describe-association-executions Status=TimedOut
  - describe-instance-information PingStatus=Active, AgentVersion=3.2.1555.0
  - list-command-invocations StatusDetails=TimedOut (no StatusMessage)
LAYER_CHECK:
  - IAM: PASS — AmazonSSMManagedInstanceCore + SSM output bucket access
  - Connectivity: PASS — PingStatus Active within last 5 min
  - Agent: PASS — IsLatestVersion true
FIX: (pending root cause)
VERIFICATION: (pending fix)
VERDICT: NEED_MORE_INFO
NEXT_STEP: Fetch the SSM agent log from the host:
  aws ssm send-command --instance-ids i-0fedcba9876543210 \
    --document-name AWS-RunShellScript \
    --parameters commands=["tail -n 200 /var/log/amazon/ssm/amazon-ssm-agent.log"]
  Then locate the plugin that produced the timeout (look for
  "documentname/gather-software-inventory" and "TimeoutExceeded").
ESCALATION_PATH: If agent log shows no plugin entry, escalate to
  AWS Support with the execution-id.
```

### Worked example — ESCALATE, NotManaged with hybrid activation

```text
DIAGNOSIS: hybrid-edge-device-missing
ASSOCIATION: 234567890abcdef234567890abcdef234567890abcdef2
INSTANCE: mi-0abc123def456789a
SYMPTOM: NotManaged
ROOT_CAUSE: Hybrid activation expired (Expired: true). The mi-* instance
            was registered under this activation; the agent can no longer
            re-authenticate.
EVIDENCE:
  - describe-instance-information returns nothing for mi-0abc123def456789a
  - describe-activations shows the activation Expired=true (expiry 2026-06-01)
LAYER_CHECK:
  - IAM: FAIL — activation role no longer exchangeable
  - Connectivity: unknown (instance not in SSM)
  - Agent: unknown (instance not in SSM)
FIX: Cannot remediate from AWS side alone — the on-prem host must
  re-register with a new activation code. Requires on-host access.
VERIFICATION: After re-registration:
  aws ssm describe-instance-information \
    --instance-information-filter-list Key=InstanceIds,ValueSet=mi-0abc123def456789a
  Expect: PingStatus=Active within 5-10 minutes.
VERDICT: ESCALATE
NEXT_STEP: Provide on-prem operator with a new activation code:
  aws ssm create-activation --iam-role <activation-role> \
    --registration-limit 1 --expiry-date $(date -u -v+7d +%Y-%m-%d)
ESCALATION_PATH: On-prem / edge-device operator must run on the host:
  amazon-ssm-agent -register -code <new-code> -id <new-id> -region <region>
  (requires sudo / admin on the host). Cannot be done from the AWS side.
```

This contract is mandatory. The Output format template above is the
authoritative structure. Violating any rule is a misdiagnosis.

### Required output structure

Every diagnosis MUST emit the exact DIAGNOSIS block with all fields
populated (no empty fields, no omitted sections, no reordering). All
three LAYER_CHECK lines (IAM, Connectivity, Agent) are mandatory —
even when the failure is association-specific.

Verdict-specific rules:
- `ROOT_CAUSE_FOUND` → ROOT_CAUSE names a single specific cause; EVIDENCE cites at least one failing API signal; FIX is actionable CLI.
- `NEED_MORE_INFO` → ROOT_CAUSE is "Pending diagnosis — <what is known>"; NEXT_STEP cites the exact next command.
- `ESCALATE` → ESCALATION_PATH names the recipient and the out-of-band action required.

### FORBIDDEN output patterns

- NEVER diagnose without checking SSM agent status first — the agent must be 'Online' for any association to work. A diagnosis that skips the LAYER_CHECK Agent line is invalid.
- NEVER confuse association status 'Failed' with instance not being managed — Failed means the document ran but returned non-zero. NotManaged is a different symptom (Step 4).
- NEVER treat association `Status: Success` as proof the document script succeeded — always read per-target `Status` from `describe-association-execution-targets`.
- NEVER emit `VERDICT: NEED_MORE_INFO` without a `NEXT_STEP` naming a specific diagnostic command. Generic phrases like "investigate further" are not acceptable.
- NEVER use `ec2 describe-instances` for `mi-*` hybrid instances. They are not EC2 resources; route through `describe-instance-information` and `describe-activations`.

## Anti-Patterns — NEVER do these things

- NEVER diagnose an association without first running the 3-layer health check. Most "association Failed" tickets are coverage gaps in IAM, connectivity, or agent.
- NEVER treat association `Status: Success` as proof that the document script succeeded. Always read `describe-association-execution-targets` for per-target `Status: Failed`.
- NEVER assume `PingStatus: Active` means the instance is fully healthy. Active is heartbeat (last 5 min), not health. Pair with `LastPingDateTime`.
- NEVER treat `AWS-ApplyPatchBaseline` `Operation=Scan` as a failure when it reports `NON_COMPLIANT`. Scan records compliance; it does NOT install patches.
- NEVER recommend `delete-association` as the first remediation. Modify-then-test (`update-association`, `start-associations-once`) preserves targeting and schedule.

## Pre-flight safety checks

- **MANDATORY CONFIRMATION GATE** before any state-changing operation (`update-association`, `start-associations-once`, `delete-association`, `send-command Operation=Install`, `create-activation`).
- **`start-associations-once` target blast radius:** confirm targets before triggering — tag-based target can hit larger fleet than expected.
- **`send-command` target blast radius:** always pass `--instance-ids <id>` (single instance) for diagnostic commands, NEVER `--targets Key=InstanceIds,Values=*`.
- **Patch Install pre-flight:** verify patch baseline `ApprovalRules` match the intended maintenance window.
- **Association modification:** snapshot `describe-association --output json` BEFORE `update-association`.

## Appendix A — Symptom-to-cause map (quick reference)

| Symptom | Most common root cause | Verify via |
|---|---|---|
| Failed — invalid parameters | Document schema drift / wrong parameter value | `describe-association-executions` StatusMessage |
| Failed — AccessDenied | Instance role missing required action | `simulate-principal-policy` |
| Failed — document not found | Document deleted or name typo | `describe-document` |
| Failed — S3 access denied | Role lacks `s3:PutObject` on output bucket | `simulate-principal-policy` |
| TimedOut — ConnectionLost | IAM, network, or agent failure | 3-layer health check (Step 1) |
| TimedOut — script hangs | Document script deadlock or infinite loop | Agent log + `timeoutSeconds` |
| NotManaged — EC2 | No instance profile / wrong policy | `ec2 describe-instances` + `list-attached-role-policies` |
| NotManaged — private subnet | VPC endpoints missing | `ec2 describe-vpc-endpoints` |
| NotManaged — hybrid `mi-*` | Activation expired or quota exhausted | `describe-activations` |
| NotManaged — fresh launch | Agent still bootstrapping (< 5 min) | `LaunchTime` vs current time |
| NeverRuns — schedule wrong | Malformed cron (both DOM and DOW set) | `describe-association` ScheduleExpression |
| NeverRuns — targets empty | Tag key/value mismatch | `ec2 describe-instances --filters` |
| NeverRuns — Disabled | Association `State: Disabled` | `describe-association` State |
| DocumentError — script error | Syntax / logic error in document | S3 output or `get-command-invocation` |
| DocumentError — platform | Document `PlatformTypes` excludes OS | `describe-document` PlatformTypes |

## Recent AWS features (2024-2026)

- **SSM Quick Setup (2024):** Pre-configured baselines (patch policies, Session Manager, inventory) deployable via CloudFormation. Verify Quick Setup-managed resources are not locally overridden when diagnosing drift.
- **Session Manager port forwarding and SSH proxy (2024-2025):** Enhanced Session Manager with native SSH proxy. Useful for fetching agent logs from instances with no inbound access.
- **Hybrid Activator (2024):** Streamlined on-prem registration. Verify activation role includes `AmazonSSMManagedInstanceCore`.
- **Patch baseline enhancements (2024-2025):** Amazon Linux 2023 support, Debian/Ubuntu improvements. Verify baseline covers all managed OS types.
- **SSM Document versioning (2024):** Verify associations reference a specific version (not `$LATEST`) for production stability — `$LATEST` produces silent drift.
- **Distributor integration (2024-2025):** SSM Distributor can deploy/update agents on hybrid instances. Verify packages are current when diagnosing `IsLatestVersion: false`.

## Domain

AWS CloudOps / Systems Manager Association Diagnostics.

## AWS documentation

- **AWS Systems Manager User Guide** — https://docs.aws.amazon.com/systems-manager/latest/userguide/what-is-systems-manager.html
- **SSM Associations** — https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-associations.html
- **SSM Agent** — https://docs.aws.amazon.com/systems-manager/latest/userguide/ssm-agent.html
- **SSM Documents** — https://docs.aws.amazon.com/systems-manager/latest/userguide/documents.html
- **Patch Manager** — https://docs.aws.amazon.com/systems-manager/latest/userguide/patch-manager.html
- **Hybrid Activations** — https://docs.aws.amazon.com/systems-manager/latest/userguide/managed-instances.html
- **VPC Endpoints for SSM** — https://docs.aws.amazon.com/systems-manager/latest/userguide/setup-create-vpc.html
- **API Reference** — https://docs.aws.amazon.com/systems-manager/latest/APIReference/
- **CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/ssm/
- **Troubleshooting SSM Agent** — https://docs.aws.amazon.com/systems-manager/latest/userguide/ssm-agent.html#ssm-agent-troubleshooting
