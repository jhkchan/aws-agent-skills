# Error Handling — s3-glacier-restore-operator

Moved verbatim from SKILL.md (progressive disclosure; load on demand). Sections keep their original headings.

## Remediation guidance


**Ordering principle:** verify source class first, then tier-vs-source
compatibility, then provision capacity for Expedited, then issue the
restore, then wait, then verify.

### For BLOCKED — GIR object passed for restore

1. Re-classify: GIR is directly readable.
2. Issue `aws s3api get-object` — no restore needed.
3. Update the procedure doc to call out GIR as a non-archive tier.

### For BLOCKED — Deep Archive with Expedited tier

1. Re-tier to Standard (12 hr) or Bulk (48 hr).
2. Reconcile RTO: Deep Archive cannot restore faster than 12 hr.
3. If faster restore is required, change the source storage class at
   the lifecycle-policy level.

### For stalled Batch Operations job

1. Check `describe-job` for `FailureReason`.
2. Check the report bucket CSV for `NoSuchKey` entries.
3. Re-run failed tasks with a filtered manifest.

### For unexpected re-archival after promotion

1. Check `get-bucket-lifecycle-configuration` for rules that match
   the promoted prefix or tags.
2. Update the rule filter to exclude promoted objects.
3. Re-copy the affected objects to Standard.
