# End-to-end usage scenario: s3-replication-operator

A walkthrough showing the skill planning an add-rule operation for
cross-region replication with SSE-KMS and Replication Time Control,
with all pre-checks passing and the operator confirming at the CONFIRM
gate. Contrasted with the BLOCKED case where destination versioning
is OFF — the false-green-rule trap.

## Input (user prompt)

> We have a source bucket `prod-logs-source-us-east-1` in us-east-1 and
> a destination `prod-logs-dr-eu-west-1` in eu-west-1. Both are SSE-KMS
> with CMKs. Add a CRR rule for the `logs/` prefix with RTC enabled.

```json
{
  "Operation": "add-rule",
  "Source": "prod-logs-source-us-east-1",
  "SourceRegion": "us-east-1",
  "Destination": "prod-logs-dr-eu-west-1",
  "DestinationRegion": "eu-west-1",
  "Filter": {"Prefix": "logs/"},
  "RTC": true,
  "SourceVersioning": "Enabled",
  "DestinationVersioning": "Enabled",
  "DestinationObjectOwnership": "BucketOwnerEnforced",
  "SourceKmsKey": "arn:aws:kms:us-east-1:111111111111:key/source-cmk",
  "DestinationKmsKey": "arn:aws:kms:eu-west-1:111111111111:key/dest-cmk",
  "IamRole": "arn:aws:iam::111111111111:role/s3-repl-role",
  "ExistingRules": [
    {"ID": "existing-rule-app", "Status": "Enabled", "Priority": 1, "Filter": {"Prefix": "app/"}}
  ]
}
```

## Skill output

```text
OPERATION: add-rule
VERDICT: READY
TARGET: prod-logs-source-us-east-1 -> prod-logs-dr-eu-west-1
        (rule id: new — "dr-crr-rtc")
PRE_CHECKS:
  - [PASS] Source bucket exists in us-east-1
  - [PASS] Source versioning Status: Enabled
  - [PASS] Destination bucket exists in eu-west-1
  - [PASS] Destination versioning Status: Enabled
  - [PASS] Destination ObjectOwnership: BucketOwnerEnforced
  - [PASS] IAM role arn:aws:iam::111111111111:role/s3-repl-role has
    s3:GetReplicationConfiguration + s3:GetObjectVersion on source
  - [PASS] IAM role has s3:ReplicateObject + s3:ReplicateDelete on
    arn:aws:s3:::prod-logs-dr-eu-west-1/*
  - [PASS] IAM role has kms:Decrypt on source key
    arn:aws:kms:us-east-1:111111111111:key/source-cmk
  - [PASS] IAM role has kms:Encrypt on destination key
    arn:aws:kms:eu-west-1:111111111111:key/dest-cmk
  - [PASS] Destination key policy grants role kms:Encrypt
  - [PASS] ReplicationTime.Time.Minutes: 15, Metrics.EventThreshold.Minutes: 15
  - [PASS] Existing rules (1) preserved in merged config
STEPS:
  1. CONFIRM: About to add replication rule "dr-crr-rtc" on
     prod-logs-source-us-east-1 (us-east-1) replicating to
     prod-logs-dr-eu-west-1 (eu-west-1) with RTC (15 min SLA). This
     applies to NEW objects only; existing objects require a Batch
     Operations job. Proceed? (yes/no)
  2. aws s3api put-bucket-replication --bucket prod-logs-source-us-east-1 \
       --replication-configuration file:///tmp/prod-logs-source-us-east-1-repl-merged.json
  3. aws cloudwatch get-metric-statistics --namespace AWS/S3 \
       --metric-name PendingReplication \
       --dimensions Name=SourceBucket,Value=prod-logs-source-us-east-1 \
       --start-time $(date -u -v-5M +%Y-%m-%dT%H:%M:%SZ) \
       --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
       --period 60 --statistics Sum
POST_VERIFY:
  - (pending execution)
  - aws s3api put-object --bucket prod-logs-source-us-east-1 \
      --key logs/__replication_test_$(date +%s).txt --body /tmp/test.txt
  - aws s3api head-object --bucket prod-logs-dr-eu-west-1 \
      --key logs/__replication_test_$(date +%s).txt → 200 within 60s
  - Compare VersionId source vs destination — MUST match
NOTES:
  - This rule replicates only NEW objects matching prefix "logs/".
    Existing objects (e.g., 4.2 TB of historical logs) require a Batch
    Operations S3ReplicateObject job AFTER this rule is applied.
  - RTC SLA: 99.99% of objects replicate within 15 minutes. CloudWatch
    alarms on PendingReplication > 0 for > 15 minutes recommended.
  - put-bucket-replication is full-replacement — pre-state was captured
    to /tmp/prod-logs-source-us-east-1-repl-merged.json before applying.
```

## Contrast — BLOCKED case (destination versioning OFF)

If the destination bucket had versioning OFF, the pre-check gate
fires and no CLI executes:

```text
OPERATION: diagnose-not-replicating
VERDICT: BLOCKED
TARGET: prod-logs-source-us-east-1 -> prod-logs-dr-eu-west-1
        (rule id: dr-crr-rtc)
PRE_CHECKS:
  - [PASS] Source replication config has rule "dr-crr-rtc", Status: Enabled
  - [FAIL] Destination bucket versioning Status: not found (versioning OFF)
    — S3 silently halts replication when destination versioning is off.
    The source rule remains Enabled, which is the false-green-rule trap.
  - [PASS] IAM role permissions verified
  - [PASS] KMS decrypt + encrypt grants verified
STEPS: (none — pre-checks failed)
POST_VERIFY: (none)
NOTES:
  - Root cause: destination bucket prod-logs-dr-eu-west-1 has versioning
    SUSPENDED (or never enabled). S3 cannot store replicated objects as
    versions on a destination without versioning.
  - Fix: enable versioning on the destination, then verify a test object
    replicates within 60 seconds.
    aws s3api put-bucket-versioning \
      --bucket prod-logs-dr-eu-west-1 \
      --versioning-configuration Status=Enabled
    aws s3api put-object --bucket prod-logs-source-us-east-1 \
      --key logs/replication-test-$(date +%s).txt --body /tmp/test.txt
    aws s3api head-object --bucket prod-logs-dr-eu-west-1 \
      --key logs/replication-test-$(date +%s).txt
  - Note: existing source objects PUT while destination versioning was
    off are NOT retroactively replicated. Run a Batch Operations job to
    backfill.
```

## What the skill caught that a generic assistant misses

1. **Full-replacement API awareness.** A generic assistant emits a
   `put-bucket-replication` with only the new rule, silently wiping the
   existing `app/` rule. The skill preserves existing rules by reading
   and merging before put.

2. **False-green-rule trap.** A generic assistant looks at the source
   rule `Status: Enabled` and concludes replication is configured. The
   skill checks BOTH source and destination versioning — destination
   versioning OFF is the silent killer.

3. **KMS key policy vs IAM policy distinction.** A generic assistant
   verifies the IAM role has `kms:Encrypt` and stops. The skill checks
   the destination KMS key policy separately — IAM alone is not
   sufficient for cross-account or even some same-account CMKs.

4. **Existing objects are NOT replicated.** A generic assistant says
   "apply the rule and replication begins." The skill surfaces that
   only NEW PUTs replicate; existing objects require a Batch Operations
   job.

5. **RTC requires both ReplicationTime AND Metrics.** A generic
   assistant sets only `ReplicationTime`. The skill sets both
   `ReplicationTime` and `Metrics` — without Metrics, the CloudWatch
   alarms do not fire.

6. **Sentinel object + version-ID match.** A generic assistant says
   "verify replication works." The skill names the specific verification:
   PUT a sentinel, poll head-object on destination, compare VersionId —
   they MUST match.

7. **Cross-account triple-policy surface.** A generic assistant omits
   the destination bucket policy and KMS key policy. The skill surfaces
   all three policy surfaces (IAM, bucket policy, KMS key policy) for
   cross-account setups.

## Slash-command invocation

```
/aws:operate-s3-replication
```

Or via the orchestrator:

```
/aws:pipeline
You: "configure CRR from prod-logs-source-us-east-1 to prod-logs-dr-eu-west-1"
```

The orchestrator emits
`[Phase: Operate | Skills routed: s3-replication-operator]` and hands
off to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "configure CRR from prod-logs-source to prod-logs-dr"
# [Phase: Operate | Skills routed: s3-replication-operator]
```

## Live-account follow-up (optional, requires AWS CLI)

After the rule is applied:

```bash
# Verify a sentinel object replicates within 60 seconds (or 15 min with RTC)
TEST_KEY="logs/__replication_test_$(date +%s).txt"
echo "test" > /tmp/test.txt
aws s3api put-object --bucket prod-logs-source-us-east-1 \
  --key "$TEST_KEY" --body /tmp/test.txt --profile default

# Poll destination until 200 (max 60 attempts, 5s sleep)
SRC_VERSION=$(aws s3api head-object --bucket prod-logs-source-us-east-1 \
  --key "$TEST_KEY" --query VersionId --output text --profile default)
for i in $(seq 1 60); do
  DEST_VERSION=$(aws s3api head-object --bucket prod-logs-dr-eu-west-1 \
    --key "$TEST_KEY" --query VersionId --output text --profile default 2>/dev/null) || true
  if [ "$DEST_VERSION" = "$SRC_VERSION" ]; then
    echo "Replicated in ${i}x5s, version IDs match: $SRC_VERSION"
    break
  fi
  sleep 5
done

# CloudWatch alarm on PendingReplication backlog (RTC required)
aws cloudwatch put-metric-alarm \
  --alarm-name prod-logs-crr-backlog \
  --namespace AWS/S3 --metric-name PendingReplication \
  --dimensions Name=SourceBucket,Value=prod-logs-source-us-east-1 \
  Name=DestinationBucket,Value=prod-logs-dr-eu-west-1 \
  --threshold 100 --comparison-operator GreaterThanThreshold \
  --period 300 --evaluation-periods 3 \
  --profile default

# Backfill existing objects via Batch Operations (manifest from S3 Inventory)
aws s3control create-job \
  --account-id 111111111111 \
  --operation '{"S3ReplicateObject": {}}' \
  --manifest file:///tmp/batch-manifest.json \
  --report '{"Bucket": "arn:aws:s3:::prod-logs-batch-reports", "Format": "Report_CSV_20180820", "Enabled": true}' \
  --role-arn arn:aws:iam::111111111111:role/s3-batch-repl-role \
  --client-request-token "$(uuidgen)" \
  --profile default
```
