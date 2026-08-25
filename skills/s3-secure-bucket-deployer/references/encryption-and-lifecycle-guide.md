# Encryption and Lifecycle Guide — S3 Secure Bucket Deployer

Deep reference on SSE-S3 vs SSE-KMS tradeoffs, S3 Bucket Keys, lifecycle
storage class minimum durations, Object Lock, and cost-optimization
patterns for data lakes and log archives.

## SSE-S3 vs SSE-KMS: when to use each

### SSE-S3 (AES256)

- **Key management:** AWS-owned key (you never see or manage the key).
- **Cost:** Free — included in S3 storage pricing.
- **Performance:** No KMS API calls; no additional latency.
- **Audit trail:** No per-object KMS events in CloudTrail. You see S3
  API events but cannot correlate encryption key usage.
- **Key policy control:** None — AWS controls the key policy.
- **Cross-account:** Any principal with `s3:GetObject` permission can
  read the object; the key does not add an additional access gate.
- **Best for:** General-purpose storage, public CDN origins, logs that
  do not have compliance requirements, development/staging buckets.

### SSE-KMS (aws:kms)

- **Key management:** Customer-managed CMK (you create, rotate, and
  control the key policy). AWS-managed `aws/s3` key also available but
  does not allow key-policy customization.
- **Cost:** $1/key/month for customer-managed CMK + per-API-call fees
  ($0.03 per 10,000 KMS API calls). S3 Bucket Keys reduce per-call
  costs by ~99%.
- **Performance:** Each upload triggers `kms:GenerateDataKey`; each
  download triggers `kms:Decrypt`. With Bucket Keys, these are
  amortized — S3 generates a data key per bucket every few minutes and
  reuses it. Without Bucket Keys, expect ~50-100ms additional latency
  per API call due to KMS round-trip. KMS throttle limits (5,500-10,000
  req/s default per region) can bottleneck high-throughput workloads.
- **Audit trail:** Every `GenerateDataKey` and `Decrypt` is logged in
  CloudTrail with the caller identity, source IP, and key ARN. This
  gives you per-object encryption audit trail that SSE-S3 cannot
  provide.
- **Key policy control:** You define who can encrypt/decrypt. This is
  an additional access gate BEYOND the bucket policy — even if a
  principal has `s3:GetObject` permission, they cannot read the object
  unless the KMS key policy grants them `kms:Decrypt`.
- **Cross-account:** The key policy must explicitly grant the cross-
  account principal `kms:Decrypt` (for reads) or `kms:GenerateDataKey`
  (for writes). This is the primary mechanism for controlling cross-
  account access to SSE-KMS-encrypted objects.
- **Best for:** Compliance workloads (HIPAA, PCI-DSS, SOC2, FedRAMP),
  sensitive data (PII, financial, healthcare), cross-account shared
  data, any workload requiring per-object encryption audit trail.

### Decision matrix

| Requirement | Recommended encryption |
|---|---|
| Cost-sensitive, non-sensitive data | SSE-S3 |
| General-purpose app storage | SSE-S3 |
| CDN / static website origin | SSE-S3 |
| Compliance (HIPAA, PCI, SOC2) | SSE-KMS (customer-managed CMK) |
| Sensitive data (PII, financial) | SSE-KMS (customer-managed CMK) |
| Cross-account data sharing | SSE-KMS (customer-managed CMK) |
| Data lake with per-object audit | SSE-KMS (customer-managed CMK) |
| High-throughput write pipeline (>5k writes/s) | SSE-KMS + Bucket Keys |
| Development / staging | SSE-S3 |

## S3 Bucket Keys — internals

Without Bucket Keys, every object upload triggers a KMS
`GenerateDataKey` API call. S3 sends the plaintext data key to the KMS
service, which returns the ciphertext. This data key encrypts the
object. On download, S3 calls `kms:Decrypt` to recover the plaintext
data key.

With Bucket Keys enabled:
1. S3 requests a **bucket-level time-limited data key** from KMS
   (once every ~3 minutes per bucket).
2. This bucket key is used to **wrap per-object data keys** locally on
   the S3 side — no KMS API call per object.
3. The wrapped per-object key is stored alongside the object metadata.
4. On download, S3 unwraps the per-object key using the cached bucket
   key — again, no KMS API call per object.

**Cost impact:** for a bucket receiving 1 million writes/day:
- Without Bucket Keys: 1M KMS API calls/day = $3/day = ~$1,095/year.
- With Bucket Keys: ~480 KMS API calls/day (one every 3 min) = negligible.

**Security tradeoff:** Bucket Keys do NOT reduce the security of object
encryption. The per-object data key is still unique. The bucket key is
only accessible to the S3 service. The only difference is that KMS does
not see per-object API calls — the wrapping happens inside S3's
infrastructure.

**Always enable Bucket Keys for SSE-KMS buckets** unless you have a
specific compliance requirement that mandates per-object KMS request
logging (rare — most compliance frameworks accept Bucket Key
architecture).

## Lifecycle storage class reference

### Storage class comparison

| Storage class | Retrieval time | Retrieval cost | Min size | Min duration | Best for |
|---|---|---|---|---|---|
| `STANDARD` | Immediate | Free | — | — | Frequently accessed data |
| `STANDARD_IA` | Immediate | $0.01/GB | 128 KB | 30 days | Infrequently accessed (monthly) |
| `ONEZONE_IA` | Immediate | $0.01/GB | 128 KB | 30 days | Infrequently accessed, recreatable |
| `INTELLIGENT_TIERING` | Immediate (FA tier) | Free (auto-tier) | — | 30 days | Unknown/unpredictable access |
| `GLACIER_IR` | Immediate-milliseconds | $0.03/GB | 128 KB | 90 days | Archives needing instant access |
| `GLACIER` (flexible) | 1-5 min (min) / 3-5h (standard) / 12-15h (bulk) | $0.03/GB + req fee | — | 90 days | Long-term archive |
| `DEEP_ARCHIVE` | 12h (standard) / 48h (bulk) | $0.05/GB + req fee | — | 180 days | Compliance archive, DR backup |
| `EXPRESS_ONE_ZONE` | <10ms | Higher storage cost | — | — | Hot analytics (directory buckets) |

### Transition timing constraints

S3 enforces minimum storage durations per class. If you transition or
expire an object before its minimum duration, you pay a pro-rated
early-deletion fee.

```
STANDARD → STANDARD_IA:   minimum 30 days in STANDARD before transition
STANDARD → GLACIER:       minimum 90 days in STANDARD (or 60 from STANDARD_IA)
STANDARD → DEEP_ARCHIVE:  minimum 180 days in STANDARD
STANDARD_IA → GLACIER:    minimum 60 days in STANDARD_IA
GLACIER → DEEP_ARCHIVE:   minimum 90 days in GLACIER
```

**Practical transition timelines (common patterns):**

| Pattern | Transition 1 | Transition 2 | Transition 3 | Expire |
|---|---|---|---|---|
| General-purpose | IA @ 30d | GLACIER @ 90d | DEEP_ARCHIVE @ 365d | 2555d (7yr) |
| Log archive | GLACIER_IR @ 1d | GLACIER @ 30d | DEEP_ARCHIVE @ 180d | 2555d (7yr) |
| Data lake | INTELLIGENT_TIERING @ 0d | — | — | Per retention policy |
| Backup / DR | GLACIER @ 90d | DEEP_ARCHIVE @ 180d | — | Per retention policy |
| Compliance (WORM) | Object Lock (not lifecycle) | — | — | Per legal hold |

### Lifecycle filter — excluding small objects

STANDARD_IA, ONEZONE_IA, and GLACIER_IR have a minimum chargeable size
of 128 KB. Objects smaller than 128 KB cost MORE in these classes than
in STANDARD due to the minimum per-object fee. Use `ObjectSizeGreaterThan`
to exclude small objects from transitions:

```json
{
  "ID": "transition-large-objects",
  "Status": "Enabled",
  "Filter": {
    "Prefix": "",
    "ObjectSizeGreaterThan": 131072
  },
  "Transitions": [
    {"Days": 30, "StorageClass": "STANDARD_IA"}
  ]
}
```

## Object Lock (compliance retention)

S3 Object Lock provides Write-Once-Read-Many (WORM) storage for
compliance retention. Two modes:

- **Compliance mode:** the retention period cannot be shortened or
  removed by ANYONE, including the root account. An object in compliance
  mode cannot be deleted or overwritten until the retention period
  expires. This is for regulatory requirements (SEC 17a-4, CFTC, FINRA,
  HIPAA).
- **Governance mode:** the retention period can be overridden by
  principals with `s3:BypassGovernanceRetention` permission. This is for
  operational data protection where authorized users may need to delete
  objects before retention expires.

**Object Lock requirements:**
1. Must be enabled at bucket CREATION time (cannot be added to existing
   buckets without AWS Support).
2. Versioning is automatically enabled.
3. Each object version gets its own retention setting.
4. Legal Hold can be placed on individual object versions to prevent
   deletion indefinitely (until the hold is removed).

**Object Lock vs Lifecycle:**
- Lifecycle expiration is a cost-optimization tool — it deletes objects
  on a schedule. It does NOT prevent deletion before the expiration date.
- Object Lock prevents deletion before the retention period — it is a
  compliance control. Use Object Lock for regulatory retention; use
  lifecycle for cost optimization. They can coexist on the same bucket.

## Cost-optimization patterns

### Data lake cost optimization

1. Use `INTELLIGENT_TIERING` for the raw/landing zone — you do not know
   the access pattern, and Intelligent-Tiering auto-moves objects to the
   cheapest tier based on actual access.
2. Use `STANDARD` for the curated/processed zone (frequently queried by
   Athena / Spark / SageMaker).
3. Use `GLACIER_IR` or `GLACIER` for the archive zone (rarely queried).
4. Enable S3 Storage Lens to identify cost-optimization opportunities
   (buckets with high storage but low access).

### Log archive cost optimization

1. Transition to `GLACIER_IR` after 1 day (for logs that may need
   immediate investigation) or `GLACIER` after 30 days (for long-term
   archive).
2. Expire non-current versions at 180 days (versioned log buckets
   accumulate delete markers and old versions).
3. Use S3 Batch Operations to transition existing logs (lifecycle only
   applies to new objects).

### Versioning cost control

Versioning stores every version of every object. Without lifecycle
rules on non-current versions, storage costs grow indefinitely. Always
pair versioning with:
- `NoncurrentVersionExpiration` — delete old versions after N days.
- `NoncurrentVersionTransitions` — move old versions to cheaper storage
  before expiring.
- `ExpiredObjectDeleteMarker: true` — clean up orphaned delete markers.

---

## Standard lifecycle configuration template (moved from SKILL.md Step 7)

```bash
aws s3api put-bucket-lifecycle-configuration \
  --bucket <BUCKET> \
  --lifecycle-configuration '{
    "Rules": [
      {
        "ID": "transition-to-ia",
        "Status": "Enabled",
        "Filter": { "Prefix": "" },
        "Transitions": [{ "Days": 30, "StorageClass": "STANDARD_IA" }],
        "NoncurrentVersionTransitions": [{ "NoncurrentDays": 30, "StorageClass": "STANDARD_IA" }],
        "NoncurrentVersionExpiration": { "NoncurrentDays": 90 },
        "AbortIncompleteMultipartUpload": { "DaysAfterInitiation": 7 }
      }
    ]
  }'
```
