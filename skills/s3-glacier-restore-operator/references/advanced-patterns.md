# Advanced Patterns — s3-glacier-restore-operator

Moved verbatim from SKILL.md (progressive disclosure; load on demand). Sections keep their original headings.

### Step 0: Expert heuristic — field craft for ambiguous cases


- **If the user does not know the source storage class → call
  `head-object` first.** Never request a restore without confirming
  StorageClass and ArchiveStatus. Restoring a GIR object is a no-op;
  restoring a Standard object returns an error; restoring an
  already-restored object resets the wait clock.

- **If the restore seems "stuck" → check `head-object` Restore
  field, not the Job ID.** Restore-object does NOT return a Job ID
  (unlike Batch Operations). The only status source is the Restore
  field on the object's metadata:
  `ongoing-request="true"` (in progress) or `ongoing-request="false"`
  with `expiry-date` (complete).

- **If Batch Operations job is `Active` for hours → check the
  manifest, not the job.** The job reports Active while the manifest
  is being processed. Failures are in the job report (CompletionReport
  bucket), not the job status. A common foot-gun: the manifest
  contains keys that no longer exist; the job marks them Failed but
  stays Active until full manifest iteration.

- **If Expedited requests are being rejected → provision capacity.**
  On-demand Expedited is best-effort and can be rejected during
  demand peaks. Provisioned capacity guarantees 3 retrieval
  requests/min or 150 MB/min per unit. Pre-provision for DR drills.

- **If the user wants a "permanent restore" → recommend copy-to-tier,
  not Days=N.** Days=N is a lease; the object reverts to archive
  when the window expires. For permanent promotion out of archive,
  copy the restored object to a hot storage class (Standard or
  Intelligent-Tiering) or update the lifecycle policy.

---

## Edge-case handling


- **Restore seems stuck.** Check `head-object Restore.ongoing-request`.
  If `true`, the restore is still in progress (Deep Archive Bulk can
  take 48 hours). If `false` but access fails, the restore failed
  silently — open an AWS support case.
- **Restore expires before user accesses the object.** Re-issue
  `restore-object` with a longer `Days` value, or copy to Standard
  before expiration. Update the procedure to use a longer lease.
- **Batch Operations job `Active` for hours with no progress.**
  Check the manifest ETag, the IAM role permissions, and rate
  limiting on the source bucket. The report CSV shows per-task
  failures.
- **Restoring a versioned object.** Specify `--version-id` on
  `restore-object` and `head-object`. Without it, the operation
  targets the current version, which may not be the archived one.
- **Restoring a Delete Marker.** Delete markers cannot be restored.
  Remove the delete marker first, then restore the underlying object.
- **Promotion via lifecycle.** If a lifecycle rule is the source of
  archiving, update or filter the rule to prevent re-archival of
  promoted objects. Otherwise the promotion is temporary.
- **GIR treated as Flexible Retrieval.** GIR is directly readable;
  restore-object is unnecessary. Re-classify and proceed with
  GetObject.
- **Cross-region restore.** Restores happen in the source bucket's
  region. For cross-region DR, copy the restored object to the
  destination region after restore completes.

---

## Recent AWS features (2024-2026)


- **S3 Glacier Instant Retrieval (GIR) — broadly adopted 2023-2024:**
  the lowest-cost storage class with single-digit-ms latency for
  infrequent access. Directly readable via GetObject — no restore
  required. Replaces Standard-IA for cold-but-queryable data.
- **Deep Archive Bulk restore cost-tier (2024):** the Bulk tier for
  Deep Archive is the lowest-cost retrieval option (48 hr SLA,
  ~$0.0025 per GB). Use for compliance exports with no RTO pressure.
- **S3 Batch Operations enhanced reporting (2024-2025):** the
  completion report now includes per-task CloudWatch metrics
  (BytesRestored, Duration) for tighter observability of bulk
  restores.
- **S3 Storage Lens restore dashboards (2024-2025):** Storage Lens
  now surfaces restore-operation counts and elapsed-time percentiles
  per bucket — useful for tuning lifecycle policies and predicting
  restore cost.

- **Lifecycle rule validation (2024-2025):** `put-bucket-lifecycle-configuration`
  now performs stricter validation, including non-overlapping rule
  detection — catches re-archival conflicts that previously caused
  silent object churn.
- **S3 Batch Operations tag-based manifests (2025):** Batch Operations
  supports S3 Resource Tags as a manifest source in addition to CSV
  — useful for tag-driven restore workflows.
- **Intelligent-Tiering Archive configurations (2025):**
  Intelligent-Tiering exposes configurable archive-access tiers
  (Flexible vs Deep Archive) per object — restores follow the same
  tier SLAs as native Glacier classes.
