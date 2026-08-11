# DataSync Task Options & Failure-Mode Reference

Load this reference when planning or executing a DataSync task change.
Covers the full Options surface, per-source-type setup details, the
failure-mode decision tree, and the per-operation pre-checklists.

## Full Options reference (create-task / update-task / start-task-execution --overrides)

| Option | Allowed values | Default | Notes |
|---|---|---|---|
| `VerifyMode` | `POINT_IN_TIME_CONSISTENT` | `POINT_IN_TIME_CONSISTENT` | Re-scans source + destination after transfer, compares checksums + metadata of every file in scope. Slowest but safest. |
|  | `ONLY_FILES_TRANSFERRED` |  | Verify only the files moved this run. Faster for delta syncs. |
|  | `NONE` |  | Skip verify. Fast but unsafe; NEVER use for compliance migrations. |
| `OverwriteMode` | `ALWAYS` | `ALWAYS` | Always overwrite destination. |
|  | `NEVER` |  | Do NOT overwrite; errors or warns on collision. Combine with `TransferMode: CHANGED` to skip-when-exists. |
| `Atime` | `NONE` | `BEST_EFFORT` | `BEST_EFFORT` preserves atime where destination supports it. |
|  | `BEST_EFFORT` |  |  |
| `Mtime` | `PRESERVE` | `PRESERVE` | Preserve modification time. |
|  | `NONE` |  |  |
| `Uid` | `PRESERVE` | `NONE` | POSIX UID. Use `PRESERVE` only on POSIX destinations. |
|  | `NONE` |  |  |
| `Gid` | `PRESERVE` | `NONE` | POSIX GID. Use `PRESERVE` only on POSIX destinations. |
|  | `NONE` |  |  |
| `PosixPermissions` | `PRESERVE` | `PRESERVE` | Full POSIX metadata. Only on POSIX destinations (EFS, FSx OpenZFS, FSx Lustre, S3 with metadata). |
|  | `PRESERVE_TRY` |  | Try preserve, fall back silently. |
|  | `BEST_EFFORT` |  |  |
|  | `NONE` |  | Drop POSIX. Required for SMB destinations. |
| `Acl` | `PRESERVE` | `NONE` | Preserve NFSv3/SMB ACLs where destination supports. |
|  | `NONE` |  |  |
| `SecurityDescriptorCopyFlags` | `OWNER_DACL_SACL` | `NONE` | SMB-specific. Copy owner + DACL + SACL. |
|  | `OWNER_DACL` |  | Copy owner + DACL (no SACL). |
|  | `NONE` |  |  |
| `TaskQueueing` | `ENABLED` | `ENABLED` | Queue executions when agent busy. |
|  | `DISABLED` |  | Fail fast if agent busy. |
| `LogLevel` | `OFF` | `BASIC` | CloudWatch Logs verbosity. `TRANSFER` is per-file diagnostic; very verbose. |
|  | `BASIC` |  |  |
|  | `TRANSFER` |  |  |
| `TransferMode` | `CHANGED` | `CHANGED` | Delta sync (default). Copies everything on first run (no baseline); subsequent runs only new/modified. |
|  | `ALL` |  | Force full re-copy. |
| `DeleteOnDelete` (2024) | `TRUE` | `FALSE` | When TRUE, source-side deletes mirror to destination. Default FALSE (destination is a backup). |

## Per-source-type setup

### NFS source

```bash
aws datasync create-location-nfs \
  --server-hostname 10.0.10.20 \
  --subdirectory /vol/data \
  --on-config --agent-arns arn:aws:datasync:us-east-1:111111111111:agent/agent-001 \
  --tags Key=env,Value=prod
```

Network reachability: agent subnet/SG must allow TCP 2049 inbound
from the source server's perspective, and the source server must
allow the agent's outbound.

### SMB source

```bash
aws datasync create-location-smb \
  --server-hostname 10.0.20.30 \
  --subdirectory /share/finance \
  --user finance-svc \
  --password-secret-arn arn:aws:secretsmanager:us-east-1:111111111111:secret:smb-cred-finance-AbCdEf \
  --domain CORP \
  --agent-arns arn:aws:datasync:us-east-1:111111111111:agent/agent-001 \
  --mount-options Version=SMB3
```

The task role needs `secretsmanager:GetSecretValue` on
`smb-cred-finance`. Hard-coded passwords NOT supported. SMB3
recommended for encryption in transit.

### HDFS source

```bash
aws datasync create-location-hdfs \
  --name-nodes NameNode=namenode-1.corp.local,Hostname=namenode-1.corp.local,Port=8020 \
  --authentication-type SIMPLE \
  --block-size 134217728 \
  --replication-factor 3 \
  --kms-key-provider-uri "kms://namenode-kms.corp.local:9600/kms" \
  --agent-arns arn:aws:datasync:us-east-1:111111111111:agent/agent-001 \
  --subdirectory /data/warehouse
```

For KERBEROS: add `--authentication-type KERBEROS`,
`--kerberos-principal`, `--kerberos-krb5conf-readable`,
`--kerberos-keytab-readable`.

### Object Storage source (non-AWS S3-compatible)

```bash
aws datasync create-location-object-storage \
  --server-hostname s3.example.com \
  --server-protocol HTTPS \
  --server-port 443 \
  --bucket-name migration-source \
  --access-key AKIAEXAMPLE \
  --secret-key $(aws secretsmanager get-secret-value --secret-id obj-storage-secret --query SecretString --output text) \
  --agent-arns arn:aws:datasync:us-east-1:111111111111:agent/agent-001 \
  --subdirectory /exports/2026
```

Verify ETag format compatibility with a small test transfer before
bulk migration; some non-AWS S3 implementations return ETags in
formats DataSync cannot checksum against.

### S3 source / destination

S3 source requires the task role to have `s3:GetObject`,
`s3:ListBucket`. S3 destination requires `s3:PutObject`,
`s3:AbortMultipartUpload`, `s3:ListBucketMultipartUploads`,
`s3:GetObject` (for verify), `s3:GetObjectTagging`,
`s3:PutObjectTagging`. SSE-KMS destinations add `kms:Encrypt`,
`kms:GenerateDataKey`. Cross-account S3 destinations require the
destination bucket policy to allow the source account's task role.

### EFS destination

The file system policy must allow `elasticfilesystem:ClientMount`,
`ClientWrite`, `ClientRootAccess` for the DataSync service principal.
The agent subnet MUST have an EFS mount target. Cross-AZ access
works but incurs charges.

### FSx for Windows destination

```bash
aws datasync create-location-fsx-windows \
  --fsx-filesystem-arn arn:aws:fsx:us-east-1:111111111111:file-system/fs-abc123 \
  --security-group-arns arn:aws:ec2:us-east-1:111111111111:security-group/sg-001 \
  --subdirectory /d$\share \
  --user svc-datasync \
  --password-secret-arn arn:aws:secretsmanager:us-east-1:111111111111:secret:fsx-cred \
  --domain corp.example.com
```

FSx for Windows does NOT preserve POSIX. Use
`PosixPermissions: NONE` or `BEST_EFFORT`.

### FSx for Lustre destination

Use `create-location-fsx-lustre`. POSIX preserved natively. Agent
subnet must be in the same AZ for Single-AZ; Multi-AZ allows
cross-AZ but charges apply.

### FSx for OpenZFS destination

Use `create-location-fsx-openzfs`. POSIX preserved natively.

### FSx for NetApp ONTAP destination

```bash
aws datasync create-location-fsx-ontap \
  --storage-virtual-machine-arn arn:aws:fsx:us-east-1:111111111111:storage-virtual-machine/svm-0456 \
  --security-group-arns arn:aws:ec2:us-east-1:111111111111:security-group/sg-001 \
  --subdirectory /vol1/finance \
  --protocol NFS={MountOptions=Version=NFSv3} \
  --tags Key=env,Value=prod
```

The SVM inter-cluster endpoint or VPC route must be reachable from
the agent subnet. Supports SMB and NFS protocols on the destination.

## Pre-operation checklists (per operation type)

### create-task

1. Agent ARN exists, `Status: ONLINE`, `LastConnectionTime` < 5 min.
2. Source location `LocationArn` exists, `LocationType` matches.
3. Destination location `LocationArn` exists, `LocationType` matches.
4. IAM task role trusts `datasync.amazonaws.com`.
5. Task role has source read + destination write chain.
6. (SSE-KMS) Task role + destination key policy grant the chain.
7. (Cross-account S3) Destination bucket policy allows source role.
8. Options internally consistent.
9. (Reports) Report bucket exists, task role has `s3:PutObject`.

### deploy-agent

1. Activation key fetched from agent local console (`http://<agent-ip>`).
2. Activation key < 24 h old.
3. Agent VM/EC2 has outbound HTTPS (443) to DataSync endpoints.
4. Agent subnet/SG can reach source location or destination VPC.
5. (Cross-Region) VPC peering/TGW/PrivateLink in place.
6. IAM role for the agent (EC2 instance profile) has `datasync:*` and
   source-reading permissions.

### update-task-options

1. Task `Status: AVAILABLE` (not RUNNING).
2. New `Options` block internally consistent.
3. Pre-state captured.

### create-schedule

1. Task ARN exists.
2. `ScheduleExpression` valid EventBridge syntax, within 1-year horizon.
3. (Bandwidth throttle) `BandwidthLimitInMb` <= agent uplink.

### diagnose-failing-execution

1. Capture `describe-task-execution` for the latest execution.
2. Read `ErrorCode`/`ErrorDetail`.
3. Consult the failure-mode table in SKILL.md.

### run-discovery

1. On-prem storage reachable from the discovery agent.
2. No in-flight discovery job covers the same storage system.
3. Collection window (14 or 28 days) set explicitly.

### transfer-to-fsx-ontap

1. FSx for NetApp ONTAP file system `AVAILABLE`.
2. SVM exists and inter-cluster endpoint reachable from agent.
3. Agent subnet has route to SVM endpoint.
4. Task role has `fsx:CreateMountTarget`,
   `fsx:DescribeFileSystems`, plus ONTAP-specific permissions.

### configure-task-reports

1. Reports S3 bucket exists in same Region.
2. Task role has `s3:PutObject` on the reports bucket.
3. `ReportLevel` is one of `ERRORS_ONLY`, `SUCCESSES_AND_ERRORS`.

## Failure-mode decision tree

```
describe-task-execution returns Status
├── SUCCESS
│   └── Check FilesTransferred == EstimatedFilesToTransfer
│       ├── Equal → Check VerificationFilesFailed (if VerifyMode != NONE)
│       │   ├── 0 → COMPLETED
│       │   └── >0 → Re-run with TransferMode: CHANGED
│       └── Less → Inspect Task Report; widen task role permissions
├── ERROR
│   └── Read ErrorDetail
│       ├── "Agent is offline" → describe-agent; restart VM; verify HTTPS 443
│       ├── "AccessDenied for s3:PutObject on <dest>" → attach s3:PutObject
│       ├── "Mount target not found" → wrong-AZ agent; add mount target
│       ├── "SMB login failed" → rotate secret; re-create SMB location
│       ├── "KMS key policy does not grant role" → update destination key policy
│       └── (other) → consult AWS Support
├── LAUNCHING > 30 min
│   └── Agent capacity exhausted; reduce concurrent tasks
└── TRANSFERRING forever, BytesTransferred flat
    └── Bandwidth throttle, agent CPU, source disk I/O bottleneck
```

## CloudWatch metrics namespace AWS/DataSync

Available at 1-minute period:

- `BytesTransferred` — total bytes read from source.
- `BytesWritten` — total bytes written to destination (after
  compression).
- `BytesCompressed` — total bytes after compression (for
  compressed-file detection).
- `FilesTransferred` — running count.
- `EstimatedFilesToTransfer` — count estimated at scan start.
- `TransferDurationBytesPerSecond` — throughput.
- `VerificationFilesTransferred` — files verified.
- `VerificationFilesFailed` — files failing verify (checksum
  mismatch).

## Discovery job

A discovery job is a read-only assessment that connects to an on-prem
NFS or SMB storage system and collects:

- Capacity usage (per share / per directory).
- Performance metrics (IOPS, throughput, latency).
- File-type distribution (extension histogram).
- Cold-data distribution (files not accessed in N days).

Run for 14 or 28 days. The recommendation report is available within
4 hours of job completion. Recommendations cover:

- Right-sized AWS destination (S3 tier, EFS size, FSx family).
- Migration wave planning (chunk by directory).
- Cold-data archival candidates (S3 Glacier Deep Archive).

A discovery job does NOT migrate data. A separate DataSync task is
required for migration.

## Task Reports output format

Reports are written as JSON Lines to:
`s3://<reports-bucket>/<task-id>/<execution-id>/reports/<report-level>/`.

Each line is one per-file result. Example:

```json
{"filePath": "/exports/2026/q3.xlsx", "sourceType": "SMB", "transferStatus": "OK", "errorCode": "", "errorDetail": "", "bytesTransferred": 4404019, "transferDuration": 1234}
{"filePath": "/exports/2026/q4.xlsx", "sourceType": "SMB", "transferStatus": "ERROR", "errorCode": "ACCESS_DENIED", "errorDetail": "s3:PutObject denied", "bytesTransferred": 0, "transferDuration": 0}
```

ReportLevel filters: `ERRORS_ONLY` emits only ERROR rows;
`SUCCESSES_AND_ERRORS` emits both. Optional `ReportCode` filters
(e.g., `TRANSFER_ERROR`, `VERIFY_CATEGORY`, `DELETE_SKIP`).

## AWS documentation pointers

- DataSync Options API — https://docs.aws.amazon.com/datasync/latest/userguide/API_Options.html
- Creating an SMB location — https://docs.aws.amazon.com/datasync/latest/userguide/create-smb-location.html
- Creating an NFS location — https://docs.aws.amazon.com/datasync/latest/userguide/create-nfs-location.html
- Creating an HDFS location — https://docs.aws.amazon.com/datasync/latest/userguide/create-hdfs-location.html
- Creating an Object Storage location — https://docs.aws.amazon.com/datasync/latest/userguide/create-object-storage-location.html
- Creating an EFS location — https://docs.aws.amazon.com/datasync/latest/userguide/create-efs-location.html
- Creating an FSx for NetApp ONTAP location — https://docs.aws.amazon.com/datasync/latest/userguide/create-fsx-ontap-location.html
