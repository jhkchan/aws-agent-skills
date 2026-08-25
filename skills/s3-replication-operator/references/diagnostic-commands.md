# Diagnostic Commands — s3-replication-operator

Moved verbatim from SKILL.md (progressive disclosure; load on demand). Sections keep their original headings.

## Pagination notes (from the pre-flight gate)

**Pagination:** `get-bucket-replication` returns the entire
`ReplicationConfiguration` (max 1,000 rules). `list-bucket-inventory-configurations`
paginates at 100. `create-job` for Batch Operations returns a JobId; status
is polled via `describe-job`.

---

## Live-account pre-flight commands (10-command gate)

**Live-account pre-flight (skip if offline plan audit):**
1. `aws s3api get-bucket-versioning --bucket <source>` AND
   `--bucket <destination>` — both MUST return `Status: Enabled`.
   Absence of the `Status` field means versioning is OFF (S3 returns
   an empty body).
2. `aws s3api get-bucket-location --bucket <source>` and
   `--bucket <destination>` — confirm Region relationship (CRR vs
   SRR) matches the rule intent.
3. `aws s3api get-bucket-replication --bucket <source>` — capture the
   full `ReplicationConfiguration` (rules, role, filters).
4. `aws s3api get-bucket-encryption --bucket <source>` and
   `--bucket <destination>` — capture KMS key ARNs.
5. `aws s3api get-bucket-ownership-controls --bucket <destination>` —
   confirm `ObjectOwnership` is compatible with cross-account
   replication (BucketOwnerEnforced eliminates the ACL issue entirely).
6. `aws iam list-attached-role-policies --role-name <role>` and
   `aws iam list-role-policies --role-name <role>` — verify the
   replication role's permission chain.
7. `aws s3api get-bucket-policy --bucket <destination>` — for
   cross-account, verify the policy grants the source account's role.
8. `aws kms describe-key --key-id <source-key>` and
   `--key-id <destination-key>` — confirm `Enabled` and key policies
   grant the replication role.
9. `aws cloudwatch get-metric-statistics --namespace AWS/S3 --metric-name
   PendingReplication --dimensions Name=SourceBucket,Value=<source>
   Name=DestinationBucket,Value=<destination>` — capture the current
   backlog (only meaningful if RTC is enabled).
10. `aws s3control list-jobs --account-id <account>` — for Batch
    Operations, confirm no in-flight batch-replicate job already covers
    the same prefix.

---

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`put-bucket-replication`, `delete-bucket-replication`,
  `put-bucket-ownership-controls`, `put-bucket-policy`,
  `s3control create-job`, `put-bucket-versioning`),
  emit: `CONFIRM: About to <operation> on <source/destination> in
  account <account> region <region>. This will <consequence>.
  Proceed? (yes/no)`. Do NOT execute until the operator confirms.

- **Capture pre-state for rollback.** Before any rule change:
  `aws s3api get-bucket-replication --bucket <source> --output json >
  /tmp/<source>-repl-$(date +%s).json`. This is the only rollback path
  — `put-bucket-replication` is full-replacement and there is no
  `undo`.

- **Verify versioning on BOTH buckets before any operation.** Replication
  silently halts if versioning is off on either side. The rule remains
  `Enabled` (the false-green trap).

- **Verify KMS key policies, not just IAM.** Cross-account KMS requires
  the destination key policy to grant the source role. IAM alone is
  not sufficient.

- **Verify the destination bucket policy for cross-account.** Check
  for `s3:x-amz-source-account` condition. Without it, replication
  fails with AccessDenied that surfaces only in S3 Server Access Logs.

- **Prefer additive changes over destructive ones.** Adding a new rule
  to the merged config is reversible; deleting a rule halts all
  in-flight replication for that rule's objects.

- **Validate filter scope before applying.** An empty prefix AND no
  Tag filter replicates the entire bucket. Confirm intent — cost scales
  with bytes replicated.
