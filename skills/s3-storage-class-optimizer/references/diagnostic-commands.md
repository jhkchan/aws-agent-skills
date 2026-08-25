# Diagnostic Commands — s3-storage-class-optimizer

Moved verbatim from SKILL.md (progressive disclosure; load on demand). Sections keep their original headings.

## Required data sources (from the pre-flight data gate)

**Required data sources** (summarized — see reference for full CLI):
1. Bucket inventory: `aws s3api list-buckets --query 'Buckets[].Name'`
2. Lifecycle config: `aws s3api get-bucket-lifecycle-configuration`
3. Versioning status: `aws s3api get-bucket-versioning`
4. Intelligent-Tiering config: `aws s3api get-bucket-intelligent-tiering-configuration`
5. Storage Lens: `aws s3control get-storage-lens-configuration`
6. Cost Explorer S3 breakdown: `aws ce get-cost-and-usage --service S3`
7. Object-age sampling: `aws s3api list-objects-v2 --query 'Contents[?LastModified<...]'`

---

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation,
  emit and await operator approval. Do NOT execute until confirmed.
- **Test lifecycle on a prefix filter first.** Deploy the policy with
  a `Filter.Prefix` on a non-critical prefix; verify transitions; then
  widen to the whole bucket.
- **Verify MFA Delete status before lifecycle expiration.** If MFA
  Delete is enabled, lifecycle expiration of current versions will be
  blocked. Inform the operator.
- **Check Object Lock before recommending expiration.** Objects under
  Object Lock retention cannot be expired or overwritten until the lock
  expires.
- **Estimate transition request cost for small-object buckets.**
  Millions of tiny objects transitioning in one day can incur thousands
  of dollars in per-request fees.
- **Batch Operations jobs are irreversible.** A COPY job that overwrites
  objects in place with the wrong storage class is destructive. Always
  test on a manifest subset first.
- **Glacier/Deep Archive transitions are not instant.** S3 processes
  transitions asynchronously (typically within 12 hours). Do not expect
  immediate class change.
- **Noncurrent-version expiration is permanent.** Once expired, prior
  versions cannot be recovered. Verify the `NewerNoncurrentVersions`
  count before deploying.
- **Bulk-operation limit:** Process at most 5 buckets per batch. Sort
  by estimated savings, verify each batch before proceeding. Abort if
  any bucket shows unexpected retrieval cost spikes.
