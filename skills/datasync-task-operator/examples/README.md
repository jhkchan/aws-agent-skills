# End-to-end usage scenario: datasync-task-operator

A walkthrough showing the skill planning a create-task operation for
NFS-to-S3 migration with POINT_IN_TIME_CONSISTENT verify and a daily
schedule, with all pre-checks passing and the operator confirming at
the CONFIRM gate. Contrasted with the BLOCKED case where the task
role is missing s3:PutObject on the destination bucket.

## Input (user prompt)

> We need to migrate an on-prem NFS share at
> `nfs://10.0.10.20/vol/data` (~12 TB, ~5M files) to
> `s3://prod-migration-archive-2026` (SSE-KMS) with daily delta
> syncs, a 1 Gbps bandwidth cap, and full integrity verification.

```json
{
  "Operation": "create-task",
  "Source": "nfs://10.0.10.20/vol/data",
  "Destination": "s3://prod-migration-archive-2026",
  "DestinationKmsKey": "arn:aws:kms:us-east-1:111111111111:key/dest-cmk",
  "Schedule": "rate(1 day)",
  "BandwidthLimitMb": 1000,
  "VerifyMode": "POINT_IN_TIME_CONSISTENT",
  "PosixPermissions": "PRESERVE",
  "AgentArn": "arn:aws:datasync:us-east-1:111111111111:agent/agent-001",
  "IamRole": "arn:aws:iam::111111111111:role/datasync-task-role"
}
```

## Skill output

```text
OPERATION: create-task
VERDICT: READY
TARGET: nfs://10.0.10.20/vol/data -> s3://prod-migration-archive-2026
        (task: new — "nfs-to-s3-archive")
PRE_CHECKS:
  - [PASS] Agent Status: ONLINE, LastConnectionTime recent
  - [PASS] Source location LocationType: NFS, reachable from agent
  - [PASS] Destination location LocationType: S3
  - [PASS] IAM role trusts datasync.amazonaws.com
  - [PASS] Task role has s3:GetObject, s3:PutObject,
    s3:AbortMultipartUpload, s3:ListBucket on destination
  - [PASS] Task role has kms:Encrypt, kms:GenerateDataKey on dest-cmk
  - [PASS] Destination key policy grants role
  - [PASS] Options.VerifyMode: POINT_IN_TIME_CONSISTENT,
    Options.PosixPermissions: PRESERVE (S3 stores POSIX in metadata)
  - [PASS] ScheduleExpression: rate(1 day) within 1-year horizon
  - [PASS] BandwidthLimitInMb: 1000 <= agent uplink (10 Gbps)
STEPS:
  1. CONFIRM: About to create DataSync task "nfs-to-s3-archive"
     in account 111111111111 region us-east-1. Source:
     nfs://10.0.10.20/vol/data. Destination:
     s3://prod-migration-archive-2026 (SSE-KMS). VerifyMode:
     POINT_IN_TIME_CONSISTENT. Schedule: daily. Bandwidth throttle:
     1000 Mb/s. First execution transfers ~12 TB. Proceed? (yes/no)
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

## Contrast — BLOCKED case (task role missing s3:PutObject)

If the latest execution failed with AccessDenied on s3:PutObject,
the pre-check gate fires and no remediation CLI executes until the
operator attaches the missing policy:

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

## What the skill caught that a generic assistant misses

1. **False-green-task trap.** A generic assistant looks at the
   task's `Status: AVAILABLE` and concludes the transfer is fine.
   The skill checks `describe-task-execution` for the latest
   execution and finds Status: ERROR with AccessDenied detail.

2. **Options vs IAM gap.** A generic assistant suggests
   `AmazonS3FullAccess` (over-broad). The skill scopes the fix to
   `s3:PutObject` + multipart permissions on the destination bucket
   ARN only.

3. **Baseline-aware re-run.** A generic assistant says "re-run the
   task" without considering the prior partial transfer. The skill
   surfaces TransferMode: CHANGED to resume from the baseline
   rather than re-copying 12 TB.

4. **KMS key policy vs IAM.** A generic assistant verifies the IAM
   role and stops. The skill checks the destination KMS key policy
   separately — IAM alone is not sufficient for cross-account or
   some same-account CMKs.

5. **POINT_IN_TIME_CONSISTENT cost awareness.** A generic assistant
   emits the create-task without surfacing the verify overhead. The
   skill notes the 5-15% wall-time addition for 12 TB.

6. **POSIX preservation on S3.** A generic assistant silently allows
   `PosixPermissions: PRESERVE` on any destination. The skill
   confirms S3 stores POSIX in object metadata (vs the SMB case
   which would BLOCK).

7. **Bandwidth-throttle feasibility check.** A generic assistant
   accepts any value. The skill checks the throttle against the
   agent's 10 Gbps uplink — values above it are silently capped by
   the agent.

## Slash-command invocation

```
/aws:operate-datasync-task
```

Or via the orchestrator:

```
/aws:pipeline
You: "migrate nfs://10.0.10.20/vol/data to s3://prod-migration-archive-2026"
```

The orchestrator emits
`[Phase: Operate | Skills routed: datasync-task-operator]` and hands
off to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "migrate nfs share to s3 with datasync"
# [Phase: Operate | Skills routed: datasync-task-operator]
```

## Live-account follow-up (optional, requires AWS CLI)

After the task is created and the first execution completes:

```bash
# Poll the latest execution until Status is SUCCESS or ERROR
EXEC_ARN=$(aws datasync list-task-executions \
  --task-arn arn:aws:datasync:us-east-1:111111111111:task/task-001 \
  --max-results 1 --query 'TaskExecutions[0].TaskExecutionArn' \
  --output text --profile default)
for i in $(seq 1 720); do
  STATUS=$(aws datasync describe-task-execution \
    --task-execution-arn "$EXEC_ARN" --query Status \
    --output text --profile default)
  if [ "$STATUS" = "SUCCESS" ] || [ "$STATUS" = "ERROR" ]; then
    echo "Terminal: $STATUS"
    break
  fi
  sleep 60
done

# Spot-check 3 files on the destination (size + ETag)
aws s3api head-object --bucket prod-migration-archive-2026 \
  --key "logs/app.log" --profile default

# CloudWatch alarm on VerificationFilesFailed > 0
aws cloudwatch put-metric-alarm \
  --alarm-name datasync-nfs-to-s3-verify-failed \
  --namespace AWS/DataSync \
  --metric-name VerificationFilesFailed \
  --dimensions Name=TaskId,Value=task-001 \
  --threshold 0 --comparison-operator GreaterThanThreshold \
  --period 300 --evaluation-periods 1 \
  --profile default

# Configure Task Reports for compliance evidence
aws datasync update-task \
  --task-arn arn:aws:datasync:us-east-1:111111111111:task/task-001 \
  --task-report-config '{
    "S3ObjectVersioning": "ENABLED",
    "OutputType": "STANDARD",
    "ReportLevel": "SUCCESSES_AND_ERRORS",
    "Destination": {
      "S3": {
        "BucketAccessRoleArn": "arn:aws:iam::111111111111:role/datasync-reports-role",
        "S3BucketArn": "arn:aws:s3:::datasync-reports-111111111111"
      }
    }
  }' --profile default
```
