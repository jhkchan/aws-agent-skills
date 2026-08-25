# Advanced Patterns — Trusted Advisor Check Auditor

Expert edge cases, API internals deep dives, and recent-feature notes moved out of the SKILL.md body. Loaded on demand.

## Expert edge cases

These patterns represent genuine, non-obvious Trusted Advisor behaviours
that a senior CloudOps engineer would catch but a generalist would miss.

### The two API namespaces and their permission split

Trusted Advisor APIs live in **two namespaces** with **different IAM
permissions**:

1. **Legacy: AWS Support API** (`aws support describe-trusted-advisor-*`).
   Requires `support:DescribeTrustedAdvisorChecks` and related permissions.
   This is the original API surface, available since 2015. All CLI examples
   in this skill use the legacy namespace for compatibility.

2. **New: AWS Trusted Advisor service** (`aws trustedadvisor *`, introduced
   2023+). Requires `trustedadvisor:Describe*`, `trustedadvisor:List*`,
   `trustedadvisor:Update*` permissions. This namespace adds Organizations
   integration and a modernized response format.

An audit role with only `support:Describe*` permissions cannot use the new
namespace, and vice versa. When building an audit pipeline, grant BOTH
permission sets so the pipeline can use whichever API is available. Do NOT
assume `support:Describe*` is sufficient — the new namespace has features
the legacy API lacks (org-level aggregation, batch check refresh).

### `not_available` vs `ok` — the silent status

The `not_available` status means the check could not evaluate — typically
because a prerequisite is missing (e.g., the CloudTrail logging check
returns `not_available` if no trail exists in the region). This is
fundamentally different from `ok`:

- `ok`: The check ran and found no issues. The control is verified.
- `not_available`: The check could not run. The control is **unverified**.

A `not_available` security check is a blind spot — it may be hiding a
finding that the check cannot detect due to missing prerequisites. Always
classify `not_available` as CONFIG_GAP and note the prerequisite that is
missing.

### Check refresh is per-check and rate-limited

`aws support refresh-trusted-advisor-check --check-id <id>` refreshes a
single check. There is no bulk "refresh all" API. The API throttles at
approximately one refresh call per second per account. An audit pipeline
that refreshes 115 checks sequentially will take several minutes and may
hit `ThrottlingException` — implement exponential backoff.

Security checks typically complete refresh within 1-5 minutes. Cost and
Performance checks may take 15-30 minutes (they analyze CloudWatch metrics
and cost data). Do NOT assume a refreshed check returns an updated result
immediately — poll
`aws support describe-trusted-advisor-check-refresh-statuses` until the
status is `success`.

### Check exclusion persistence

Resource exclusions in Trusted Advisor are **permanent across refreshes**.
When an operator excludes a resource from a check (e.g., suppresses a
specific security group from the "open ports" check because it was flagged
as a known exception), the exclusion survives every subsequent refresh.
The check result shows `ok` or `warning` without any indication that a
resource was suppressed.

This means an excluded finding is more dangerous than a resolved finding:
a resolved finding re-appears if the condition recurs; an excluded finding
stays hidden permanently. When exclusions are present, always note: "N
resources excluded from this check. Excluded resources are invisible in
future refreshes. Review exclusions periodically to ensure they are still
justified."

### Cost optimization thresholds are hardcoded (not configurable)

Trusted Advisor cost-optimization checks use **fixed thresholds** set by
AWS — they are not user-configurable:

- **Idle EC2 Instances**: average CPU utilization < 10% for 14 consecutive
  days, plus network I/O < 5 MB/s for 14 days. Daily charge > $0.05.
- **Low Utilization EC2 Instances**: average CPU utilization < 20% for 7
  consecutive days, plus network I/O < 5 MB/s for 7 days.
- **Underutilized EBS Volumes**: < 1 IOPS for 7 consecutive days. Volume
  has been unattached for at least 7 days.
- **Unassociated Elastic IPs**: EIP not associated with a running EC2
  instance for more than 24 hours.

These thresholds are conservative — a instance at 12% CPU for 13 days will
NOT be flagged by "Idle EC2" (it does not meet the 14-day window). Do not
treat TA's absence of a cost finding as "no waste" — the instance may be
below the detection threshold but still underutilized. For finer-grained
cost analysis, use Compute Optimizer (which has adjustable lookback
windows) alongside TA.

### Organizations delegated admin is opt-in

By default, Trusted Advisor runs **per-account** even in an AWS
Organization. There is no automatic org-level aggregation. To see TA
results across all member accounts from a single payer, a delegated admin
must be explicitly configured:

```bash
aws trustedadvisor enable-organization --profile management-account
```

This sets up the management account (or a delegated member) as the TA
aggregation point. Without this, an auditor checking the payer account
sees only the payer's checks — member account findings are invisible. For
a multi-account audit, always verify the delegated admin configuration
before treating the payer's TA results as org-wide.

### `describe-trusted-advisor-check-summaries` vs `-result`

The legacy API has two granularity levels:

- **`describe-trusted-advisor-check-summaries`**: returns the check-level
  status only (ok / warning / error / not_available). Fast, lightweight,
  suitable for a first-pass sweep of all 115+ checks. Does NOT include
  flagged resource details.
- **`describe-trusted-advisor-check-result`**: returns the full flagged
  resource list with per-resource status and metadata. Heavier response,
  suitable for drill-down on non-ok checks.

An efficient audit pipeline runs summaries first (identify which checks are
non-ok), then result only on the non-ok checks. This minimizes API calls
and response size. Do NOT call `result` on every check — the responses for
checks with hundreds of flagged resources are large and slow.

**Batch processing pattern for multi-check audits:**

1. Call `describe-trusted-advisor-check-summaries` once per check (or
   `batch-describe-trusted-advisor-check-summaries` in the new namespace)
   to get the status of all checks in a single pass.
2. Filter to checks where status is not `ok` (typically 5-20 out of 115+).
3. For each non-ok check, call `describe-trusted-advisor-check-result` to
   get flagged resource details.
4. Classify each result using Steps 0-5, then aggregate worst-finding-wins.

This two-phase pattern reduces API calls from ~115 to ~20 and avoids
fetching large resource lists for clean checks.

### Security check overlap with Security Hub

Several Trusted Advisor security checks overlap with AWS Security Hub
controls. The most common overlaps:

- TA "IAM Use" ≈ Security Hub [IAM.7] (password policy), [IAM.8] (MFA on
  root).
- TA "Security Groups - Specific Ports Unrestricted" ≈ Security Hub
  [EC2.14]-[EC2.18].
- TA "S3 Bucket Permissions" ≈ Security Hub [S3.1]-[S3.3].

If both TA and Security Hub are enabled, they produce duplicate findings.
When remediating, fix the issue once (it clears both). When auditing,
note the overlap to avoid double-counting severity.

### Legacy API metadata is positional, not key-value

The legacy `describe-trusted-advisor-check-result` API returns each
flagged resource's `metadata` as an **ordered string array**, not a
key-value map. The field names are defined separately in the check's
`metadataTemplate` (returned by `describe-trusted-advisor-checks`). For
example, a Service Limits check result might show `"metadata": ["5",
"5", "Amazon VPC"]` where position 0 is current usage, position 1 is the
limit, and position 2 is the service name. An audit pipeline that
assumes key-value pairs will silently misparse the data. Always map
positions to names using the `metadataTemplate` before interpreting
values.

### TA delegated admin is separate from other delegated admins

Configuring a delegated admin for Trusted Advisor
(`aws trustedadvisor enable-organization`) does NOT configure delegated
admins for Security Hub, GuardDuty, or Amazon Macie — each service
requires its own delegation. An audit that verifies org-level TA
coverage must not assume that a Security Hub delegated admin covers TA.
Check each service independently with its own API.

### Refresh status `none` is ambiguous

The refresh status `none` has two valid meanings: (a) the check has
never been refreshed, or (b) the check was refreshed successfully and
the status was cleared. Do not treat `none` as an error. Fetch the
check result directly with
`describe-trusted-advisor-check-result` — the `timestamp` on the result
tells you when it was last evaluated, which is the authoritative
freshness signal.

## Deep reference: Trusted Advisor API internals

### Two API namespaces

| Namespace | IAM permission prefix | Introduced | Key advantage |
|---|---|---|---|
| `aws support describe-trusted-advisor-*` | `support:Describe*` | 2015 | Universally available, well-documented |
| `aws trustedadvisor *` | `trustedadvisor:*` | 2023+ | Organizations integration, batch operations, modernized response format |

An audit pipeline should attempt the new namespace first (richer features)
and fall back to the legacy namespace if the IAM permissions are not
available. Both namespaces return the same check data — the check IDs and
categories are identical across namespaces.

### Refresh lifecycle

When `refresh-trusted-advisor-check` is called, the check enters a refresh
queue. The lifecycle is:

1. `none` → check has never been refreshed or is not queued.
2. `enqueued` → refresh request accepted, waiting for evaluation.
3. `processing` → AWS is evaluating the check against current account
   state.
4. `success` → refresh complete, new results available.
5. `abandoned` → refresh failed (typically due to transient service issue).

Security checks typically complete in 1-5 minutes. Cost and Performance
checks may take 15-30 minutes (they analyze CloudWatch and cost data).
Service Limits checks are typically fast (< 1 minute). Always poll until
`success` before re-fetching results — fetching during `processing` returns
the stale result from the prior refresh.

### Organizations integration

The `aws trustedadvisor` namespace adds org-level APIs:

- `describe-organization` — check if org-level TA is enabled.
- `enable-organization` — set up the management account as the TA admin.
- `list-accounts-for-organization` — see which member accounts are
  reporting TA data to the aggregation point.
- `set-organization-access` — grant or revoke member account TA access to
  the admin.

Without organization-level TA, each member account must be audited
individually. The management account's TA results do NOT include member
account findings by default. For a multi-account audit, verify org-level
setup before relying on the management account's TA data.

### Check category reference

| Pillar | Example checks | Severity on `error` |
|---|---|---|
| **Security** | IAM Use (root MFA, access keys), S3 Bucket Permissions, Security Groups, CloudTrail Logging, IAM Access Key Age | CRITICAL_CHECK |
| **Fault Tolerance** | ELB AZ Awareness, RDS Multi-AZ, Auto Scaling Group Health, EBS Snapshot, Route 53 Health Checks | CRITICAL_CHECK |
| **Cost Optimization** | Idle EC2 Instances, Low Utilization EC2, Underutilized EBS Volumes, Unassociated EIPs, S3 Bucket Lifecycle | WARNING_CHECK |
| **Performance** | High Performance Assurance, EC2 Instance Optimization, EBS I/O Performance | WARNING_CHECK |
| **Service Limits** | EC2 Instance Limit, VPC Limit, EBS Volume Count, Auto Scaling Groups, IAM Roles | Step 3 (graduated) |

## Recent AWS features (2024-2026)

- **Trusted Advisor recommendations API GA (2024):** The Trusted Advisor recommendations API is now available to all customers (previously Business/Enterprise only). Auditors should verify that the API is integrated with monitoring/automation systems and that recommendation refresh is scheduled.
- **Organization-level checks (2024-2025):** Trusted Advisor now provides organization-wide check aggregation from the management account. Auditors should verify that the management account can access all member-account check results and that consolidated reports are generated.
- **New check categories (2024):** Additional checks for newer AWS services and best practices. Auditors should verify that check exclusion lists do not silently disable newly added checks.
- **Integration with Cost Optimization Hub (2024):** Trusted Advisor cost checks now feed into COH recommendations. Auditors should cross-reference TA cost checks with COH to ensure consistency.
