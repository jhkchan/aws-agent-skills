---
name: datasync-task-operator
description: Operates AWS DataSync task end-to-end — agent deployment (on-prem VM, EC2), location configuration for every supported source (NFS, SMB, S3, HDFS, Object Storage) and destination (S3, EFS, FSx for Windows, FSx for Lustre, FSx for OpenZFS, FSx for NetApp ONTAP, Snowball Edge), task creation with the full Options surface (VerifyMode POINT_IN_TIME_CONSISTENT | ONLY_FILES_TRANSFERRED | NONE, OverwriteMode ALWAYS | NEVER, PosixPermissions PRESERVE | PRESERVE_TRY | BEST_EFFORT | NONE, Acl PRESERVE | NONE, TransferMode CHANGED | ALL, Gid PRESERVE | NONE, Uid PRESERVE | NONE, Mtime PRESERVE | NONE, SecurityDescriptorCopyFlags OWNER_DACL_SACL | OWNER_DACL | NONE, TaskQueueing ENABLED | DISABLED), scheduling (cron-like ScheduleExpression with up to 1-year horizon), bandwidth throttling (BandwidthLimitInMb), Task Reports with report-level and report-code filters, DataSync Discovery for on-prem capacity assessment, and FSx for NetApp ONTAP destination support. Runs deterministic pre-checks behind a CONFIRM gate and.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline plan classification. Live-account operations use aws datasync create-agent, create-location-nfs | create-location-smb | create-location-s3 | create-location-hdfs | create-location-object-storage | create-location-efs | create-location-fsx-windows | create-location-fsx-lustre | create-location-fsx-openzfs | create-location-fsx-ontap, create-task, update-task, start-task-execution...
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '4'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Storage
  task_type: operate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY | BLOCKED | COMPLETED
  when_to_use: Creating or modifying a DataSync task, deploying or activating a DataSync agent (on-prem VM or EC2), configuring source/destination locations for NFS, SMB, S3, HDFS, Object Storage, EFS, or FSx family destinations, setting task Options (VerifyMode, OverwriteMode, TransferMode, PosixPermissions, ACLs), creating a task Schedule with bandwidth throttling, diagnosing a failed or partial task execution, configuring Task Reports, planning an on-prem assessment with DataSync Discovery, or transferring to FSx for NetApp ONTAP.
  activation_triggers: create DataSync task, deploy DataSync agent, activate DataSync agent, DataSync NFS to S3, DataSync SMB to FSx, DataSync HDFS migration, DataSync schedule, DataSync bandwidth throttle, verify data integrity DataSync, POINT_IN_TIME_CONSISTENT, ONLY_FILES_TRANSFERRED, DataSync task failing, DataSync task execution error, DataSync Discovery, DataSync FSx for NetApp ONTAP, DataSync Task Reports, DataSync Snowball Edge, DataSync overwrite mode
  invocation_schema: 'Input: either (a) a DataSync task configuration (describe-task, describe-task-execution, describe-agent, list-locations) plus the intended operation (create-task, deploy-agent, update-task-options, create-schedule, diagnose-failing-execution, run-discovery, transfer-to-fsx-ontap, configure-task-reports), OR (b) a source + destination location pair for live-account execution. Output: deterministic OPERATION / VERDICT / PRE_CHECKS / STEPS / POST_VERIFY / NOTES block per operation, where VERDICT is one of READY, BLOCKED, COMPLETED.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: AWS DataSync, DataSync task, DataSync agent, DataSync Discovery, NFS migration, SMB migration, HDFS migration, Object Storage migration, S3 transfer, EFS transfer, FSx transfer, FSx for NetApp ONTAP, verify data integrity, POINT_IN_TIME_CONSISTENT, ONLY_FILES_TRANSFERRED, bandwidth throttling, BandwidthLimitInMb, task schedule, Task Reports, overwrite mode, PosixPermissions preserve, on-prem to AWS migration, Snowball Edge, activation key
  tags: aws, datasync, storage, migration, nfs, smb, hdfs, s3, efs, fsx, operate
---

# AWS DataSync Task Operator

## What this skill does

Executes AWS DataSync operations correctly and safely across the full
source/destination matrix. Runs deterministic pre-checks before any
state-changing CLI — agent activation key validity and reachability,
source location readability, destination location writeability, IAM
task role trust + permissions chain (including the KMS encrypt path
for SSE-KMS destinations, the cross-account bucket policy for
destinations in another account, and the EFS/FSx file system policy
allowing the DataSync service principal), task Options consistency
(e.g. `PosixPermissions PRESERVE` requires a destination that
preserves POSIX metadata; SMB sources need
`SecurityDescriptorCopyFlags` configured explicitly), schedule
expression validity (max 1-year horizon, required for
`update-task-schedule`), and bandwidth-throttle feasibility against
the agent's provisioned uplink. Executes the task change behind a
CONFIRM gate, then verifies the result by tailing
`describe-task-execution` until `Status` reaches `SUCCESS` (with
`BytesTransferred`, `BytesWritten`, `EstimatedFilesToTransfer`,
`FilesTransferred`, `VerifiedFilesCount`, `TransferDurationBytesPerSecond`
surfaced), and for `VerifyMode != NONE` confirming the verify pass
produced zero files failing the integrity check.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **§ Quick reference** | Verdict thresholds (BLOCKED/READY/COMPLETED) + pre-check priority | Before any operation |
| **§ Mindset** | Why DataSync is an agent-mediated async pipeline; the false-green-task trap; the verify-mode contract | Understanding the safety model |
| **§ Pre-flight** | Source + destination metadata gate — agent reachability, location readability, IAM role chain | Before executing any CLI |
| **§ Process** | Per-operation planning: create-task, deploy-agent, update-options, create-schedule, diagnose-failing-execution, run-discovery, transfer-to-fsx-ontap, configure-task-reports | When choosing which operation to run |
| **§ Output format** | STRICT output contract — OPERATION/VERDICT/PRE_CHECKS/STEPS/POST_VERIFY/NOTES template | Formatting the response |
| **§ Anti-Patterns** | NEVER list — common mistakes that strand data or break transfers silently | Review before risky operations |
| **§ Pre-flight safety** | Capture pre-state, IAM role policy, KMS key policy, destination bucket policy | Defense-in-depth |
| **§ Expert heuristic** | DataSync is async + eventually-consistent — never assume success from the API alone | Avoiding the false-green trap |

## STRICT output contract

EVERY response MUST end with a single fenced text block in this exact
shape (the operator's downstream tooling greps for it). No deviations:

```text
OPERATION: <create-task | deploy-agent | update-task-options | create-schedule | diagnose-failing-execution | run-discovery | transfer-to-fsx-ontap | configure-task-reports>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <source-location-uri> -> <destination-location-uri> (task: <id-or-"new">)
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. <CLI command with flags populated, or "(none — pre-checks failed)">
  2. <wait / monitoring command>
POST_VERIFY:
  - [PASS] <verification description> | (pending execution)
  - [FAIL] <verification description> — <reason>
NOTES: <schedule, monitoring, caveats>
```

Rules of the contract:

- VERDICT is exactly one of `READY`, `BLOCKED`, `COMPLETED`. No other
  values. `READY` means pre-checks passed and a CONFIRM gate is
  pending; `BLOCKED` means at least one pre-check failed — do NOT
  emit STEPS that mutate state; `COMPLETED` means post-verification
  passed after execution.
- If PRE_CHECKS has any `[FAIL]`, VERDICT MUST be `BLOCKED` and STEPS
  MUST be `(none — pre-checks failed)`.
- If VERDICT is `READY`, STEPS[1] MUST be the CONFIRM prompt and
  STEPS[2] MUST be the actual CLI.
- If VERDICT is `COMPLETED`, POST_VERIFY MUST contain at least one
  `[PASS]` and no `[FAIL]`.
- Never wrap the block in JSON, never abbreviate the field names,
  never omit a section. If a section is empty, write `(none)`.

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `BLOCKED` | One or more pre-checks failed (agent activation key missing/failed, source unreachable from agent, destination write-denied, IAM task role missing source-read or destination-write, KMS encrypt gap on SSE-KMS destination, cross-account destination bucket policy missing DataSync principal, Options mismatch like `PosixPermissions PRESERVE` on SMB destination, `ScheduleExpression` past 1-year horizon, bandwidth-throttle value exceeds agent uplink, destination EFS/FSx in WRONG AZ vs agent subnet) | List failures, do NOT execute |
| `READY` | All pre-checks passed; awaiting CONFIRM gate | Emit exact CLI sequence, wait for operator yes |
| `COMPLETED` | Task execution reached `Status: SUCCESS` AND post-verification passed (`FilesTransferred == EstimatedFilesToTransfer`, `VerificationFilesFailed == 0` when `VerifyMode != NONE`, destination spot-check object exists with expected size and mtime) | Emit verification results, monitoring plan |

**Priority order for pre-checks (apply in this sequence, all must pass
for READY):**

1. **Agent activation + reachability.** Agent ARN exists,
   `LastConnectionTime` recent (< 5 min), `Status: ONLINE`.
2. **Source location readable by agent.** Self-managed sources
   (NFS/SMB/HDFS/Object Storage): agent subnet/SG can reach source
   server's IP/FQDN on the right port (2049 NFS, 445 SMB, 8020/50070
   HDFS NameNode, 443/80 object storage). AWS sources (S3): IAM role
   has `s3:GetObject` + `s3:ListBucket`.
3. **Destination location writable.** S3: IAM role has
   `s3:PutObject`, `s3:ListBucketMultipartUploads`,
   `s3:AbortMultipartUpload`, `s3:GetObject` (for verify). EFS/FSx:
   file-system-specific write permissions and file system policy
   allows DataSync service principal.
4. **IAM task role trust + permissions.** Role trusts
   `datasync.amazonaws.com` and has the read-on-source +
   write-on-destination chain. Cross-account destinations need the
   destination bucket policy to allow the source account's role.
5. **KMS encrypt path on destination.** SSE-KMS destinations require
   `kms:Encrypt` + `kms:GenerateDataKey` on the destination key AND
   the destination key policy must grant the role.
6. **Options consistency.** `PosixPermissions: PRESERVE` requires a
   POSIX-preserving destination (EFS, FSx for OpenZFS, FSx for
   Lustre, S3 with bucket-owner-enforced). SMB sources need
   `SecurityDescriptorCopyFlags` set. SMB destinations cannot
   preserve POSIX.
7. **Schedule expression validity.** `ScheduleExpression` is a valid
   `at(...)` or `rate(...)` within the 1-year task-schedule horizon.
   `ScheduleStatus: ENABLED` requires the expression be set.
8. **Bandwidth-throttle feasibility.** `BandwidthLimitInMb` does not
   exceed the agent's provisioned uplink (typical VM agent ~10 Gbps;
   EC2 agents bounded by instance-type network caps).
9. **Destination file system state.** EFS: `available`, not
   `updating`. FSx: `AVAILABLE`, agent subnet has a mount target or
   reachable route.
10. **Task Reports configuration.** If reports requested,
    `S3BucketArn` for reports exists and task role has
    `s3:PutObject` on the report bucket.

**Cost/time baselines (2026):**

- Transfer throughput per agent: ~10 Gbps saturated for a single
  task on a dedicated VM with NVMe; 1-3 Gbps typical on EC2
  c5.2xlarge.
- Verify pass overhead: `POINT_IN_TIME_CONSISTENT` adds 5-15% wall
  time on the first run; `ONLY_FILES_TRANSFERRED` is fastest for
  incremental runs.
- DataSync pricing: $0.0125/GB for transfers in + out of AWS (US
  regions); Snowball Edge transfers billed separately.
- Discovery job: 14- or 28-day collection window; recommendation
  reports available within 4 hours of completion.

## Mindset

**One-line takeaway:** A DataSync task with `Status: AVAILABLE` is a
*registration*, not proof of a successful transfer. A task is only
"done" once `describe-task-execution` returns `Status: SUCCESS`,
`FilesTransferred == EstimatedFilesToTransfer`, and the verify pass
shows zero failed files (when `VerifyMode != NONE`). Driven by three
DataSync realities:

- **DataSync is an agent-mediated async pipeline.** The agent (or
  agents) running in the source or destination VPC performs the
  actual read/write. AWS schedules execution on the agent; the
  control-plane API (`start-task-execution`) returns immediately with
  a `TaskExecutionArn`. Failures in the agent, source location, or
  destination location surface only in `describe-task-execution` and
  the task's `ErrorCode`/`ErrorDetail` fields — never on the task's
  own `Status` field.
- **`VerifyMode` is a separate pass, not a transfer property.** With
  `POINT_IN_TIME_CONSISTENT`, DataSync re-scans source and destination
  after transfer, comparing checksums and metadata. With
  `ONLY_FILES_TRANSFERRED`, verify runs only on the files just moved.
  `NONE` skips verification entirely — fast but unsafe; never use for
  compliance-driven migrations.
- **The destination file system or bucket must be writable AS the
  DataSync service.** For EFS, the file system policy must allow
  `elasticfilesystem:ClientMount`, `ClientWrite`, `ClientRootAccess`.
  For cross-account S3, the destination bucket policy must allow the
  source account's task role. Missing either surfaces as a misleading
  `AccessDenied (403)` only visible in the task execution error
  detail.

## Pre-flight: source + destination metadata gate

Run before classification. Misclassifying these produces wrong plans.

**Pagination:** `list-locations` paginates at 100.
`list-task-executions` paginates at 100 by default, sorted descending
by `StartTime`. `describe-task-execution` returns the full execution
detail.

**Live-account pre-flight (skip if offline plan audit):**
1. `aws datasync list-agents` — confirm an agent exists, capture
   `AgentArn`. `describe-agent` returns `LastConnectionTime`,
   `Status`. Anything older than 5 minutes or `Status != ONLINE`
   is BLOCKED.
2. `aws datasync list-locations` — find source and destination
   `LocationArn` and capture their `LocationUri` and `LocationType`.
3. For S3 sources: `aws s3api get-bucket-location`,
   `get-bucket-encryption`, `get-bucket-versioning`.
4. For S3 destinations: same set as #3, plus `get-bucket-policy`
   (cross-account), `get-bucket-ownership-controls`.
5. For EFS destinations: `aws efs describe-file-systems`,
   `describe-mount-targets` — confirm `available` and a mount target
   exists in the agent's subnet.
6. For FSx family destinations: `aws fsx describe-file-systems` and
   the file-system-specific describe call. Confirm `Lifecycle:
   AVAILABLE` and the agent subnet has network reachability.
7. `aws iam list-attached-role-policies --role-name <task-role>` and
   `list-role-policies` — verify the task role's permission chain.
8. `aws kms describe-key --key-id <destination-key>` — confirm
   `Enabled` and key policy grants the task role.
9. `aws datasync describe-task --task-arn <task>` — capture
   `CurrentTaskExecutionArn`, `Status`, `Options`, `Schedule`.
10. `aws datasync describe-task-execution --task-execution-arn <arn>`
    for the most recent execution — capture `Status`,
    `BytesTransferred`, `FilesTransferred`, `EstimatedFilesToTransfer`,
    `VerificationFilesFailed`, `ErrorCode`, `ErrorDetail`.
11. For discovery: `aws datasync list-discovery-jobs` — confirm no
    in-flight discovery job covers the same storage system.

**Malformed input:** if the input JSON is invalid or missing required
fields, emit `VERDICT: ERROR` with `REASON: Task/location configuration
is not valid JSON or is missing required fields — cannot plan.` and
`REMEDIATION: Re-fetch with aws datasync describe-task --task-arn
<task> --output json and re-plan.`

| Location attribute | Effect on operation |
|---|---|
| Agent `Status: OFFLINE` | create-task BLOCKED. Existing tasks fail execution. |
| Agent `LastConnectionTime` > 5 min ago | Activation may have expired or network is broken. |
| Source `LocationType: NFS` but server unreachable from agent subnet | BLOCKED; verify security group + route table. |
| SMB source missing `SMBUser`/`SMBPassword` secret ARN | BLOCKED; create AWS Secrets Manager secret and re-create location. |
| HDFS source missing `NameNodes` list | BLOCKED; re-create `create-location-hdfs` with valid NameNodes. |
| Object Storage missing `ServerHostname`/`BucketName`/`AccessKey`/`SecretKey` | BLOCKED; re-create with valid endpoint. |
| S3 destination SSE-KMS but role missing `kms:GenerateDataKey` | BLOCKED; attach KMS permissions to task role. |
| Destination EFS `LifeCycle: DELETING` | BLOCKED; pick a new destination. |
| Destination FSx `Lifecycle: MISCONFIGURED` | BLOCKED; resolve FSx config first. |
| Destination FSx for NetApp ONTAP SVM not reachable via agent subnet | BLOCKED; verify mount target or VPC peering. |
| Destination S3 `ObjectOwnership: ObjectWriter` (legacy) with cross-account task | Replicas owned by source account; update to `BucketOwnerEnforced`. |
| `Options.PosixPermissions: PRESERVE` on SMB destination | BLOCKED; SMB does not preserve POSIX. Use `BEST_EFFORT` or `NONE`. |
| `Options.Atime: BEST_EFFORT` on S3 destination | S3 does not track atime; field silently ignored. |
| `at(...)` past 1 year | BLOCKED; schedule horizon is 1 year. |
| `BandwidthLimitInMb: 50000` exceeds agent uplink | BLOCKED; throttle must be <= agent uplink capacity. |
| Task `Status: RUNNING` with new `start-task-execution` | BLOCKED; only one execution per task concurrently. Queue or wait. |
| `VerifyMode: NONE` on compliance migration | Surface as a WARNING; never silently allow. |
| `TransferMode: ALL` on a delta sync task | Forces re-copy of all matching objects; cost/time impact. |

## Process — operation planning (apply in order)

### Step 0: Expert knowledge — non-obvious DataSync behaviors

These behaviors are easy to misjudge without operational DataSync
experience. Each changes a plan if ignored. (See
`references/task-options-and-failure-modes.md` for the full Options
reference and per-source-type setup details.)

- **An agent is mandatory for self-managed sources.** NFS, SMB, HDFS,
  Object Storage sources REQUIRE a DataSync agent (VM on-prem, or EC2
  in a connecting VPC). AWS-native sources (S3) can be read directly
  when both source and destination are in AWS. The agent is activated
  via `create-agent --activation-key` (key fetched from the agent's
  local console at `http://<agent-ip>`, valid 24 hours).

- **`VerifyMode: POINT_IN_TIME_CONSISTENT` re-reads source AND
  destination after transfer.** Compares metadata + checksums of
  EVERY file in scope, not just transferred files. For 50 TB this
  adds hours. Use `ONLY_FILES_TRANSFERRED` for delta syncs.

- **`TransferMode: CHANGED` (default) is delta, not full.** Copies
  everything on the first run (no baseline), but subsequent runs only
  copy new/modified files. For forced re-copy, use `TransferMode:
  ALL`.

- **`OverwriteMode: NEVER` does NOT skip the file silently — it
  errors or warns.** To skip-when-exists, use `OverwriteMode: NEVER`
  + `TransferMode: CHANGED` together. To always overwrite, use
  `ALWAYS` (default).

- **PosixPermissions preservation depends on destination type.**
  EFS, FSx for OpenZFS, FSx for Lustre preserve POSIX natively. FSx
  for Windows and SMB shares do NOT — use `BEST_EFFORT` or `NONE`.
  S3 destinations store POSIX metadata in object metadata when
  `PRESERVE` is set; the S3 API itself does not enforce it.

- **SMB sources require a Secrets Manager secret for credentials.**
  `create-location-smb` takes `SMBUser` and references a secret ARN
  for the password. Task role needs `secretsmanager:GetSecretValue`.
  Hard-coded passwords NOT supported.

- **Bandwidth throttling is per-agent, not per-task.** Two tasks on
  one agent with `BandwidthLimitInMb: 1000` share the 1,000 Mb cap.
  Schedule sequentially if total bandwidth is a hard cap.

- **Task schedules auto-disable after 1 year.** `ScheduleExpression`
  uses EventBridge-like `rate`/`at` syntax but the schedule stops
  firing after 1 year. Re-arm annually or move the trigger to
  EventBridge calling `start-task-execution`.

- **EFS destination MUST be in the same AZ as the agent subnet (or
  have a mount target there).** Cross-AZ EFS access works but incurs
  cross-AZ charges; Single-AZ FSx requires same-AZ.

- **FSx for NetApp ONTAP destinations require a Storage Virtual
  Machine (SVM).** `create-location-fsx-ontap` takes
  `StorageVirtualMachineArn`. The SVM's inter-cluster endpoint or
  VPC route must be reachable from the agent subnet.

- **DataSync Discovery is read-only.** A discovery job connects to
  the on-prem storage (NFS or SMB), collects 14- or 28-day metrics,
  emits recommendations. It does NOT migrate data.

- **Task Reports are written to an S3 bucket.** Configure via
  `update-task` with `S3BucketArn`, `ReportLevel` (`ERRORS_ONLY |
  SUCCESSES_AND_ERRORS`), optional `ReportCode` filters. Per-file
  JSON Lines emitted after each execution.

- **A task can only have ONE in-flight execution at a time.**
  `start-task-execution` while `Status: RUNNING` errors. Use
  `Includes`/`Excludes` filters on multiple tasks to parallelize.

- **`DeleteOnDelete` (2024) controls source-side delete mirroring.**
  Default FALSE — files deleted on source between runs do NOT
  propagate to destination. Set TRUE for true-mirror semantics.

- **`StartTaskExecution` overrides do NOT persist.** Only the task's
  `Options` block is the source of truth. For a permanent change use
  `update-task`.

### Step 1: Pre-check gate — BLOCKED if any check fails

Run ALL pre-checks for the chosen operation. If ANY fails, the verdict
is BLOCKED with the failed checks in PRE_CHECKS. Do NOT execute.

**For ALL operations:**
1. Task ARN exists (or operator is creating new) in the expected
   account/Region.
2. Agent ARN exists, `Status: ONLINE`, `LastConnectionTime` < 5 min
   ago (skip for S3-to-S3 in same Region without agent).
3. Source and destination locations exist and match the operator's
   intended URIs.
4. Task IAM role trusts `datasync.amazonaws.com` and has the
   read-on-source + write-on-destination permission chain.

**For create-task (new `create-task`):**
5. Source location `LocationArn` exists, `LocationType` matches
   operator's claim.
6. Destination location `LocationArn` exists, `LocationType` matches.
7. IAM task role has source-side read (e.g., `s3:GetObject` for S3
   source, agent-credential-derived access for self-managed).
8. IAM task role has destination-side write (e.g., `s3:PutObject`
   for S3, `elasticfilesystem:ClientWrite` for EFS).
9. (SSE-KMS destination) IAM role has `kms:Encrypt`,
   `kms:GenerateDataKey`; destination key policy grants the role.
10. (Cross-account S3 destination) Destination bucket policy allows
    the source account's task role.
11. Options consistency: `PosixPermissions: PRESERVE` only on POSIX
    destinations; `SecurityDescriptorCopyFlags` set for SMB;
    `VerifyMode != NONE` for compliance migrations.
12. (Task Reports) Report bucket exists and the task role has
    `s3:PutObject` on it.

**For deploy-agent:** activation key non-empty and < 24h old; agent
VM/EC2 has outbound HTTPS (443) to DataSync endpoints; agent
subnet/SG can reach source location or destination VPC; (cross-Region
or cross-account) VPC peering/TGW/PrivateLink to destination subnet;
IAM role for the agent has `datasync:*` and source-reading
permissions.

**For update-task-options:** task `Status: AVAILABLE` (not RUNNING);
new `Options` block is internally consistent (see Step 0); pre-state
captured (full prior `Options`).

**For create-schedule:** task ARN exists; `ScheduleExpression` is
valid EventBridge `rate`/`at` syntax within 1-year horizon;
(bandwidth throttle) `BandwidthLimitInMb` <= agent uplink.

**For diagnose-failing-execution (read-only, no BLOCKED gate):** read
the failure-mode table to identify the root cause from `ErrorCode` +
`ErrorDetail`.

**For run-discovery:** on-prem storage reachable from the discovery
agent; no in-flight discovery job covers the same storage system;
collection window (14 or 28 days) set explicitly.

**For transfer-to-fsx-ontap:** FSx for NetApp ONTAP file system
`AVAILABLE`; SVM exists and inter-cluster endpoint reachable from
agent; agent subnet has route to SVM endpoint; task role has
`fsx:CreateMountTarget`, `fsx:DescribeFileSystems`, plus the
ONTAP-specific permissions.

**For configure-task-reports:** reports S3 bucket exists in same
Region; task role has `s3:PutObject` on the reports bucket;
`ReportLevel` is one of `ERRORS_ONLY`, `SUCCESSES_AND_ERRORS`.

**DataSync failure-mode table (use during diagnose-failing-execution):**

| Symptom (`ErrorCode` / Status) | Root cause | Fix |
|---|---|---|
| `Status: ERROR`, `ErrorDetail: "Agent is offline"` | Agent VM/EC2 unreachable or stopped | `describe-agent`; restart VM; verify outbound HTTPS 443 to DataSync endpoints. |
| `ErrorDetail: "AccessDenied for s3:PutObject on <dest>"` | Task role missing `s3:PutObject` on destination | Attach policy granting `s3:PutObject` on `arn:aws:s3:::<dest>/*` |
| `ErrorDetail: "Mount target not found"` | EFS/FSx in wrong AZ vs agent subnet | Re-create agent in matching AZ or add mount target in agent subnet |
| `ErrorDetail: "SMB login failed"` | SMB secret expired or rotated | Update Secrets Manager secret; re-create SMB location |
| `ErrorDetail: "KMS key policy does not grant role"` | Destination KMS key policy missing task role | Add `kms:Encrypt`, `kms:GenerateDataKey` grant on destination key policy |
| `VerificationFilesFailed > 0` | Source/destination checksums differ after transfer | Re-run with `VerifyMode: POINT_IN_TIME_CONSISTENT` + `TransferMode: CHANGED`; if persists, investigate destination write path |
| `Status: TRANSFERRING` forever, `BytesTransferred` flat | Network bottleneck, throttling, source saturated | Check `BandwidthLimitInMb`, agent CPU, source disk I/O. Increase agent size or remove throttle. |
| `FilesTransferred` < `EstimatedFilesToTransfer`, `Status: SUCCESS` | Some files skipped via `Includes`/`Excludes` filter (verify intent); if no filter, permission-denied on specific files | Inspect Task Report; widen task role permissions. |
| `Status: LAUNCHING` > 30 min | Agent capacity exhausted (too many queued executions) | Wait; or reduce concurrent tasks on this agent. |

### Step 2: READY — emit operation plan

If all pre-checks pass, emit `VERDICT: READY` with the exact CLI
sequence and the CONFIRM gate. The plan includes:

- The exact AWS CLI command with all flags populated from the source
  + destination configuration. For `create-task` this includes the
  full `--options` JSON and the `--cloud-watch-log-group-arn` if
  specified.
- Expected throughput (10 Gbps ceiling for a single VM agent;
  c5.2xlarge ~2 Gbps typical).
- Expected verify-mode overhead (5-15% extra wall time for
  POINT_IN_TIME_CONSISTENT).
- The CONFIRM gate prompt.
- The monitoring step (describe-task-execution poll until Status
  reaches SUCCESS or ERROR).

### Step 3: Execute behind CONFIRM gate

- **MANDATORY CONFIRMATION GATE.** Before any state-changing CLI
  (`create-task`, `update-task`, `start-task-execution`,
  `update-task-schedule`, `create-agent`, `delete-task`), emit:
  `CONFIRM: About to <operation> on task <task> in account <account>
  region <region>. This will <consequence>. Proceed? (yes/no)`. Do
  NOT execute until the operator confirms.
- Capture pre-state for rollback: `aws datasync describe-task
  --task-arn <task> --output json > /tmp/<task>-pre-$(date +%s).json`.
- Execute the CLI. For `start-task-execution`, the API returns a
  `TaskExecutionArn` immediately; the transfer runs asynchronously
  on the agent.
- Poll the execution:
  `aws datasync describe-task-execution --task-execution-arn <arn>`
  every 60 seconds (or longer for big transfers). Surface
  `BytesTransferred`, `BytesWritten`, `EstimatedFilesToTransfer`,
  `FilesTransferred`, `VerificationFilesFailed`.

### Step 4: Post-verification — COMPLETED

After execution reaches `Status: SUCCESS`, run post-verification. ALL
checks must pass for `COMPLETED`.

1. Confirm `FilesTransferred == EstimatedFilesToTransfer` (unless
   `Includes`/`Excludes` filters intentionally subset the scope).
2. For `VerifyMode != NONE`: confirm `VerificationFilesFailed == 0`
   and `VerificationFilesTransferred == FilesTransferred`.
3. Spot-check 3 random files on the destination via `head-object` /
   `ls` on the file system. Compare size and mtime to source.
4. For S3 destination: confirm `ETag` matches (or differs only by
   multipart-ETag format).
5. For EFS/FSx destination: confirm POSIX permissions preserved when
   `PosixPermissions: PRESERVE` was set.
6. For scheduled tasks: confirm next-run `NextRunTime` is set under
   `Schedule`.
7. For Task Reports: confirm the report object exists at
   `<report-bucket>/<task-id>/<execution-id>/reports/`.

If ANY verification fails, emit `VERDICT: ERROR` with the failure
details — do not claim COMPLETED. Route the failure back to
diagnose-failing-execution.

## Output format (per operation)

See § STRICT output contract above. The block MUST appear exactly in
that shape.

### Worked example — create-task (NFS -> S3, VERIFY + schedule)

```text
OPERATION: create-task
VERDICT: READY
TARGET: nfs://10.0.10.20/vol/data -> s3://prod-migration-archive-2026
        (task: new — "nfs-to-s3-archive")
PRE_CHECKS:
  - [PASS] Agent arn:aws:datasync:us-east-1:111111111111:agent/agent-001
    Status: ONLINE, LastConnectionTime: 2026-08-10T22:00:00Z
  - [PASS] Source location LocationType: NFS, URI: nfs://10.0.10.20/vol/data
  - [PASS] Destination location LocationType: S3, URI: s3://prod-migration-archive-2026
  - [PASS] IAM role arn:aws:iam::111111111111:role/datasync-task-role
    trusts datasync.amazonaws.com
  - [PASS] Task role has s3:PutObject, s3:GetObject, s3:ListBucket,
    s3:AbortMultipartUpload on prod-migration-archive-2026
  - [PASS] Task role has kms:Encrypt, kms:GenerateDataKey on
    arn:aws:kms:us-east-1:111111111111:key/dest-cmk
  - [PASS] Destination key policy grants role
  - [PASS] Options.VerifyMode: POINT_IN_TIME_CONSISTENT
    Options.PosixPermissions: PRESERVE (S3 destination stores POSIX
    metadata in object metadata)
  - [PASS] ScheduleExpression: rate(1 day) within 1-year horizon
  - [PASS] BandwidthLimitInMb: 1000 <= agent uplink (10 Gbps)
STEPS:
  1. CONFIRM: About to create DataSync task "nfs-to-s3-archive"
     in account 111111111111 region us-east-1. Source:
     nfs://10.0.10.20/vol/data. Destination:
     s3://prod-migration-archive-2026 (SSE-KMS, key dest-cmk).
     VerifyMode: POINT_IN_TIME_CONSISTENT. Schedule: daily.
     Bandwidth throttle: 1000 Mb/s. First execution transfers
     ~12 TB. Proceed? (yes/no)
  2. aws datasync create-task \
       --source-location-arn arn:aws:datasync:us-east-1:111111111111:location/loc-001 \
       --destination-location-arn arn:aws:datasync:us-east-1:111111111111:location/loc-042 \
       --name nfs-to-s3-archive \
       --cloud-watch-log-group-arn arn:aws:logs:us-east-1:111111111111:log-group:/aws/datasync/nfs-to-s3 \
       --options file:///tmp/datasync-options.json \
       --schedule-expression "rate(1 day)" \
       --tags Key=env,Value=prod Key=pipeline,Value=migration
  3. aws datasync start-task-execution --task-arn <new-task-arn>
  4. aws datasync describe-task-execution --task-execution-arn <exec-arn>
POST_VERIFY: (pending execution)
NOTES:
  - First execution performs a FULL transfer (TransferMode: CHANGED
    with no prior baseline). Subsequent executions on the daily
    schedule are delta-only.
  - VerifyMode POINT_IN_TIME_CONSISTENT adds 5-15% wall time after
    the transfer phase. For 12 TB expect ~24-36h on a 1 Gbps throttle.
  - Task Reports NOT configured — recommend update-task with reports
    bucket for compliance evidence.
  - Destination KMS key policy MUST list the task role; verify with
    aws kms get-key-policy --key-id dest-cmk --policy-name default
    before the first execution.
```

### Worked example — diagnose-failing-execution (BLOCKED with fix)

```text
OPERATION: diagnose-failing-execution
VERDICT: BLOCKED
TARGET: nfs://10.0.10.20/vol/data -> s3://prod-migration-archive-2026
        (task: nfs-to-s3-archive)
PRE_CHECKS:
  - [PASS] Task exists, Status: AVAILABLE
  - [PASS] Agent Status: ONLINE, LastConnectionTime recent
  - [PASS] Source location reachable from agent subnet
  - [FAIL] Latest execution Status: ERROR
    ErrorDetail: "AccessDenied (403) for s3:PutObject on
    arn:aws:s3:::prod-migration-archive-2026/logs/app.log" — the
    task role arn:aws:iam::111111111111:role/datasync-task-role
    is missing s3:PutObject on the destination bucket.
  - [PASS] KMS grants verified
STEPS: (none — pre-checks failed)
POST_VERIFY: (none)
NOTES:
  - Root cause: task role datasync-task-role is missing
    s3:PutObject on prod-migration-archive-2026. DataSync
    executions partially completed (2.1 TB of 12 TB) before
    failing; partially-transferred objects exist on the destination.
  - Fix: attach a policy granting s3:PutObject,
    s3:AbortMultipartUpload, s3:GetObject, s3:ListBucket on
    arn:aws:s3:::prod-migration-archive-2026/* to the task role,
    then re-run:
    aws iam attach-role-policy --role-name datasync-task-role \
      --policy-arn arn:aws:iam::111111111111:policy/datasync-dest-write
    aws datasync start-task-execution \
      --task-arn arn:aws:datasync:us-east-1:111111111111:task/task-001 \
      --override-options file:///tmp/datasync-options-verify-all.json
  - Set TransferMode: CHANGED on the override; the prior partial
    transfer leaves a baseline so only the failed files re-transfer.
    Do NOT use TransferMode: ALL unless you want to re-copy 12 TB.
```

### Worked example — transfer-to-fsx-ontap (COMPLETED)

```text
OPERATION: transfer-to-fsx-ontap
VERDICT: COMPLETED
TARGET: smb://10.0.20.30/share/finance -> fsxn://fs-0abc123/vol1/finance
        (task: smb-to-fsxn-finance)
PRE_CHECKS:
  - [PASS] Agent Status: ONLINE
  - [PASS] FSx for NetApp ONTAP fs-0abc123 Lifecycle: AVAILABLE
  - [PASS] SVM svm-0456 inter-cluster endpoint reachable from
    agent subnet 10.0.30.0/24
  - [PASS] Task role has fsx:CreateMountTarget,
    fsx:DescribeFileSystems on fs-0abc123
  - [PASS] SMB source secret smb-cred-finance valid in Secrets Manager
  - [PASS] Options.SecurityDescriptorCopyFlags: OWNER_DACL
    Options.VerifyMode: POINT_IN_TIME_CONSISTENT
STEPS:
  1. CONFIRM: About to create task "smb-to-fsxn-finance"
     transferring smb://10.0.20.30/share/finance to
     fsxn://fs-0abc123/vol1/finance. Proceed? (yes/no)
  2. aws datasync create-location-smb ...
  3. aws datasync create-location-fsx-ontap ...
  4. aws datasync create-task --source-location-arn <smb-loc> \
       --destination-location-arn <ontap-loc> \
       --name smb-to-fsxn-finance --options file:///tmp/options.json
  5. aws datasync start-task-execution --task-arn <task-arn>
POST_VERIFY:
  - [PASS] Latest execution Status: SUCCESS
  - [PASS] FilesTransferred: 48,231 == EstimatedFilesToTransfer: 48,231
  - [PASS] VerificationFilesFailed: 0
  - [PASS] Spot-check: \\fsx\vol1\finance\2026\Q3.xlsx size matches
    SMB source (4.2 MB), mtime within 1 second
  - [PASS] ACL on \\fsx\vol1\finance\2026 preserves OWNER_DACL
    per SecurityDescriptorCopyFlags
NOTES:
  - FSx for NetApp ONTAP SVM must remain reachable for future
    delta syncs. CloudWatch alarm on SVM inter-cluster endpoint
    reachability recommended.
  - VerifyMode POINT_IN_TIME_CONSISTENT confirmed zero checksum
    mismatches after the 48,231-file transfer.
  - Re-run scheduled: set ScheduleExpression: rate(1 day) and
    TransferMode: CHANGED for nightly delta sync.
```

## Anti-Patterns — NEVER

- NEVER assume `Status: AVAILABLE` on a DataSync task means data is
  transferred. The task only declares it is ready to execute; the
  only proof of transfer is a `describe-task-execution` returning
  `Status: SUCCESS` and `FilesTransferred == EstimatedFilesToTransfer`.
  Always verify with an explicit execution result check.

- NEVER use `VerifyMode: NONE` for compliance-driven migrations. The
  speed gain is not worth the loss of integrity verification.
  Compliance audits require `POINT_IN_TIME_CONSISTENT` or
  `ONLY_FILES_TRANSFERRED`.

- NEVER set `PosixPermissions: PRESERVE` on an SMB destination. SMB
  does not preserve POSIX metadata; the execution will fail or
  silently drop the metadata. Use `BEST_EFFORT` or `NONE`, or pick
  a POSIX-preserving destination (EFS, FSx for OpenZFS).

- NEVER share an agent across more tasks than its throughput can
  sustain. Bandwidth throttle is per-agent, not per-task; scheduling
  three concurrent 1 Gbps tasks on a 1 Gbps-throttled agent starves
  them all.

- NEVER assume a `rate(2 days)` schedule survives forever. DataSync
  schedules auto-disable after 1 year. Re-arm annually or move the
  trigger to EventBridge calling `start-task-execution`.

- NEVER set `BandwidthLimitInMb` higher than the agent's provisioned
  uplink. The cap is enforced on the agent; setting it higher does
  not buy throughput, it just removes the throttle.

- NEVER call `start-task-execution` on a task that is already
  `Status: RUNNING`. The API errors with a "task already running"
  condition. Use `Includes`/`Excludes` filters on multiple tasks to
  parallelize instead.

- NEVER assume `TransferMode: CHANGED` does a full copy on every
  run. It copies everything on the first run (no baseline) but
  subsequent runs only copy new/modified files. For a forced re-copy,
  use `TransferMode: ALL`.

- NEVER use a single cross-account destination S3 bucket without a
  bucket policy explicitly granting the source account's task role.
  IAM identity-based policy on the task role is necessary but not
  sufficient.

- NEVER forget the SMB secret. `create-location-smb` requires an
  AWS Secrets Manager secret ARN for the SMB password. Hard-coded
  passwords are not supported.

- NEVER re-create a discovery job for the same on-prem storage
  system while one is in flight. The two jobs will compete for
  metrics collection and produce inconsistent recommendations.

- NEVER auto-execute a state-changing DataSync CLI without the
  CONFIRM gate. `delete-task`, `update-task`, and
  `start-task-execution` all have irreversible side effects.

- NEVER skip capturing pre-state before `update-task` or
  `update-task-schedule`. The prior Options and Schedule are
  overwritten with no undo.

- NEVER assume destination EFS is in the same AZ as the agent.
  Cross-AZ EFS access works but incurs cross-AZ charges; Single-AZ
  EFS requires same-AZ mount target.

- NEVER rely solely on the task's `Status` field for migration
  completeness. Read `describe-task-execution` for every execution.

- NEVER deploy an on-prem agent without verifying outbound HTTPS
  (443) to DataSync endpoints. The activation key fetch succeeds
  locally but the agent will not be able to register with DataSync
  control plane.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`create-task`, `update-task`, `start-task-execution`,
  `delete-task`, `create-agent`, `update-task-schedule`,
  `start-discovery-job`), emit: `CONFIRM: About to <operation> on
  <task> in account <account> region <region>. This will
  <consequence>. Proceed? (yes/no)`. Do NOT execute until the
  operator confirms.

- **Capture pre-state for rollback.** Before any task change:
  `aws datasync describe-task --task-arn <task> --output json >
  /tmp/<task>-pre-$(date +%s).json`. This is the only rollback path
  — `update-task` is full-replacement of `Options`.

- **Verify agent health before any execution.** An offline agent
  produces `Status: LAUNCHING` indefinitely on the execution; the
  diagnostic surface for that is poor. Check `describe-agent`
  `LastConnectionTime` < 5 min ago.

- **Verify KMS key policies, not just IAM.** Cross-account KMS
  requires the destination key policy to grant the task role. IAM
  alone is not sufficient.

- **Verify the destination bucket policy for cross-account S3.**
  Check for `s3:PutObject` grant with the source account condition.
  Without it, the task fails partway through with a misleading
  AccessDenied.

- **Prefer additive changes over destructive ones.** Adding a new
  task is reversible; deleting a task loses all execution history
  and Task Reports.

- **Validate `Includes`/`Excludes` filter scope before applying.**
  An empty filter transfers everything under the source location.
  Confirm intent — cost/time scales with bytes scanned.

## Expert heuristic: the false-green task

DataSync is async and eventually-consistent. The single highest-
leverage rule for operating it safely is:

> A DataSync task with `Status: AVAILABLE` is a REGISTRATION claim,
> not a DELIVERY claim. The only proof of a successful transfer is a
> `describe-task-execution` returning `Status: SUCCESS`,
> `FilesTransferred == EstimatedFilesToTransfer`, and (when
> `VerifyMode != NONE`) `VerificationFilesFailed == 0`. Treat any
> dashboard that shows "task AVAILABLE" as a health signal worth
> less than a single end-to-end execution check.

**Why this rule exists:** DataSync evaluates the task asynchronously
after `start-task-execution` returns. Failures in the agent, source
location, destination location, IAM role, KMS key policy, or
destination bucket policy do NOT fail the task creation — the task
remains `AVAILABLE`. The execution `Status` is the only signal of
actual transfer success; the task's own `Status` field is decoupled.

**Concrete verification techniques:**

| Technique | Mechanism | What it proves |
|---|---|---|
| `describe-task-execution` poll until terminal | Tail `Status`, `BytesTransferred`, `FilesTransferred` | End-to-end execution reached SUCCESS or ERROR |
| `VerificationFilesFailed == 0` (when VerifyMode != NONE) | Built-in checksum + metadata verify pass | Source and destination are byte-identical for the transferred scope |
| Spot-check via `head-object` (S3) or `ls`/`stat` (file) | Sample 3-5 random files | Independent confirmation beyond aggregate counters |
| Task Reports (per-file JSON) | Filter for `TransferStatus: ERROR` rows | Per-file failure attribution |
| CloudWatch Logs `/aws/datasync/<task>` | Filter for `Transfer` log level | Detailed agent-side diagnostics |
| `BytesWritten` vs `BytesTransferred` divergence | Compare after SUCCESS | Compression or partial-write detection |

**Three-point verification protocol (apply on every new task):**

1. **Execution status:** poll `describe-task-execution` until
   `Status` is `SUCCESS`. `ERROR` is a hard fail. `TRANSFERRING`
   for > 24h on a small dataset is suspicious.
2. **Counter alignment:** `FilesTransferred == EstimatedFilesToTransfer`
   (unless `Includes`/`Excludes` filters narrow the scope). If
   `FilesTransferred < Estimated`, inspect Task Reports for skipped
   files (often permission-denied).
3. **Verify-mode confirmation (when VerifyMode != NONE):**
   `VerificationFilesTransferred == FilesTransferred` AND
   `VerificationFilesFailed == 0`. A non-zero `VerificationFilesFailed`
   means checksum mismatch — re-run with `TransferMode: CHANGED`.

**Surface in the output:** for any task change, include
`DELIVERY_STATUS: <verified | pending | failed>` and the latest
execution's `FilesTransferred` vs `EstimatedFilesToTransfer`. If
`DELIVERY_STATUS` is not `verified`, do NOT mark the operation
COMPLETED.

**Detection of silent transfer failure post-deploy:** CloudWatch
alarm on `Status == ERROR` for any execution in the task's log group
AND a daily scheduled Lambda that calls `describe-task-execution`
for the latest execution and verifies `Status == SUCCESS`. The daily
check catches executions that the CloudWatch alarm missed (e.g.,
when the alarm was misconfigured).

## Recent AWS features (2024-2026)

- **FSx for NetApp ONTAP destination support (2023 GA, enhanced
  2024-2025):** `create-location-fsx-ontap` accepts an SVM ARN; the
  SVM's inter-cluster endpoint or VPC route must be reachable from
  the agent. Supports SMB and NFS protocols on the destination.

- **DataSync Discovery (2023 GA, expanded 2024-2025):** Run a 14- or
  28-day discovery job against an on-prem NFS or SMB storage system
  to collect capacity, performance, and file-type metrics. Produces
  recommendations for right-sizing the AWS destination and
  identifying cold data. Discovery is read-only — no migration.

- **Task Reports (2023 GA, filters expanded 2024):** Per-file JSON
  reports after each execution, written to an S3 bucket.
  Configurable `ReportLevel`: `ERRORS_ONLY` or
  `SUCCESSES_AND_ERRORS`. Optional `ReportCode` filters (e.g.,
  `TRANSFER_ERROR`, `VERIFY_CATEGORY`, `DELETE_SKIP`).

- **`DeleteOnDelete` Option (2024):** When TRUE, files deleted on
  source between executions are also deleted on destination — true
  mirror semantics. Default is FALSE (deletions on source do not
  propagate), preserving destination as a backup.

- **Object Storage location type (2023 GA, S3-compatible + Alibaba
  OSS 2024):** `create-location-object-storage` for non-AWS S3-
  compatible systems. Specify `ServerHostname`, `BucketName`,
  `AccessKey`, `SecretKey`, `ServerProtocol`.

- **Bandwidth throttle per-task override (2024):**
  `start-task-execution --overrides BandwidthLimitInMb` allows
  per-execution bandwidth caps without changing the task's default.
  Useful for off-hours bulk transfers.

- **HDFS source GA (2022, Kerberos refined 2024):**
  `create-location-hdfs` with `NameNodes` list, `AuthenticationType:
  SIMPLE | KERBEROS`, optional `KerberosPrincipal`/keytab.

- **DataSync on Snowball Edge (2024):** Snowball Edge supports a
  DataSync agent for air-gapped migration. Activate the agent locally
  on the Snowball; ship the device to AWS; DataSync ingests from the
  Snowball into S3.

- **Multi-Agent tasks (2024-2025):** A single task can leverage
  multiple agents for parallel throughput (scales beyond a single
  agent's 10 Gbps ceiling). Configure at the task level via the
  console or CLI `--agent-arns` (list).

- **CloudWatch Metrics for DataSync (2024):**
  `BytesTransferred`, `BytesWritten`, `FilesTransferred`,
  `BytesCompressed`, `TransferDurationBytesPerSecond`,
  `VerificationFilesTransferred`, `VerificationFilesFailed` available
  at 1-minute period in `AWS/DataSync` namespace.

## Domain

AWS CloudOps / DataSync, on-prem-to-AWS migration, AWS-to-AWS
large-scale transfer, and FSx family destination support.

## AWS documentation

- **DataSync User Guide** — https://docs.aws.amazon.com/datasync/latest/userguide/what-is-datasync.html
- **Working with AWS DataSync agents** — https://docs.aws.amazon.com/datasync/latest/userguide/working-with-agents.html
- **Creating a DataSync task** — https://docs.aws.amazon.com/datasync/latest/userguide/create-task.html
- **Task options** — https://docs.aws.amazon.com/datasync/latest/userguide/api-reference.html#API_TaskOptions
- **Scheduling a task** — https://docs.aws.amazon.com/datasync/latest/userguide/configure-task-schedule.html
- **DataSync Task Reports** — https://docs.aws.amazon.com/datasync/latest/userguide/task-reports.html
- **DataSync Discovery** — https://docs.aws.amazon.com/datasync/latest/userguide/discovering-your-storage.html
- **FSx for NetApp ONTAP as a destination** — https://docs.aws.amazon.com/datasync/latest/userguide/destination-fsx-ontap.html
- **DataSync on Snowball Edge** — https://docs.aws.amazon.com/datasync/latest/userguide/snowball-edge.html
- **DataSync CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/datasync/
- **DataSync API Reference** — https://docs.aws.amazon.com/datasync/latest/userguide/API_Reference.html
