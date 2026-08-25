# Advanced Patterns — s3-secure-bucket-deployer

Moved verbatim from SKILL.md (progressive disclosure; load on demand). Sections keep their original headings.

## Reasoning framework (why the provisioning order matters)

S3 configuration items have **dependency and timing semantics** that make
the provisioning order non-trivial. Applying configurations in the wrong
order creates windows of exposure or silently fails:

1. **Block Public Access FIRST** — BPA is the foundation. It prevents
   accidental public exposure during the rest of the setup. If you
   create a bucket, upload objects, and THEN enable BPA, there is a
   window where a misconfigured ACL or policy (or a race with a
   concurrent policy attach) exposes data. Enabling BPA at creation
   time closes this window before any data lands.

2. **Default encryption BEFORE any object upload** — server-side
   encryption is applied at write time. Objects written before default
   encryption is configured are NOT retroactively encrypted by the
   bucket-level setting. You would need S3 Batch Operations to encrypt
   existing objects after the fact.

3. **Object Ownership = BucketOwnerEnforced BEFORE granting cross-account
   write access** — this setting disables ALL ACLs on the bucket. If a
   cross-account writer has been using ACLs to share objects, setting
   BucketOwnerEnforced silently breaks that workflow. Set it early so
   all access flows through bucket policies from the start.

4. **Versioning BEFORE lifecycle rules and replication** — both lifecycle
   rules for non-current versions and S3 replication REQUIRE versioning
   to be enabled. Configuring either without versioning is a silent
   no-op (lifecycle) or an API error (replication).

5. **Bucket policy AFTER BPA** — the bucket policy enforces HTTPS-only
   and SSE-KMS on uploads. It is the enforcement layer; BPA is the
   prevention layer. Both are needed for defense-in-depth.

6. **Access logging EARLY** — logging captures all access events. The
   sooner it is enabled, the more audit trail you have. Log delivery
   requires a log-delivery ACL or bucket policy grant on the target
   logging bucket — set this up before the data bucket receives
   production traffic.

7. **Lifecycle AFTER versioning** — lifecycle rules that transition or
   expire non-current versions require versioning. Rules also have
   minimum-storage-duration constraints (STANDARD_IA: 30 days, GLACIER:
   90 days via STANDARD_IA transition). Configure lifecycle after
   versioning is confirmed enabled.

8. **Replication LAST** — replication requires versioning, a destination
   bucket with its OWN security baseline, and an IAM role with
   `s3:ReplicateObject` + KMS decrypt permissions. It is the most
   complex configuration and depends on all prior steps being correct.

The order matters because each layer DEPENDS ON or is STRENGTHENED BY
the prior layer. The provisioning procedure below follows this order.

---

## Cross-dependency gotchas

**Cross-dependency gotchas** (not visible in the table):
- Setting `BucketOwnerEnforced` on the LOG TARGET silently breaks log
  delivery if the log-delivery ACL was the only grant — must switch to
  a bucket policy grant (see `references/bucket-policy-examples.md`).
- Enabling SSE-KMS on a bucket with cross-account readers requires the
  KMS key policy to grant them `kms:Decrypt`; the bucket policy alone
  is not enough.
- Removing the last KMS key referenced by a bucket policy is
  irreversible — encrypted objects become cryptographically unreadable.

---

## Expert heuristic: BPA timing window

The most dangerous period in an S3 bucket's lifecycle is the gap between
bucket creation and BPA enablement. This is when most real-world data
leaks occur — not from persistent misconfiguration, but from a race
condition during initial setup.

**The window:**

```text
T0: Bucket created (no public-access protection yet)
T1: Default encryption set
T2: Bucket policy attached
T3: BPA enabled at bucket level

Gap: T0 → T3 — bucket exists with NO public-access protection
```

**Why this matters in practice:**
- Internet scanners (GrayhatWarfare, Censys, Shodan) enumerate new S3
  buckets within **2-5 minutes** of creation. If any object is uploaded
  during T0 to T3, it is discoverable.
- A concurrent process (CI/CD pipeline, Lambda function) may upload
  objects to the bucket before BPA is enabled, creating a window even
  when the provisioning script is sequential.
- A bucket policy with `Principal: "*"` attached BEFORE BPA is enabled
  creates a public-access window even if the policy is later corrected.

**CloudFormation race condition:** when using CloudFormation, BPA is
applied as a SEPARATE resource (`AWS::S3::BucketPublicAccessBlock`) that
is created AFTER the `AWS::S3::Bucket` resource reaches
`CREATE_COMPLETE`. There is a real window where the bucket exists but
BPA is not yet enforced. To eliminate it:

```yaml
BucketPublicAccessBlock:
  Type: AWS::S3::BucketPublicAccessBlock
  Properties:
    Bucket: !Ref MyBucket
    BlockPublicAcls: true
    IgnorePublicAcls: true
    BlockPublicPolicy: true
    RestrictPublicBuckets: true

BucketPolicy:
  Type: AWS::S3::BucketPolicy
  Properties:
    Bucket: !Ref MyBucket
    PolicyDocument: ...
  DependsOn: BucketPublicAccessBlock   # enforce order
```

**Terraform:** use `aws_s3_bucket_public_access_block` as a separate
resource and add `depends_on = [aws_s3_bucket_public_access_block.my]`
on any resource that uploads objects.

**Account-level BPA is the real fix:** if account-level BPA is enabled
BEFORE any bucket is created in the account, the window is zero — all
new buckets inherit the account-level setting at creation time. Make
account-level BPA a one-time account bootstrap step, not a per-bucket
step. This eliminates the race entirely.

---

## Expert heuristic: SSE-KMS Bucket Keys cost model

When using SSE-KMS with cross-account or high-throughput access, Bucket
Keys are not a "nice to have" — they are the difference between a $1K/year
and a $1M/year KMS bill.

**Without Bucket Keys:**

```text
Every GET  → 1x kms:Decrypt call         ($0.03 / 10k)
Every PUT  → 1x kms:GenerateDataKey call ($0.03 / 10k)
Every HEAD → 1x kms:Decrypt call (if SSE-KMS object)

At 10M GETs/day without Bucket Keys:
  KMS cost = 10,000,000 / 10,000 * $0.03 = $3,000/day = $1,095,000/year
```

**With Bucket Keys enabled:**

```text
S3 negotiates ONE data key per bucket (time-limited, reused ~3 min).
KMS calls drop by ~99% — only 1x kms:GenerateDataKey every ~3 min.

At 10M GETs/day with Bucket Keys:
  KMS calls = ~480/day (1 every 3 min)
  KMS cost  = 480 / 10,000 * $0.03 = $0.0014/day = ~$0.52/year
```

The 99% reduction is real and documented. The nuance a baseline model
misses is the **cross-account amplification**: when a bucket is accessed
by principals in OTHER AWS accounts (cross-account replication, shared
data lake, analytics pipeline), each cross-account access without Bucket
Keys requires a KMS call in the KEY-OWNING account. This means:

1. The KMS quota (5,500-10,000 req/s region default) is shared across ALL
   cross-account readers — a single hot bucket can throttle KMS for the
   entire account.
2. The KMS cost is billed to the key owner, not the accessor. A data lake
   bucket accessed by 50 downstream accounts generates 50x the KMS calls
   with no way to charge back.

**Enable Bucket Keys on:**
- Any SSE-KMS bucket with more than 1,000 reads/day
- ANY bucket with cross-account access (no exceptions)
- Replication source and destination buckets (replication doubles KMS calls)

**Do NOT enable Bucket Keys on:**
- Buckets where you need per-request KMS audit in CloudTrail (Bucket Keys
  reduce the audit granularity to per-bucket, not per-request).
- Buckets with per-object KMS keys (different CMK per object) — Bucket
  Keys require a bucket-level default key.

---

### Step 1 — Block Public Access: rationale and common mistakes

**Why all 4 settings**: Each blocks a different vector — `BlockPublicAcls`
prevents PUT with public ACL, `IgnorePublicAcls` ignores existing public
ACLs, `BlockPublicPolicy` prevents attaching a public bucket policy,
`RestrictPublicBuckets` restricts access to public buckets to only known
principals. All 4 together = full BPA.

**Common mistake**: Enabling only bucket-level BPA without account-level.
Account-level BPA overrides any bucket-level relaxation. Always set both.

---

### Step 2 — Default encryption: rationale and common mistakes

**Why before upload**: Encryption applies at write time. Objects written
before this setting are NOT retroactively encrypted.

**KMS cost warning**: SSE-KMS incurs $0.03 per 10,000 requests. For
high-throughput buckets (logs, CDN), SSE-S3 is the better default. Use
SSE-KMS only when compliance or audit requirements mandate it.

**Common mistake**: Forgetting to set `BucketKeyEnabled: true` on
SSE-KMS buckets. Without Bucket Keys, every PutObject triggers a
`kms:GenerateDataKey` call ($0.03/10k + ~50-100ms latency) and you
risk hitting KMS throttle limits (5,500-10,000 req/s region default)
on high-throughput workloads.

---

### Step 3 — Object Ownership: rationale and common mistakes

**Why**: ACLs are a legacy access-control mechanism that's easy to
misconfigure. BucketOwnerEnforced eliminates ACL-based exposure vectors.
Cross-account access must flow through bucket policies (more auditable).

**Common mistake**: Flipping BucketOwnerEnforced on a bucket that has
existing cross-account writers using ACL-granted object ownership. The
switch is immediate and silent — those writers' next PutObject will
succeed but lose their per-object ownership, breaking any downstream
ACL-based read workflow. Audit `s3:GetObjectAcl` across writers first;
migrate grants to the bucket policy before flipping.

---

### Step 4 — Versioning: rationale and common mistakes

**Why**: Versioning protects against accidental deletion and overwrites.
Required for lifecycle rules on non-current versions and for replication.

**Common mistake**: Setting `MFADelete=Enabled` from an IAM user or
role. MFA Delete can ONLY be configured by the root account credentials
— an IAM principal issuing the call gets a silent success with no MFA
enforcement. Verify the actual MFADelete state with
`aws s3api get-bucket-versioning --bucket <BUCKET>` after the call.

---

### Step 5 — Bucket policy: common mistakes

**Common mistake**: Using `Principal: "*"` with `Effect: "Allow"`.
The deny-style policies above are safe with `*` because the condition
gates the call. An ALLOW with `Principal: "*"` is genuine public access
and will be blocked by BPA — but if BPA is ever relaxed, the bucket
becomes public. Always use deny-style for enforcement policies.

---

### Step 6 — Access logging: common mistakes

**Common mistake**: Setting the log target to a bucket with
`BucketOwnerEnforced` enabled but granting log delivery via the legacy
`log-delivery` ACL. BucketOwnerEnforced disables ALL ACLs, so S3 log
delivery silently stops with no error. Grant `s3:PutObject` to
`logging.s3.amazonaws.com` via a bucket policy on the log target —
see `references/bucket-policy-examples.md` "Log-delivery grant".

---

### Step 7 — Lifecycle rules: common mistakes

**Common mistake**: Writing `NoncurrentVersion*` rules before checking
that versioning is enabled. Without versioning the rule applies
silently as a no-op — the API returns success, no objects transition,
and you only discover the cost leak weeks later via Storage Lens. Also:
transitioning objects smaller than 128 KB to STANDARD_IA / ONEZONE_IA /
GLACIER_IR costs MORE than leaving them in STANDARD due to the
minimum-size fee — use `ObjectSizeGreaterThan: 131072` in the filter.

---

### Step 8 — Replication: common mistakes

**Common mistake**: Forgetting that replication does NOT backfill
objects written before the rule was added. Only new PutObject calls
after the rule is active are replicated. For pre-existing objects, run
an S3 Batch Operations Copy job or restart replication with
`ExistingObjectReplication: Enabled` (v2 config only).

---

## Recent AWS features

- **S3 Express One Zone (directory buckets)**: Single-AZ, lowest latency
  for ML/AI and analytics. $0.16/GB. Use for hot data requiring <10ms
  latency. Does NOT support all lifecycle/replication features.
- **S3 Tables**: Managed Apache Iceberg tables stored in S3. Requires
  different provisioning (catalog database + table bucket).
- **S3 Object Versioning + BPA interaction**: As of 2024, BPA at account
  level overrides bucket-level BPA relaxations for ALL versions.
- **Intelligent-Tiering Archive configurations**: Can now specify Instant
  Access vs Deep Archive access tiers within Intelligent-Tiering.
- **S3 Storage Lens**: Organization-level dashboard for storage
  visibility. Enable to get metrics on noncurrent bytes, storage class
  distribution, and object age — critical for lifecycle planning.
