# Worked Examples (load on demand) — AWS DataSync Task Operator

Secondary worked examples (diagnose-failing-execution BLOCKED with
fix, transfer-to-fsx-ontap COMPLETED) moved verbatim from SKILL.md.
Loaded on demand.

---

## Worked example — diagnose-failing-execution (BLOCKED with fix) (moved from SKILL.md)



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



## Worked example — transfer-to-fsx-ontap (COMPLETED) (moved from SKILL.md)



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


