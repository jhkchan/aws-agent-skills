# Worked Examples — s3-replication-operator

Moved verbatim from SKILL.md (progressive disclosure; load on demand). Sections keep their original headings.

### Worked example — diagnose-not-replicating (BLOCKED with fix)

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
      --key replication-test-$(date +%s).txt --body /tmp/test.txt
    aws s3api head-object --bucket prod-logs-dr-eu-west-1 \
      --key replication-test-$(date +%s).txt
  - Note: existing source objects PUT while destination versioning was
    off are NOT retroactively replicated. Run a Batch Operations job to
    backfill.
```

---

### Worked example — configure-cross-account (COMPLETED)

```text
OPERATION: configure-cross-account
VERDICT: COMPLETED
TARGET: prod-logs-source-us-east-1 (111111111111) ->
        audit-logs-dest-222222222222 (222222222222, us-west-2)
        (rule id: xaccount-audit)
PRE_CHECKS:
  - [PASS] Source + destination versioning Enabled
  - [PASS] Destination ObjectOwnership: BucketOwnerEnforced
  - [PASS] IAM role has s3:ReplicateObject +
    s3:ObjectOwnerOverrideToBucketOwner on destination ARN
  - [PASS] Destination bucket policy grants source account 111111111111
    role with s3:x-amz-source-account condition
  - [PASS] Destination KMS key policy grants source role kms:Encrypt
STEPS:
  1. CONFIRM: About to apply cross-account replication rule
     "xaccount-audit" from prod-logs-source-us-east-1 (111111111111)
     to audit-logs-dest-222222222222 (222222222222). This will create
     replicas owned by account 222222222222. Proceed? (yes/no)
  2. aws s3api put-bucket-replication --bucket prod-logs-source-us-east-1 \
       --replication-configuration file:///tmp/xaccount-repl-merged.json
  3. aws s3api head-object --bucket audit-logs-dest-222222222222 \
       --key xaccount-test-$(date +%s).txt
POST_VERIFY:
  - [PASS] Test object replicated within 45 seconds
  - [PASS] Version ID in destination matches source version ID
  - [PASS] Destination account 222222222222 can read the replica
    (verified via head-object as destination role)
  - [PASS] Replica owner is 222222222222 (BucketOwnerEnforced honored)
NOTES:
  - Replica ownership is enforced via ObjectOwnership +
    s3:ObjectOwnerOverrideToBucketOwner. Without either of these,
    replicas are owned by the source account and unreadable by the
    destination.
  - For ongoing verification, alarm on CloudTrail "Replication" events
    with "ErrorCode: AccessDenied" in the destination account.
```
