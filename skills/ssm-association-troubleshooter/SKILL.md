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

**One-line takeaway:** an SSM association runs only when three
independent layers are healthy — **IAM** (instance can talk to
SSM), **connectivity** (instance reaches SSM endpoints), and
**agent** (SSM Agent running and current). Most association
failures are one of these three layers masquerading as an
association problem. Diagnose the layer first, then the
association-specific config.

- **The 3-layer SSM health check is the upstream gate.** If the
  instance is not pinging SSM (ConnectionLost, Inactive, missing
  from console), no association can run. Diagnose IAM, then
  connectivity, then agent — in that order. Most "association
  Failed" tickets are actually coverage gaps.
- **`describe-association-executions` is the source of truth.**
  The console shows a status enum; the API returns the detailed
  execution output, including per-target results, error messages,
  and S3 output URIs. Always drill into execution-targets for the
  specific failure.
- **Association status and document execution status are
  different.** A `Success` association status means the document
  started; it does NOT mean the script inside succeeded. Always
  cross-reference `describe-association-execution-targets` for
  per-target `Status: Success|Failed|TimedOut`.

## Quick navigation

| You want to... | Go to |
|---|---|
| Run the 3-layer health check first (recommended) | Step 1 |
| Diagnose association status: Failed | Step 2 |
| Diagnose association status: TimedOut | Step 3 |
| Diagnose instance not appearing in SSM | Step 4 |
| Diagnose association never runs | Step 5 |
| Diagnose document execution fails mid-run | Step 6 |
| Inspect SSM agent logs on the host | Appendix A |
| Map symptom to root cause quickly | Appendix B |
| Avoid misdiagnosis pitfalls | Anti-Patterns |
| Reduce a partial diagnosis to ROOT_CAUSE_FOUND | Output format |

## Critical rules at a glance (do NOT bury these)

1. **Run the 3-layer health check FIRST.** Before any association-
   specific diagnosis, confirm: (1) IAM role has
   `AmazonSSMManagedInstanceCore`, (2) instance can reach SSM
   endpoints (`ssm.`, `ec2messages.`, `ssmmessages.`), (3) agent
   is running and current. A failing layer invalidates all
   downstream association diagnosis.
2. **Use `describe-association-executions`, not the console.** The
   console aggregates; the API returns per-target detail including
   the actual error message, S3 output URI, and execution-id
   needed for deeper drill-down.
3. **Association status `Success` does NOT mean the script
   succeeded.** A `Success` association status means the document
   orchestration started; per-target `Failed` is a separate
   field. Always read `describe-association-execution-targets`.
4. **Patch `Scan` vs `Install` matters.** An `AWS-ApplyPatchBaseline`
   association with `Operation=Scan` reports compliance but does
   NOT install patches. A "failing" patch association may simply
   be running Scan against a non-compliant host.
5. **Hybrid activations have a different diagnosis path than EC2.**
   `mi-*` instances are registered via activation code/ID; their
   IAM role comes from the activation, not an EC2 instance profile.
   Do not run `ec2 describe-instances` for `mi-*` — it will return
   nothing.

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

**If the input is malformed** (no association-id, no instance-id,
ambiguous symptom), emit:

```text
DIAGNOSIS: <reference>
SYMPTOM: unknown
VERDICT: NEED_MORE_INFO
GAP: Cannot start diagnosis — required inputs missing.
     Re-supply: association-id or association name, the observed
     symptom (Failed / TimedOut / never-runs / document-error /
     instance-missing), and at least one instance-id or target.
```

## Process — Diagnostic decision tree (apply in order)

### Step 0: Expert knowledge — non-obvious SSM behaviors

These behaviours change a diagnosis if ignored:

- **`describe-instance-information` only shows instances SSM
  already knows about.** A freshly launched EC2 instance with no
  IAM profile will NOT appear. To find the true coverage gap, diff
  `ec2 describe-instances` (full EC2 set) against
  `ssm describe-instance-information` (managed subset).

- **`PingStatus: Active` is heartbeat, not health.** Active only
  means the agent pinged SSM in the last ~5 minutes. It does NOT
  mean associations are running, patches are current, or the
  document can execute. Always pair with `LastPingDateTime`.

- **Association `Status` is the orchestration status, not the
  document result.** `Status: Success` on
  `describe-association-executions` means SSM started the
  document. The per-target `Status: Failed` (in
  `describe-association-execution-targets`) is where the script
  error lives.

- **`AWS-ApplyPatchBaseline` has two Operations: `Scan` and
  `Install`.** `Scan` records compliance but does not patch;
  `Install` applies patches. A "failing" patch association may be
  a `Scan` correctly reporting NON_COMPLIANT — not a failure.

- **`Patch Group` is a TAG, not an association property.** The
  case-sensitive tag key `Patch Group` (with space, capital G)
  links an instance to a baseline. Without this tag, the instance
  uses the default regional baseline silently.

- **`AmazonSSMManagedInstanceCore` is the modern role policy.**
  The deprecated `AmazonEC2RoleforSSM` lacks `ssmmessages:*`
  (Session Manager) and several inventory permissions. A
  "managed" instance on the legacy policy may run associations
  but cannot run Session Manager.

- **Hybrid activation `mi-*` instances use the activation role,
  not an EC2 profile.** `IamRoleARN` for `ResourceType:
  ManagedInstance` comes from the activation code/ID exchange at
  registration. Different remediation path than EC2.

- **Three VPC endpoints are required for fully-private SSM.**
  `ssm`, `ssmmessages`, and `ec2messages`. Missing any one
  produces `ConnectionLost` PingStatus even with correct IAM and
  a healthy agent. This is a NETWORKING failure, not an agent
  failure.

- **SSM enforces a per-instance command concurrency limit
  (default 1).** A second concurrent command returns
  `InvalidInstanceId` or `TargetNotConnected`. Diagnose as
  transient back-off, not a coverage failure.

- **`AWS-UpdateSSMAgent` is the auto-update association.** Without
  it, the agent only updates on instance stop/start or manual
  command. Missing it is the root cause of most
  `IsLatestVersion: false` findings.

- **Association versions are immutable; SSM keeps up to 99.** To
  "revert" an association, update its document-version reference
  or recreate it with the old parameters.

- **`scheduleExpression` on associations uses `rate()` or
  `cron()`.** Common mistake: copying a CloudWatch cron syntax
  (which uses `?` in DOM/DOW) — SSM associations accept the same
  AWS cron syntax as EventBridge rules.

- **Targets are evaluated at execution time, not creation time.**
  An association targeting `Key=tag:Environment,Values=prod` runs
  against whatever currently has that tag. If you retag mid-run,
  the next execution picks up the new targets.

- **Document parameters are validated at execution time.** A
  document reference to a deleted parameter (e.g., an S3 bucket
  that no longer exists) produces `Failed` execution only when
  the association runs — not at association creation.

### Step 1: The 3-layer SSM health check (run FIRST)

Before any association-specific diagnosis, confirm all three
layers. A failing layer invalidates all downstream diagnosis.

**Layer 1 — IAM (instance profile has AmazonSSMManagedInstanceCore).**

```bash
# EC2 instance profile check
aws ec2 describe-instances --instance-ids <instance-id> \
  --query 'Reservations[*].Instances[*].IamInstanceProfile.Arn' --output text

aws iam list-instance-profiles --output text \
  --query 'InstanceProfiles[?InstanceProfileName==`<profile-name>`].Roles[*].RoleName'

aws iam list-attached-role-policies --role-name <role-name> --output text \
  --query 'AttachedPolicies[*].PolicyName'
```

For hybrid `mi-*` instances, check the activation role:

```bash
aws ssm describe-instance-information \
  --instance-information-filter-list Key=InstanceIds,ValueSet=<mi-id> \
  --query 'InstanceInformationList[*].IamRoleARN' --output text

aws ssm describe-activations \
  --filters Key=RegistrationStatus,Values=Registered \
  --query 'ActivationList[*].[ActivationId,IamRole,Expired]' --output text
```

**Layer 2 — Connectivity (instance can reach SSM endpoints).**

For instances in a private subnet (no internet egress), confirm
the three required VPC endpoints exist:

```bash
aws ec2 describe-vpc-endpoints \
  --filters Name=vpc-id,Values=<vpc-id> Name=service-name,Values=com.amazonaws.<region>.ssm,com.amazonaws.<region>.ssmmessages,com.amazonaws.<region>.ec2messages \
  --query 'VpcEndpoints[*].[ServiceName,State]' --output table
```

For instances with internet egress, verify the security group
allows HTTPS/443 outbound to SSM endpoints.

**Layer 3 — Agent (running and current).**

```bash
aws ssm describe-instance-information \
  --instance-information-filter-list Key=InstanceIds,ValueSet=<instance-id> \
  --query 'InstanceInformationList[*].[PingStatus,LastPingDateTime,AgentVersion,IsLatestVersion,PlatformType]' --output table
```

Flags:
- `PingStatus: ConnectionLost` or `Inactive` — Layer 1 or 2 failure
- `IsLatestVersion: false` — agent out of date; missing `AWS-UpdateSSMAgent` association
- `LastPingDateTime` > 1 hour ago — flapping agent or stale record

**If any layer fails, fix the layer FIRST.** Most association
failures resolve when coverage is restored. Specifically:
- Layer 1 fails → attach `AmazonSSMManagedInstanceCore` to the
  instance profile (EC2) or re-activate with a new role (`mi-*`).
- Layer 2 fails → deploy VPC endpoints or fix security group
  outbound.
- Layer 3 fails → restart the agent or update via
  `AWS-UpdateSSMAgent`.

### Step 2: Diagnose association status: Failed

**Symptom:** association `Status: Failed` in console or
`describe-association-executions`.

**Diagnostic tree:**

```bash
# 1. Get the most recent execution
aws ssm describe-association-executions \
  --association-id <association-id> \
  --query 'Executions[0].[ExecutionId,Status,StatusMessage,ExecutionTime]' --output table

# 2. Drill into per-target results
aws ssm describe-association-execution-targets \
  --association-id <association-id> \
  --execution-id <execution-id> \
  --query 'Targets[*].[Status,StatusMessage,ResourceId,OutputSource.S3Url]' --output table

# 3. Fetch detailed output from S3 if OutputSource is configured
aws s3 cp <s3-url-from-step-2> -

# 4. List association versions to detect a recent parameter change
aws ssm list-association-versions \
  --association-id <association-id> \
  --query 'AssociationVersions[*].[Version,Date,CreatedBy]' --output table
```

**Common root causes (Failed):**

| Cause | Diagnostic signal | Fix |
|---|---|---|
| Invalid parameters | `StatusMessage: Invalid parameters` | Fix association parameters; document may have changed schema |
| Document not found | `StatusMessage: Document does not exist` | Document deleted or name typo; recreate or fix association document-name |
| S3 bucket access denied for output | `StatusMessage: AccessDenied on s3:PutObject` | Add `s3:PutObject` for the output bucket to the instance role |
| Instance profile missing permissions | `StatusMessage: AccessDenied` on the target API | Add the required action to the instance role |
| Document parameters reference deleted resource | `StatusMessage: InvalidDocument` or `InvalidParameters` | Update association parameters; recreate referenced resource |
| Association document-version points at `$LATEST` and document was updated | `StatusMessage: schema drift` | Pin document-version or update association to match new schema |

**VERDICT:** ROOT_CAUSE_FOUND when the StatusMessage + S3 output
identifies a specific cause; NEED_MORE_INFO when the message is
generic ("document execution failed") and the S3 output is empty
(fetch the agent log via Step 6 / Appendix A).

### Step 3: Diagnose association status: TimedOut

**Symptom:** association `Status: TimedOut` in console.

**Diagnostic tree:**

```bash
# 1. Check the most recent execution
aws ssm describe-association-executions \
  --association-id <association-id> \
  --query 'Executions[0].[ExecutionId,Status,ExecutionTime]' --output table

# 2. Check instance reachability NOW (the timeout may be transient)
aws ssm describe-instance-information \
  --instance-information-filter-list Key=InstanceIds,ValueSet=<instance-id> \
  --query 'InstanceInformationList[*].[PingStatus,LastPingDateTime,AgentVersion]' --output table

# 3. If PingStatus is ConnectionLost/Inactive, run the 3-layer check (Step 1)
# 4. If the instance is reachable, check command-level timeout
aws ssm list-command-invocations \
  --instance-id <instance-id> \
  --query 'CommandInvocations[*].[CommandId,Status,StatusDetails,NotificationStatus]' --output table
```

**Common root causes (TimedOut):**

| Cause | Diagnostic signal | Fix |
|---|---|---|
| SSM Agent unreachable | `PingStatus: ConnectionLost` or `Inactive` | Run 3-layer check; fix IAM, endpoints, or restart agent |
| Instance offline (stopped/terminated) | `ec2 describe-instances` shows state `stopped` or `terminated` | Start the instance or recreate |
| Network connectivity to SSM endpoints lost | Agent unreachable but EC2 reachable; VPC endpoints missing or SG blocking | Deploy endpoints / fix SG |
| Script in document hangs (deadlock, infinite loop) | Instance healthy, agent running, but command never completes | Review document script; add explicit timeouts via `timeoutSeconds` |
| `ExecutionTimeout` too short for the workload | `StatusDetails: Timeout` immediately | Increase document `ExecutionTimeout` |

**VERDICT:** ROOT_CAUSE_FOUND when the 3-layer check identifies a
specific layer failure or the script-hang signal is clear;
NEED_MORE_INFO if the instance is reachable and the agent is
current — fetch the agent log (Appendix A) to confirm the
specific command that hung.

### Step 4: Diagnose instance not appearing in SSM (not managed)

**Symptom:** instance is missing from the SSM console / Fleet
Manager / `describe-instance-information`.

**Diagnostic tree:**

```bash
# 1. Confirm the instance exists in EC2 (and is running)
aws ec2 describe-instances --instance-ids <instance-id> \
  --query 'Reservations[*].Instances[*].[State.Name,LaunchTime,IamInstanceProfile.Arn]' --output table

# 2. If state is running but no instance profile, that is the cause
# Attach AmazonSSMManagedInstanceCore:
aws ec2 associate-iam-instance-profile \
  --instance-id <instance-id> \
  --iam-instance-profile Name=<profile-with-SSM-policy>

# 3. If state is running with profile, check VPC endpoints
aws ec2 describe-vpc-endpoints \
  --filters Name=vpc-id,Values=<vpc-id> \
  --query 'VpcEndpoints[?contains(ServiceName,`.ssm.`) \|\| contains(ServiceName,`.ssmmessages.`) \|\| contains(ServiceName,`.ec2messages.`)].[ServiceName,State]' --output table

# 4. If profile and endpoints are fine, check if the SSM agent is running on the host
# (requires the instance to be reachable via SSH/SSM from another working instance)
aws ssm send-command --instance-ids <reachable-instance-id> \
  --document-name "AWS-RunShellScript" \
  --parameters commands=["ssm-cli get-agent-connection-status --region <region>"] \
  --query 'Command.CommandId' --output text

# 5. For hybrid (mi-*) instances, check activation status
aws ssm describe-activations --filters Key=RegistrationStatus,Values=Registered
```

**Common root causes (not managed):**

| Cause | Diagnostic signal | Fix |
|---|---|---|
| EC2 instance has no IAM instance profile | `describe-instances` returns empty `IamInstanceProfile.Arn` | Attach a profile with `AmazonSSMManagedInstanceCore` |
| Profile missing `AmazonSSMManagedInstanceCore` | `list-attached-role-policies` does not include it | Attach `AmazonSSMManagedInstanceCore` to the role |
| Legacy policy only (`AmazonEC2RoleforSSM`) | Role has the deprecated policy only | Replace with `AmazonSSMManagedInstanceCore` |
| Instance in private subnet without VPC endpoints | No `ssm.`, `ssmmessages.`, or `ec2messages.` endpoints | Deploy all three interface endpoints |
| SSM Agent not installed | `ssm-cli get-agent-connection-status` fails or agent missing | Install the agent for the OS |
| SSM Agent not running | Service status `inactive` / `stopped` | `systemctl start amazon-ssm-agent` (Linux) or restart the service (Windows) |
| Hybrid activation expired or quota exhausted | `describe-activations` shows `Expired: true` or `RegistrationLimit` reached | Create a new activation; re-register the instance |
| Instance launched < 5 min ago | Agent has not bootstrapped yet | Wait 5-10 minutes; do not flag as UNMANAGED |

**VERDICT:** ROOT_CAUSE_FOUND when one of the seven causes above
matches; NEED_MORE_INFO if multiple causes are partially true
(e.g., profile exists but is the legacy policy AND no endpoints)
— fix one and re-check.

### Step 5: Diagnose association never runs (wrong schedule or targets)

**Symptom:** association exists and is `Enabled` but has no
executions in `describe-association-executions`, or the schedule
is wrong.

**Diagnostic tree:**

```bash
# 1. Confirm the association is Enabled
aws ssm describe-association \
  --association-id <association-id> \
  --query 'AssociationDescription.[Name,AssociationName,State,ScheduleExpression,ScheduleOffset,LastExecutionDate,NextExecutionDate]' --output table

# 2. Check targets match any current instances
aws ssm describe-association \
  --association-id <association-id> \
  --query 'AssociationDescription.Targets' --output table

# Then verify the targets actually match instances:
aws ec2 describe-instances \
  --filters Name=tag:<tag-key>,Values=<tag-value> \
  --query 'Reservations[*].Instances[*].InstanceId' --output text

# 3. Check the cron/rate expression syntax
# (SSM uses AWS cron with ? in DOM or DOW; rate(N unit))
aws ssm describe-association \
  --association-id <association-id> \
  --query 'AssociationDescription.ScheduleExpression' --output text

# 4. List recent executions to confirm absence
aws ssm describe-association-executions \
  --association-id <association-id> \
  --query 'Executions[*].[ExecutionId,Status,ExecutionTime]' --output table
```

**Common root causes (never runs):**

| Cause | Diagnostic signal | Fix |
|---|---|---|
| Schedule expression wrong | Malformed `cron()` or `rate()`; both DOM and DOW set (no `?`) | Fix syntax; use `?` in one of DOM/DOW |
| Targets don't match any instance | Tag key/value mismatch; `Targets` returns empty on `describe-instances` | Fix tag values or retag instances |
| Association `State: Disabled` | `State: Disabled` on `describe-association` | `update-association-state` to `Enabled` |
| `NextExecutionDate` is in the past but no run | Rate-limiting or service degradation | Check CloudWatch `AWS/SSM` metrics; wait and recheck |
| Rate-limiting on associations | Many associations on same instance; throttling visible in CloudTrail | Stagger schedules; reduce concurrency |
| Calendar mismatch (schedule offset) | `ScheduleOffset` shifts run into next day | Verify `ScheduleOffset` is intended |
| Targeting `Key=InstanceIds,Values=<wrong-id>` | Typo in instance-id | Fix target list |

**VERDICT:** ROOT_CAUSE_FOUND when the schedule, target, or state
issue is clearly identified; NEED_MORE_INFO if the association
config looks correct but no executions appear — fetch CloudTrail
`StartAssociationsOnce` events to confirm the scheduler invoked
the association.

### Step 6: Diagnose document execution fails mid-run

**Symptom:** association orchestration succeeds but per-target
`Status: Failed` in `describe-association-execution-targets`,
or the script within the document errors.

**Diagnostic tree:**

```bash
# 1. Get per-target results
aws ssm describe-association-execution-targets \
  --association-id <association-id> \
  --execution-id <execution-id> \
  --query 'Targets[*].[Status,StatusMessage,ResourceId,OutputSource.S3Url]' --output table

# 2. Fetch the S3 output (the actual script stdout/stderr)
aws s3 cp <s3-url-from-step-1> -

# 3. If OutputSource is empty, the instance role lacks s3:PutObject
# Check IAM:
aws iam simulate-principal-policy \
  --policy-source-arn <instance-role-arn> \
  --action-names s3:PutObject s3:GetObject \
  --resource-arns arn:aws:s3:::<output-bucket>/*

# 4. Verify the document exists and the version matches
aws ssm describe-document \
  --name <document-name> \
  --query 'Document.[LatestVersion,DefaultVersion,SchemaVersion,PlatformTypes]' --output table

# 5. For Send Command-based documents, fetch the command invocation
aws ssm get-command-invocation \
  --command-id <command-id> --instance-id <instance-id> \
  --query '[Status,StatusDetails,StandardOutputContent,StandardErrorContent]' --output table
```

**Common root causes (document fails):**

| Cause | Diagnostic signal | Fix |
|---|---|---|
| Script error (syntax, logic) | `StandardErrorContent` shows script error | Fix the document script |
| Permission denied (instance profile lacks API) | `AccessDenied` in script output | Add the required action to the instance role |
| Platform unsupported | `PlatformTypes` does not include the instance OS | Use a different document or extend platform support |
| Document references missing resource (S3, parameter) | `ResourceNotFound` in output | Recreate or fix reference |
| Document version drift | `DefaultVersion` changed; association pinned to old version | Update association `DocumentVersion` |
| Script exceeds `timeoutSeconds` | `StatusDetails: Timeout` mid-execution | Increase timeout or split the document |
| Script depends on missing package | yum/apt/dnf returns error | Install the package via a separate association first |
| Reboot mid-script on Windows | Script restarts the instance; subsequent steps fail | Split document; use `aws:rebootInstance` action explicitly |
| Script running as wrong user | `AccessDenied` on file/resource | Set `runCommand` user explicitly in the document |

**VERDICT:** ROOT_CAUSE_FOUND when the S3 output / standard error
identifies a specific failure; NEED_MORE_INFO when output is empty
— fetch the SSM agent log from the host (Appendix A) for the
plugin-level error.

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
ESCALATION_PATH: <if ESCALATE, the recommended path (AWS Support, in-house owner)>
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
ROOT_CAUSE: Pending diagnosis — instance is reachable (PingStatus
            Active) and agent is current, but the document hangs
            mid-execution. Need SSM agent log to identify the
            hung plugin.
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
ROOT_CAUSE: Hybrid activation `aabbccdd-1111-2222-3333-aabbccddeeff`
            is expired (Expired: true). The mi-* instance was
            registered under this activation; the agent can no
            longer re-authenticate.
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

## Anti-Patterns — NEVER do these things

- NEVER diagnose an association without first running the 3-layer
  health check. Most "association Failed" tickets are coverage
  gaps in IAM, connectivity, or agent. Skipping the layer check
  sends you down the wrong remediation path.

- NEVER treat association `Status: Success` as proof that the
  document script succeeded. `Success` means the orchestration
  started; per-target `Status: Failed` (in
  `describe-association-execution-targets`) is where the script
  error lives. Always read the per-target detail.

- NEVER assume `PingStatus: Active` means the instance is fully
  healthy. `Active` is heartbeat (last 5 min), not health. Pair
  with `LastPingDateTime` and the layer check.

- NEVER treat `AWS-ApplyPatchBaseline` `Operation=Scan` as a
  failure when it reports `NON_COMPLIANT`. `Scan` records
  compliance; it does NOT install patches. A "failing" Scan is
  correctly identifying missing patches.

- NEVER use `ec2 describe-instances` for `mi-*` hybrid instances.
  They are not EC2 resources; the API returns nothing. Use
  `describe-instance-information` only.

- NEVER recommend `delete-association` as the first remediation.
  Modify-then-test (`update-association`,
  `start-associations-once`) preserves targeting and schedule;
  deleting loses configuration context.

- NEVER assume the SSM Agent auto-updates. Without the
  `AWS-UpdateSSMAgent` association, the agent only updates on
  instance stop/start or manual `SendCommand`. Missing this
  association is the leading root cause of `IsLatestVersion: false`.

- NEVER assume a private-subnet instance can reach SSM without
  VPC endpoints. The three required interface endpoints are
  `ssm`, `ssmmessages`, `ec2messages`. Missing any one produces
  `PingStatus: ConnectionLost`.

- NEVER conflate `InstalledPendingCount` with `MissingCount` in
  patch state. `InstalledPending` are patches installed but
  awaiting reboot (Windows); `Missing` are not installed. Both
  count toward NON_COMPLIANT but the remediation differs.

- NEVER treat a concurrent-command limit error
  (`InvalidInstanceId`, `TargetNotConnected`) as a coverage
  failure. SSM enforces 1 concurrent command per instance by
  default; a second command is a transient back-off, not a
  managed-state issue.

- NEVER diagnose a freshly launched instance (< 5 min) as
  UNMANAGED. The SSM Agent takes 1-5 minutes to bootstrap on
  first boot. Treat absent `LastPingDateTime` on a fresh launch
  as PENDING.

- NEVER assume a `cron(0 2 * * *)` schedule expression is valid
  for an SSM association. SSM uses AWS cron syntax requiring `?`
  in either day-of-month or day-of-week. Use
  `cron(0 2 * * ? *)` for daily at 02:00.

- NEVER assume `Targets` is evaluated at association creation.
  Targets are evaluated at execution time. A tag-based target
  matches whatever currently has the tag — retagging mid-run
  changes the target set silently.

- NEVER skip fetching S3 output when an association has
  `OutputSource.S3Url` configured. The S3 object contains the
  actual stdout/stderr; the API `StatusMessage` is a summary.

- NEVER escalate to AWS Support without first gathering the
  association-id, execution-id, instance-id, and the SSM agent
  log excerpt. AWS Support will ask for these immediately.

## Pre-flight safety checks (run before applying any fix)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing
  operation (`update-association`, `start-associations-once`,
  `delete-association`, `send-command Operation=Install`,
  `create-activation`), the troubleshooter MUST emit:
  `CONFIRM: About to <action> on association <id> / instance
  <id> in account <account>. This affects <consequence>.
  Proceed? (yes/no)`. Do NOT execute until the operator
  confirms. `AWS-ApplyPatchBaseline Operation=Install` reboots
  Windows instances.

- **`start-associations-once` target blast radius.** Confirm the
  association's targets before triggering a run — a tag-based
  target can hit a much larger fleet than expected.

- **`send-command` target blast radius.** Always pass
  `--instance-ids <id>` (single instance) for diagnostic
  commands, NEVER `--targets Key=InstanceIds,Values=*` or a
  tag-based target. A mis-scoped diagnostic command can fan out
  fleet-wide.

- **Patch Install pre-flight:** before running `Operation=Install`,
  verify the patch baseline's `ApprovalRules` match the intended
  maintenance window via `describe-patch-baseline`.

- **Association modification:** snapshot
  `aws ssm describe-association --association-id <id> --output
  json` BEFORE `update-association`. SSM keeps version history
  but explicit rollback is easier with a snapshot.

- **Role-policy changes:** when adding `s3:PutObject` or other
  permissions, use `put-role-policy` (inline) for testing or
  attach a managed policy for permanent changes. Avoid widening
  existing inline policies — add a new statement.

## Appendix A — SSM agent logs and on-host diagnostics

The SSM agent logs are the primary evidence for document-level
failures. Fetch them via a working SSM session or out-of-band
access.

**Primary log locations:**

| OS | Path |
|---|---|
| Linux (most) | `/var/log/amazon/ssm/amazon-ssm-agent.log` |
| Linux (Amazon Linux 2023 / snap) | `/var/snap/amazon-ssm-agent/current/amazon-ssm-agent.log` |
| Windows | `C:\ProgramData\Amazon\SSM\Logs\amazon-ssm-agent.log` |
| Windows errors | `C:\ProgramData\Amazon\SSM\Logs\errors.log` |

**Fetch via SSM (if the instance is reachable):**

```bash
aws ssm send-command \
  --instance-ids <instance-id> \
  --document-name "AWS-RunShellScript" \
  --parameters commands=["tail -n 200 /var/log/amazon/ssm/amazon-ssm-agent.log"] \
  --query 'Command.CommandId' --output text

aws ssm get-command-invocation \
  --command-id <command-id> --instance-id <instance-id> \
  --query 'StandardOutputContent' --output text
```

**Diagnostic signals in the log:**

| Log entry | Diagnosis |
|---|---|
| `Failed to load agent config` | Activation or IAM issue (Layer 1) |
| `connection refused` to `ssm.<region>` | Network / endpoint issue (Layer 2) |
| `EmptyInstanceID` | Instance not registered; new instance still bootstrapping |
| `TimeoutExceeded` for a plugin | Document script hung; check `timeoutSeconds` |
| `AccessDenied` on a service call | Instance role lacks the action |
| `Plugin {name} crashed` | Plugin-specific bug; update the agent |
| `no space left on device` | Disk full on the instance — common root cause |

**On-host agent status:**

```bash
# Linux
systemctl status amazon-ssm-agent
sudo ssm-cli get-agent-connection-status --region <region>
sudo ssm-cli get-agent-fqdn --region <region>

# Windows
Get-Service AmazonSSMAgent
& "C:\Program Files\Amazon\SSM\ssm-cli.exe" get-agent-connection-status --region <region>
```

**Restart the agent (post-fix verification):**

```bash
# Linux
sudo systemctl restart amazon-ssm-agent
# Windows
Restart-Service AmazonSSMAgent
```

## Appendix B — Symptom-to-cause map (quick reference)

| Symptom | Most common root cause | Verify via |
|---|---|---|
| Failed — invalid parameters | Document schema drift / wrong parameter value | `describe-association-executions` StatusMessage |
| Failed — AccessDenied | Instance role missing required action | `simulate-principal-policy` |
| Failed — document not found | Document deleted or name typo | `describe-document` |
| Failed — S3 access denied | Role lacks `s3:PutObject` on output bucket | `simulate-principal-policy` |
| TimedOut — ConnectionLost | IAM, network, or agent failure (Layer 1/2/3) | 3-layer health check (Step 1) |
| TimedOut — script hangs | Document script deadlock or infinite loop | Agent log + `timeoutSeconds` |
| NotManaged — EC2 | No instance profile / wrong policy | `ec2 describe-instances` + `list-attached-role-policies` |
| NotManaged — private subnet | VPC endpoints missing | `ec2 describe-vpc-endpoints` |
| NotManaged — hybrid `mi-*` | Activation expired or quota exhausted | `describe-activations` |
| NotManaged — fresh launch | Agent still bootstrapping (< 5 min) | `LaunchTime` vs current time |
| NeverRuns — schedule wrong | Malformed cron (both DOM and DOW set) | `describe-association` ScheduleExpression |
| NeverRuns — targets empty | Tag key/value mismatch | `ec2 describe-instances --filters` |
| NeverRuns — Disabled | Association `State: Disabled` | `describe-association` State |
| NeverRuns — rate limited | Many concurrent associations; throttling | CloudTrail `ThrottlingException` |
| DocumentError — script error | Syntax / logic error in document | S3 output or `get-command-invocation` StandardErrorContent |
| DocumentError — platform | Document `PlatformTypes` excludes OS | `describe-document` PlatformTypes |
| DocumentError — version drift | Association pinned to old document version | `list-association-versions` |

## Expert heuristic: "The 3-layer SSM health check"

Before any association-specific diagnosis, run the 3-layer check.
A failing layer invalidates all downstream diagnosis and is the
root cause of most "association Failed" tickets:

1. **IAM layer** — instance profile has `AmazonSSMManagedInstanceCore`
   (EC2) or the activation role has it (`mi-*`). Verify via
   `describe-instance-information` — if the instance appears,
   IAM is OK. If not, the role is the cause.

2. **Connectivity layer** — instance can reach SSM endpoints
   (`ssm.<region>`, `ec2messages.<region>`, `ssmmessages.<region>`).
   For private subnets, verify all three VPC endpoints exist. For
   internet-egress instances, verify the security group allows
   HTTPS/443 outbound.

3. **Agent layer** — `amazon-ssm-agent` service is running,
   `IsLatestVersion: true` (or at least >= v2.3.12.0 for Session
   Manager), and `PingStatus: Active` with `LastPingDateTime`
   within the last 5-30 minutes.

If all three layers pass, the issue is association-specific
(schedule, targets, document, parameters). Move to Steps 2-6.

If any layer fails, fix the layer first. Most "association
Failed" tickets close when coverage is restored — no association-
specific remediation is needed.

## Recent AWS features (2024-2026)

- **SSM Quick Setup (2024):** Pre-configured baselines (patch
  policies, Session Manager, inventory) deployable via
  CloudFormation. Verify Quick Setup-managed resources are not
  locally overridden when diagnosing drift.

- **Session Manager port forwarding and SSH proxy (2024-2025):**
  Enhanced Session Manager with native SSH proxy. Useful for
  fetching agent logs from instances that otherwise have no
  inbound access.

- **Hybrid Activator (2024):** Streamlined on-prem registration.
  Verify activation role includes
  `AmazonSSMManagedInstanceCore` — older activations may have a
  legacy role missing Session Manager permissions.

- **Patch baseline enhancements (2024-2025):** Amazon Linux 2023
  support, Debian/Ubuntu package manager improvements. Verify
  the patch baseline covers all managed OS types in the fleet.

- **SSM Document versioning (2024):** Documents support versioning.
  Verify that associations reference a specific version (not
  `$LATEST`) for production stability — `$LATEST` produces silent
  drift when the document is updated.

- **Distributor integration (2024-2025):** SSM Distributor can
  deploy and update agents on hybrid instances. Verify Distributor
  packages are current when diagnosing `IsLatestVersion: false`
  on hybrid fleets.

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
