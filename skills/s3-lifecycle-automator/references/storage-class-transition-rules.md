# Storage Class Transition Rules Reference

Supplementary reference for the S3 Lifecycle Automator skill. Use when
selecting transition days, validating min-days constraints, or debugging
a lifecycle policy that deploys but never transitions objects.

## Enforced minimum-days constraints

These are HARD constraints enforced by the S3 lifecycle engine. Rules
that violate them are silently accepted by the API but NEVER execute.

| From | To | Min days (total object age) | Notes |
|---|---|---|---|
| STANDARD | STANDARD_IA | 30 | Hard minimum; most common violation |
| STANDARD | ONEZONE_IA | 30 | Same as STANDARD_IA |
| STANDARD_IA | GLACIER_IR | 90 | Must be >= 90 total object age |
| STANDARD_IA | GLACIER | 91 | 30 (IA) + 61 days after IA |
| STANDARD | GLACIER (direct, skipping IA) | 1 | Allowed — can skip IA entirely |
| STANDARD | GLACIER_IR (direct) | 90 | Direct to IR requires 90 days |
| GLACIER | DEEP_ARCHIVE | 180 | Total object age must be >= 180 |
| STANDARD | DEEP_ARCHIVE | 180 | Direct transition requires 180 days |
| STANDARD | INTELLIGENT_TIERING | 0 | No minimum — immediate opt-in |

## Why min-days violations are silent

The `put-bucket-lifecycle-configuration` API performs basic schema
validation (field names, types, required fields) but does NOT validate
transition days against the enforced minimums. The rule passes schema
validation, appears in `get-bucket-lifecycle-configuration` output, and
is stored by S3 — but the lifecycle engine skips it during daily
evaluation.

**There is no error, no warning, no CloudWatch metric, and no log
entry.** The only way to detect the failure is to monitor Storage Lens
`StorageClass` distribution and notice that objects are NOT moving to
the target storage class over time.

## Transition design patterns

### Pattern 1: Log archival (predictable, millisecond access)

```
Standard → IA (30d) → Glacier IR (90d) → Deep Archive (365d)
```

Best for application logs, access logs, and audit trails. Objects are
initially accessed for debugging, then rarely accessed. Glacier IR
maintains millisecond retrieval for compliance queries.

### Pattern 2: Backup retention (predictable, archival)

```
Standard → IA (30d) → Glacier Flexible (91d) → Deep Archive (180d)
```

Best for database snapshots and backups. Retrieval latency is acceptable
at minutes-to-hours since restores are planned.

### Pattern 3: Temporary uploads (short-lived)

```
Standard → Expire (30d)
```

Best for user upload staging, temporary processing artifacts. No
transition needed — objects are deleted before they would benefit from
tiering.

### Pattern 4: Unknown access pattern (Intelligent-Tiering)

```
Standard → Intelligent-Tiering (0d, immediate)
```

No transition days to manage. Intelligent-Tiering auto-moves objects
between tiers based on access frequency. Monitoring fee applies
($0.0025 per 1,000 objects).

### Pattern 5: Compliance archive (long-term retention)

```
Standard → Deep Archive (180d)
```

Best for regulatory/compliance archives with 7+ year retention.
Retrieval is rare and 12-hour SLA is acceptable.

## Storage class comparison matrix

| Storage class | Retrieval latency | Retrieval fee | Min duration | Monitoring fee | Best for |
|---|---|---|---|---|---|
| STANDARD | Milliseconds | None | None | None | Frequently accessed |
| STANDARD_IA | Milliseconds | Per-GB + per-request | 30 days | None | Infrequent, long-lived |
| ONEZONE_IA | Milliseconds | Per-GB + per-request | 30 days | None | Infrequent, reproducible |
| GLACIER_IR | Milliseconds | Per-GB + per-request | 90 days | None | Archives with fast access |
| GLACIER (Flexible) | 1-5 min (Expedited) to hours | Per-GB + per-request tiered | 90 days | None | Long-term archives |
| DEEP_ARCHIVE | 12 hours | Per-GB + per-request tiered | 180 days | None | Compliance archives |
| INTELLIGENT_TIERING | Milliseconds (FA/IA) | None for FA/IA tiers | None | $0.0025/1K objects | Unpredictable access |

## Glacier Flexible Retrieval tiers

| Retrieval option | Latency | Cost |
|---|---|---|
| Expedited | 1-5 minutes | Most expensive |
| Standard | 3-5 hours | Standard rate |
| Bulk | 5-12 hours | Cheapest |

## NoncurrentVersion lifecycle

When versioning is enabled, each object modification creates a new
version. The prior version becomes "non-current." Non-current versions
remain in their original storage class until explicitly managed by
NoncurrentVersion rules.

| Rule type | Field | Behavior |
|---|---|---|
| `NoncurrentVersionTransition` | `NoncurrentDays`, `StorageClass` | Transition non-current versions after N days of being non-current |
| `NoncurrentVersionExpiration` | `NoncurrentDays` | Permanently delete non-current versions after N days |
| `AbortIncompleteMultipartUpload` | `DaysAfterInitiation` | Abort multipart uploads incomplete within N days |
| `ExpiredObjectDeleteMarker` | `true` | Remove the delete marker when it's the only version left |

**Key insight:** `NoncurrentDays` counts from when the version became
non-current (i.e., when a newer version was created), NOT from the
object's original creation date.

## Common lifecycle debugging

| Symptom | Likely cause | Fix |
|---|---|---|
| Policy deployed but objects never transition | Min-days violation (rule silently ignored) | Validate days against minimums |
| Old lifecycle rules disappeared | `put` replaced entire policy without GET-merge first | Always GET, merge, PUT |
| S3 costs growing despite lifecycle | Non-current versions accumulating in Standard | Add NoncurrentVersionExpiration |
| Orphaned multipart upload costs | No AbortIncompleteMultipartUpload rule | Add `DaysAfterInitiation: 7` |
| Transition to wrong Glacier tier | Confused IR (90-day min) with Flexible (1-day min) | Verify the storage class name |
| Objects in Standard after 30+ days | Rule filter excludes the objects (wrong prefix) | Verify the `Filter` prefix matches |

---

## Appendix A — Storage class reference


| Storage class | Use case | Retrieval | Min lifecycle days | Cost (vs Standard) |
|---|---|---|---|---|
| `STANDARD` | Frequently accessed | Milliseconds | N/A | 1x baseline |
| `STANDARD_IA` | Infrequent, long-lived | Milliseconds | 30 days | ~40% cheaper |
| `ONEZONE_IA` | Infrequent, non-critical | Milliseconds | 30 days | ~52% cheaper |
| `GLACIER_IR` | Archives, millisecond access | Milliseconds | 90 days | ~68% cheaper |
| `GLACIER` (Flexible) | Long-term archives | 1-5 min to hours | 1 day after IA | ~80% cheaper |
| `DEEP_ARCHIVE` | Compliance archives | 12 hours | 180 days | ~95% cheaper |
| `INTELLIGENT_TIERING` | Unknown access patterns | Milliseconds (FA/IA) | 0 days | Varies |
