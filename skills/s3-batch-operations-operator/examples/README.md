# End-to-end usage scenario: s3-batch-operations-operator

A walkthrough showing the skill planning a bulk KMS re-encrypt job
(copy with new SSE-KMS key) against an S3 inventory manifest, with all
pre-checks passing and the operator confirming at the CONFIRM gate.
Contrasted with the BLOCKED case where the destination KMS key policy
denies the role.

## Input (user prompt)

> We need to bulk re-encrypt 12.4M objects in `prod-data` from the old
> KMS key to `arn:aws:kms:us-east-1:111111111111:key/new-key` using
> S3 Batch Operations. The S3 inventory manifest is at
> `s3://prod-inventory/2026-08-01/manifest.json`. Use the role
> `S3BatchOpsRole`. Rate: 500 RPS.

```json
{
  "Operation": "create-job",
  "OperationType": "Copy (in-place re-encrypt with new SSE-KMS key)",
  "Manifest": "s3://prod-inventory/2026-08-01/manifest.json (S3InventoryReport V2)",
  "SourceBucket": "prod-data",
  "Destination": "same bucket, new SSE-KMS key: arn:aws:kms:us-east-1:111111111111:key/new-key",
  "ReportBucket": "prod-batch-reports (us-east-1)",
  "Role": "arn:aws:iam::111111111111:role/S3BatchOpsRole",
  "RequestsPerSecond": 500,
  "Priority": 50,
  "EstimatedObjectCount": 12400000,
  "CallerPermissions": {
    "s3control:CreateJob": true,
    "iam:PassRole": "arn:aws:iam::111111111111:role/S3BatchOpsRole"
  },
  "RolePolicies": [
    "s3:GetObject on prod-data/*",
    "s3:PutObject on prod-data/*",
    "s3:GetObject on prod-inventory/manifests/*",
    "s3:PutObject on prod-batch-reports/*",
    "kms:Decrypt on arn:aws:kms:us-east-1:111111111111:key/old-key",
    "kms:Encrypt on arn:aws:kms:us-east-1:111111111111:key/new-key"
  ],
  "NewKmsKeyPolicy": {"GrantsRoleEncrypt": true}
}
```

## Skill output

```text
OPERATION: create-job
VERDICT: READY
TARGET: s3://prod-inventory/2026-08-01/manifest.json
        (operation: copy with new SSE-KMS key, role:
         arn:aws:iam::111111111111:role/S3BatchOpsRole)
PRE_CHECKS:
  - [PASS] Manifest readable, format S3InventoryReport V2 (versioned)
  - [PASS] Report bucket prod-batch-reports in us-east-1 (matches job)
  - [PASS] Caller has s3control:CreateJob + iam:PassRole on role
  - [PASS] Role has batchoperations trust + s3:GetObject + s3:PutObject
  - [PASS] Role has kms:Decrypt on old-key, kms:Encrypt on new-key
  - [PASS] New KMS key policy grants role Encrypt
  - [PASS] RequestsPerSecond: 500 (in [1, 2500])
  - [PASS] Manifest object count: 12,400,000 — ETA ~6.9h at 500 RPS
    (within CompletionWindow: 24h)
STEPS:
  1. CONFIRM: About to create a Batch Operations copy+re-encrypt job
     on 12,400,000 objects in bucket prod-data (account 111111111111,
     region us-east-1), overwriting in place with new SSE-KMS key
     arn:aws:kms:us-east-1:111111111111:key/new-key, at 500 RPS.
     Estimated cost: ~$248. Proceed? (yes/no)
  2. aws s3control create-job \
       --account-id 111111111111 \
       --region us-east-1 \
       --priority 50 \
       --role-arn arn:aws:iam::111111111111:role/S3BatchOpsRole \
       --operation '<copy-with-new-encryption-json>' \
       --manifest '{"Spec":{"Format":"S3InventoryReport","Fields":["Bucket","Key","VersionId"]},"Location":{"ObjectArn":"arn:aws:s3:::prod-inventory/2026-08-01/manifest.json","ETag":"<etag>"}}' \
       --report '{"Bucket":"arn:aws:s3:::prod-batch-reports","Prefix":"kms-reencrypt-2026-08/","Format":"Report_CSV_20180820","ReportScope":"FailedTasksOnly"}' \
       --client-request-token "$(uuidgen)"
  3. Poll: aws s3control describe-job --account-id 111111111111
     --job-id <returned-id> every 5 minutes
POST_VERIFY:
  - (pending execution)
NOTES:
  - Bulk KMS re-encrypt is a server-side copy with new SSE-KMS
    metadata, overwriting in place. Source ~12.4M Decrypt + destination
    ~12.4M Encrypt requests. Verify KMS quota first.
  - Use FailedTasksOnly report scope to avoid a multi-GB report.
  - CloudWatch alarm on KMS Throttles during the job window.
```

## Contrast — BLOCKED case (Lambda invoke missing principal)

If the operator had specified an invoke operation where the Lambda's
resource-based policy lacks the `batchoperations.amazonaws.com`
principal, the pre-check gate would fire and no CLI would execute:

```text
OPERATION: create-job
VERDICT: BLOCKED
TARGET: s3://prod-manifests/objects.csv
        (operation: Invoke Lambda MyObjectProcessor)
PRE_CHECKS:
  - [PASS] Manifest readable, format CSV
  - [PASS] Report bucket prod-batch-reports in us-east-1
  - [PASS] Caller has s3control:CreateJob + iam:PassRole
  - [PASS] Role has s3:GetObject on prod-data, s3:PutObject on reports
  - [PASS] Lambda State: Active, Timeout: 60s, Reserved: 100
  - [FAIL] Lambda resource-based policy missing
    batchoperations.amazonaws.com principal — Batch Operations cannot
    invoke the Lambda. The job would complete with 100% failure
    (ResourceConflictException / AccessDenied on every invocation).
STEPS: (none — pre-checks failed)
POST_VERIFY: (none)
NOTES:
  - Root cause: Lambda resource-based policy only allows
    s3.amazonaws.com, not batchoperations.amazonaws.com.
  - Fix: add the permission, then create the job.
    aws lambda add-permission \
      --function-name MyObjectProcessor \
      --statement-id BatchOperationsAccess \
      --principal batchoperations.amazonaws.com \
      --action lambda:InvokeFunction \
      --source-arn arn:aws:s3:::prod-manifests \
      --source-account 111111111111
```

## What the skill caught that a generic assistant misses

1. **Pre-check gate before any CLI executes.** A generic assistant
   emits the `create-job` command directly. The skill runs
   deterministic pre-checks (manifest format, report bucket region,
   role trust + identity policy, KMS key policy, Lambda resource
   policy, rate-control validity) and BLOCKS before creating a job
   that would silently fail.

2. **Operation-specific IAM grants.** A generic assistant says "make
   sure the role has permissions." The skill names the exact grants
   per operation type (see the operation/IAM matrix reference) and
   verifies the destination KMS key policy grants the role.

3. **`iam:PassRole` on the caller.** A generic assistant omits that
   the CALLER (not the role) needs `iam:PassRole` on the role ARN.
   Without it, `create-job` fails with `AccessDenied` before any
   object processing.

4. **Completion-window ETA validation.** A generic assistant does not
   estimate the ETA from the manifest size and rate. The skill flags
   a 12.4M-object job at 500 RPS as ~6.9 hours — if the operator's
   `CompletionWindow` is shorter, it BLOCKS.

5. **FailedTasksOnly report scope.** A generic assistant uses the
   default `Task` scope, producing a multi-GB report for large jobs.
   The skill always recommends `FailedTasksOnly` for jobs over 1M
   objects.

6. **Glacier restore two-stage semantics.** A generic assistant treats
   `Status: Complete` as "objects are restored." The skill surfaces
   that Bulk-tier restores are asynchronous; `Complete` only means
   requests were submitted.

7. **Large-job rate-control and KMS quota.** A generic assistant
   creates a single job with no rate limit. The skill requires
   explicit `RequestsPerSecond` for jobs over 100M objects and
   verifies the KMS quota beforehand.

## Slash-command invocation

```
/aws:operate-s3-batch-operations
```

Or via the orchestrator:

```
/aws:pipeline
You: "bulk re-encrypt prod-data with the new KMS key"
```

The orchestrator emits
`[Phase: Operate | Skills routed: s3-batch-operations-operator]` and
hands off to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "bulk re-encrypt prod-data with the new KMS key"
# [Phase: Operate | Skills routed: s3-batch-operations-operator]
```

## Live-account follow-up (optional, requires AWS CLI)

After the job completes:

```bash
# Verify job status and progress
aws s3control describe-job \
  --account-id 111111111111 \
  --job-id <id> \
  --query '{Status:Status,Succeeded:ProgressSummary.NumberOfTasksSucceeded,Failed:ProgressSummary.NumberOfTasksFailed}' \
  --profile default

# Read the completion report (FailedTasksOnly)
aws s3 cp s3://prod-batch-reports/kms-reencrypt-2026-08/result/<id>/results.csv - \
  --profile default

# Sample 5 objects — verify the new KMS key
for key in object-1 object-2 object-3 object-4 object-5; do
  aws s3api head-object --bucket prod-data --key "$key" \
    --query '{Key:Metadata,SSEKMSKeyId:SSEKMSKeyId}' \
    --profile default
done
```
