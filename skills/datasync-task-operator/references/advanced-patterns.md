# Advanced Patterns (load on demand) — AWS DataSync Task Operator

Mindset framing, cost/time baselines, Step 0 non-obvious DataSync
behaviors, the false-green-task expert heuristic, and Recent AWS
features moved verbatim from SKILL.md. Loaded on demand.

---

## Cost/time baselines (2026) (moved from SKILL.md)



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



## Mindset — three DataSync realities (moved from SKILL.md)



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



## Step 0: Expert knowledge — non-obvious DataSync behaviors (moved from SKILL.md)



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



## Expert heuristic: the false-green task (moved from SKILL.md)



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



## Recent AWS features (2024-2026) (moved from SKILL.md)



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


