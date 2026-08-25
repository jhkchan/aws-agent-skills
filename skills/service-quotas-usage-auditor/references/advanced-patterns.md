# Advanced Patterns — Service Quotas Usage Auditor

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

### Step 0: Expert knowledge — non-obvious Service Quotas behaviors

- **`list-service-quotas` returns the APPLIED value, not the default.**
  The `Value` field in the response is the currently-effective quota,
  which may include an approved increase. To see the AWS default, call
  `get-aws-default-service-quota`. Many operators compare utilization
  against the default and produce false negatives — the applied quota
  may already be higher, giving more headroom than expected. Always
  compute utilization as `currentUsage / appliedValue`.

- **Not all quotas emit CloudWatch metrics.** Only quotas with a
  `UsageMetric` block have a corresponding `AWS/Usage` metric. Quotas
  without it (some IAM quotas, some Route 53 quotas, many
  Organizations quotas) have NO programmatic utilization signal — you
  must enumerate live resources and compare manually. This is a
  CONFIG_GAP (Step 2a) because there is no way to alarm before
  exhaustion.

- **The `AWS/Usage` CloudWatch namespace requires exact dimensions.**
  The `UsageMetric` block specifies `MetricNamespace` (always
  `AWS/Usage`), `MetricName` (usually `ResourceCount`), `Dimensions`
  (Service, Resource, Type, and sometimes a Class or other dimension),
  and `StatisticType` (`Sum` or `Maximum`). An alarm created with the
  wrong dimension values silently monitors nothing — `DescribeAlarms`
  returns the alarm as OK while the actual metric has no data points.
  Always copy dimensions verbatim from the `UsageMetric` block.

- **`GlobalQuota` determines region scope.** A `GlobalQuota: true`
  quota (e.g., S3 buckets per account) applies account-wide; an increase
  is global. A `GlobalQuota: false` quota (e.g., VPCs per region) is
  per-region — an increase in us-east-1 does NOT apply to eu-west-1.
  Cross-referencing a regional quota across regions requires querying
  each region independently.

- **Applied quota != requested quota.** A PENDING increase request has
  NOT changed the applied quota. The applied value remains the old
  number until the request transitions to APPROVED. Computing
  utilization against the requested (future) value masks the current
  risk. Always use the current `Value` from `get-service-quota`, not the
  `DesiredValue` from a pending request.

- **Request status lifecycle:** `PENDING` -> `CASE_OPENED` ->
  (`APPROVED` | `DENIED` | `NOT_APPROVED` | `CASE_CLOSED`). APPROVED
  increases the applied quota (may take minutes to propagate). DENIED
  and NOT_APPROVED do not change the quota. A CASE_OPENED status means
  AWS support is reviewing — this can take days for large increases.

- **`Adjustable: false` quotas are architectural constraints.** You
  cannot request an increase — the limit is fixed by AWS. The only
  remediation is to restructure: distribute across accounts (if
  GlobalQuota) or regions (if regional), reduce usage, or switch to a
  different service. Do NOT suggest `request-service-quota-increase` —
  it returns `ValidationException`.

- **`AWS/Usage` metrics publish with a 5-15 minute ingestion delay.**
  A CloudWatch alarm set at exactly 80% of the applied quota may fire
  AFTER actual usage has already crossed 100% — by the time the alarm
  triggers and pages on-call, new resource creation is already failing
  with `LimitExceededException`. Set alarm thresholds at 70-75% of
  the applied quota to create a real remediation window, not at the
  same 80% line used for the audit verdict.

- **`list-service-quotas` does NOT return current utilization.** The
  API returns only quota metadata and the applied value — there is no
  `CurrentUsage` field. You must separately call `aws cloudwatch
  get-metric-statistics` on the `AWS/Usage` metric and divide by the
  applied value to compute utilization. Automation that assumes
  `list-service-quotas` includes a usage number silently produces 0%
  for every quota — every verdict comes back OK.

- **The Service Quotas API itself is rate-limited.** The
  `list-service-quotas` and `list-requested-service-quota-change-history`
  endpoints share a per-account throttle (approximately 10-20 TPS).
  Bulk-auditing every quota for every service in a single loop will
  hit `ThrottlingException`. Implement exponential backoff and batch
  by service-code with a 0.5s delay between services.

- **Large increase requests auto-route to support cases.** Even for
  `Adjustable: true` quotas, requests beyond a service-specific
  multiplier (often 2x-10x the current value) are NOT auto-approved.
  AWS converts them to a support case (status transitions to
  CASE_OPENED) that can take 2-5 business days. This means a quota at
  85% with a freshly-submitted 2x request will NOT be relieved before
  exhaustion — plan capacity increases when utilization crosses 50%,
  not 80%.

- **Pending increase requests have their own quota.** There is a limit
  on the number of concurrent PENDING requests per account. If you hit
  this, you must withdraw old requests (`--request-id`) before
  submitting new ones.

- **`QuotaCode` (e.g., `L-1212C26A`) is the stable identifier.**
  `QuotaName` can change between API versions or be renamed by the
  service team. Always track and reference quotas by `QuotaCode` in
  automation, dashboards, and remediation scripts.

- **Service Quotas is replacing Trusted Advisor service-limit checks.**
  Trusted Advisor's service-limit checks cover only a subset of quotas
  and are deprecated for accounts with Business/Enterprise support. The
  modern approach is Service Quotas + CloudWatch alarms on `AWS/Usage`.
  Do NOT rely on Trusted Advisor as the sole utilization signal.

- **Utilization can spike instantly.** A quota at 30% utilization can
  jump to 100% in seconds if an Auto Scaling group adds instances, a
  Lambda function fan-outs, or a misconfigured deploy creates resources.
  This is why a CloudWatch alarm is recommended even for quotas with
  moderate utilization — the alarm is for the spike, not the trend.


## Recent AWS features (2024-2026)

- **Organization-level quota management (2024-2025):** Service Quotas now supports viewing and requesting quota increases across all accounts in an Organization from the management account. Auditors should verify that the management account has visibility into member-account quota utilization and that organization-level quota requests are tracked.
- **Additional trackable quotas (2024):** More AWS services now expose `UsageMetric` data for Service Quotas tracking. Auditors should re-check quotas that were previously non-trackable — many have been updated with CloudWatch metrics.
- **Quota increase request automation:** Enhanced API support for programmatic quota increase requests. No new audit-surface fields, but auditors should verify that automated quota requests have approval workflows (not auto-approved without review).
