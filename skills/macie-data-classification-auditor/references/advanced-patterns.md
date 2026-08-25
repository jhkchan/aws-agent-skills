# Advanced patterns — macie-data-classification-auditor

Expert-knowledge deep dives and edge cases moved verbatim from SKILL.md for progressive disclosure. Load on demand.

## Step 1 edge case — job FAILED with ASDD disabled

**Edge case — job FAILED with ASDD disabled:** A job that existed but
FAILED is worse than no job at all because it creates a false sense of
coverage. Operators may believe "we have a Macie job running" when in
fact it has been failing silently. Emit the FAILED status in the
FINDINGS list so the operator knows to investigate the failure cause
(often IAM permission drift on the job role, or S3 bucket deletion).

## Recent AWS features (2024-2026)

- **Automated sensitive data discovery for additional data stores (2025):**
  Macie ASDD now supports sensitive data discovery beyond S3, including
  Amazon RDS snapshots and DynamoDB tables (where supported). Auditors
  should verify whether ASDD coverage extends to non-S3 data stores in
  the account — S3-only ASDD leaves database-resident PII undetected.
- **Expanded managed data identifiers (2024-2025):** Macie added new
  managed identifiers for additional PII types (international national
  IDs, financial instrument numbers). Auditors should verify that
  classification jobs are running the latest managed identifier set —
  jobs created before new identifiers were added may need recreation to
  pick up the expanded coverage.
- **Enhanced multi-account management via Organizations (2024):**
  Macie's delegated-administrator model integrates with AWS Organizations
  for centralized management. Auditors should verify that the Macie
  delegated admin account is set and that all member accounts are
  associated — a member account that is not associated has no Macie
  coverage regardless of the admin account's configuration.
- **Improved findings publication to Security Hub (2024-2025):** Macie
  now supports more granular publication controls for Security Hub,
  including separate toggles for classification findings vs policy
  findings. Auditors should verify both types are published if the
  organisation's SOC monitors both.
- **Sensitive data discovery for S3 Server Access Logs (2024):** Macie
  can now scan S3 server access logs for sensitive data inadvertently
  captured in log entries (e.g., query-string parameters containing
  tokens). Auditors should verify that access-log buckets are in scope
  for classification jobs.

## Reference — Expert knowledge — non-obvious Macie behaviors

These behaviors are easy to misjudge without operational Macie experience.
Each changes a verdict if ignored:

- **ASDD does probabilistic sampling, not full scans.** Automated
  sensitive data discovery samples objects in each bucket — it does NOT
  scan every object. A bucket "covered by ASDD" may have sensitive data
  that the sampling window missed. Only a classification job with
  `samplingPercentage: 100` guarantees every object is checked. Do NOT
  treat ASDD-enabled as equivalent to full job coverage for
  compliance-driven audits (PCI-DSS, HIPAA, GDPR).

- **`samplingPercentage` uses deterministic interval sampling, not
  random.** At `samplingPercentage: 25`, Macie selects every 4th object
  in S3 ListObjects order — the same objects on every run. Newly
  uploaded data that lands between sampled intervals is persistently
  missed across runs. An attacker who knows the sampling cadence can
  place sensitive data in the non-sampled positions. For
  compliance-driven audits, only `samplingPercentage: 100` eliminates
  this blind spot.

- **`jobStatus: USER_CANCELLED` produces partial results — a silent blind
  spot.** When an operator cancels a job mid-scan, findings exist for the
  objects already scanned, but the unscanned majority is never checked.
  A job in `USER_CANCELLED` is NOT active. A `FAILED` job (system
  cancelled, often throttling or IAM permission drift) similarly produces
  partial or no results. Only `RUNNING` and `COMPLETE` count as active.

- **`initialRun: false` on a new classification job creates a 24h+ blind
  spot.** The first scan does not run until the next scheduled interval.
  A daily job created at 09:00 with `initialRun: false` will not scan
  until 09:00 the next day. During that window, sensitive data uploaded
  to the target bucket is invisible to Macie.

- **Findings `severity` is about the data TYPE, not volume.** A single
  HIGH finding with `count: 1_000_000` represents one exposure point
  (one data type in one bucket), not "a million findings." Severity
  follows the managed-data-identifier category: `AWS_CREDENTIALS`,
  `CREDIT_CARD_NUMBER`, `US_SOCIAL_SECURITY_NUMBER` are HIGH; email
  addresses and names are typically MEDIUM. Do not escalate severity
  based on count alone.

- **The `count` field is per-object occurrences, not object or finding
  count.** A finding showing `count: 45000` for
  `US_SOCIAL_SECURITY_NUMBER` means 45,000 SSN matches were detected in
  a single S3 object (e.g., one large CSV). It does NOT mean 45,000
  findings or 45,000 objects. A bucket with 10,000 objects each
  containing 5 SSNs produces one finding with `count: 50000`, not
  10,000 findings. When triaging, investigate the object itself, not
  the count magnitude.

- **Classification jobs silently truncate on very large datasets.** Macie
  does not error when a job's data volume exceeds internal processing
  limits; the job reaches `COMPLETED` status but processes fewer objects
  than exist. Compare `statistics.numberOfBytesProcessed` against the
  total bucket size — a significant gap means objects were skipped. For
  data lakes exceeding ~1 TB per bucket, scope jobs to individual prefix
  levels rather than entire buckets.

- **Custom data identifiers silently no-op if the regex is too complex.**
  A CDI with a regex near or beyond the internal complexity threshold
  (nested quantifiers, deep backtracking) will be accepted by the API but
  produce zero findings on every object — with no error in job
  statistics. A CDI that works in testing on small files may silently
  fail on large production objects. Always validate CDIs against
  realistic object sizes and verify expected match counts in test runs.

- **`archived: true` is "marked as read," NOT "remediated."** Archiving a
  finding in Macie is a bookkeeping action — the sensitive data is still
  in the bucket. An archived HIGH finding still represents real PII or
  credentials at rest. Only treat archived findings as "triaged" when
  accompanied by evidence of investigation (annotation, ticket reference,
  or verified data removal). For the verdict logic, `archived: false`
  findings with severity HIGH are the UNTRIAGED_FINDINGS trigger.

- **Security Hub export is NOT retroactive.** Enabling the integration
  only pushes NEW findings to Security Hub. Pre-existing findings
  generated before the integration was enabled do NOT appear in Security
  Hub automatically. They must be exported manually via
  `aws macie2 export-findings`.

- **`bucket_allow_list` with wildcard prefixes silently masks future
  sensitive data.** An allow-list entry like `s3://data-lake/logs/*`
  tells Macie to never scan that prefix. If someone later stores PII in
  `s3://data-lake/logs/exports/`, it will never be detected. The
  allow-list should be scoped to specific object paths, not wildcards.

- **`findingsFilters` with `action: ARCHIVE` auto-suppress findings.** A
  findings filter can automatically archive findings matching criteria
  (e.g., all MEDIUM findings in a specific bucket). This is useful for
  known false positives but can also hide real findings from operators.
  An active ARCHIVE filter is a CONFIG_GAP — it reduces visibility.

- **Macie charges per GB scanned.** Classification jobs bill by data
  volume. A full scan of a 100 TB data lake costs significantly more than
  a 1% sample. The allow-list and job scoping (bucket criteria) control
  cost. A job with `samplingPercentage: 1` on a large bucket is
  cost-optimised but can miss sensitive data in the other 99%.

- **Managed data identifiers cannot be disabled per-job.** Every
  classification job runs all managed identifiers (150+ patterns). You
  cannot tell Macie "skip credit card detection on this job." To suppress
  specific managed-identifier findings, use a findings filter or
  allow-list, not job configuration.
