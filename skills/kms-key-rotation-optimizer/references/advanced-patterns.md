# Advanced Patterns — KMS Key Rotation Optimizer

Load-on-demand deep dives moved verbatim from SKILL.md.

## Mindset — full framing (moved from SKILL.md)

KMS cost optimization is an inventory and API-call-volume exercise. The
goal is to eliminate keys that no longer encrypt or decrypt data, and to
consolidate keys where fine-grained separation is unnecessary — not to
weaken encryption posture.

Four principles guide every recommendation:

- **Keys are the fixed cost.** Every customer-managed key bills $1/month
  regardless of API call volume. The highest-leverage action is inventory
  reduction: delete unused keys and consolidate low-usage keys where
  access policy boundaries allow.
- **API calls are the variable cost.** KMS charges $0.03 per 10,000
  requests for customer-managed keys. High-volume Decrypt/Encrypt
  patterns (e.g., per-record encryption) drive cost. AWS managed keys
  include a free tier of requests.
- **Rotation is free, not a cost lever.** Enabling rotation has no
  billing impact. The optimization is about ensuring rotation is ENABLED
  for compliance, not about reducing rotation cost.
- **Grants accumulate silently.** Each grant has a lifecycle. Expired
  grants that are not retired remain in the key's grant list, adding
  latency to authorization checks and complicating audits. Grant cleanup
  is a hygiene issue, not a direct cost issue — but it prevents key
  bloat that leads to duplicate key creation.

## Configuration dependency graph

```
KMS Key ─┬─ Rotation ──── Automatic (annual, free, transparent)
         │                Manual (alias reassignment, new key)
         ├─ Grants ────── Active grants (authorization delegation)
         │                Expired grants (should be retired)
         ├─ Alias ─────── Stable reference (survives rotation)
         ├─ KeyPolicy ─── Access control (principal-based)
         ├─ MultiRegion ─ Primary key ($1/month)
         │                Replica keys ($1/month per region)
         ├─ Tags ──────── Cost allocation tracking
         └─ Deletion ──── PendingWindow (7-30 days)
                          Disabled (billing stops after deletion)
```

Each edge in this graph is a potential cost or hygiene lever. Walk every
node before emitting a verdict.

## Step 0 — Non-obvious behaviours that change the recommendation (moved from SKILL.md)

These operational gotchas route a recommendation away from the obvious
choice:

- **Automatic rotation preserves the key ARN.** When annual rotation
  fires, AWS generates new backing key material under the SAME key ARN.
  All aliases, key policies, grants, and application references continue
  to work. No code changes needed. This is why rotation is free and
  transparent.
- **Manual rotation creates a NEW key.** Manual rotation means creating
  a new key, updating the alias to point at it, and eventually deleting
  the old key. This is necessary only for custom rotation cadences or
  when key material must change immediately. It costs $1/month for each
  key during the overlap period.
- **Cross-account grant tokens are ephemeral.** When a principal in
  account B uses a key in account A, a grant is created with a grant
  token. The grant token must be passed with the API call. If the grant
  expires or is revoked, the cross-account call fails immediately. Grant
  lifecycle management is critical for cross-account encryption.
- **Scheduled key deletion has a 7-30 day window.** After `schedule-key-
  deletion`, the key enters `PendingDeletion` state and stops accepting
  Decrypt/Encrypt requests. The $1/month billing continues until the
  window expires and the key is permanently deleted. The minimum window
  is 7 days; maximum is 30 days (120 days extended via support case).
- **Deleting a key that encrypts active data makes that data permanently
  unrecoverable.** Unlike most AWS resources, KMS key deletion is
  IRREVERSIBLE. Data encrypted under the key can never be decrypted.
  Always verify no encrypted resources depend on the key before deletion.
- **Multi-region keys have independent replica lifecycles.** Each replica
  key bills $1/month per region. A replica can be deleted independently
  of the primary key. Deleting a replica does not affect the primary or
  other replicas.
- **Grants do not expire automatically.** A grant with no `Constraints`
  or `ExpiryDate` persists until explicitly retired. Long-lived grants
  accumulate and complicate key policy audits. Retire grants when the
  delegated permission is no longer needed.
- **AWS managed keys rotate annually by default.** You cannot disable
  rotation on AWS managed keys. They are free ($0/month) and include a
  generous free request tier. Prefer AWS managed keys when fine-grained
  key separation is not required.
- **The $1/month per key is prorated.** A key created mid-month and
  deleted mid-month still incurs partial charges. The billing is not
  per-day but per-month with proration for partial months.
- **GenerateDataKey calls are billed as requests even though the data
  key is generated client-side.** Each `GenerateDataKey` API call counts
  as one request at $0.03/10K for customer-managed keys. High-frequency
  envelope encryption patterns should cache data keys to reduce API
  volume.

## Expert heuristic (domain expert rules of thumb)

Three rules that a KMS cost expert applies instinctively:

1. **Automatic rotation transparency (same key ARN, new backing key).**
   When annual automatic rotation fires on a customer-managed key, AWS
   generates new backing key material under the SAME key ARN. Every
   alias, policy, grant, and application reference continues to work
   without any change. This is fundamentally different from manual
   rotation, which creates a new key ARN. The expert takeaway: always
   prefer automatic rotation — it is free, transparent, and requires
   zero code changes. Manual rotation is only for custom cadences or
   compromise response.

2. **Cross-account grant token lifecycle.** When account B uses a key in
   account A, a grant is created with a unique grant token. The grant
   token must be passed with each API call. Grants do NOT auto-expire
   unless an ExpiryDate is set at creation. This means cross-account
   grants accumulate silently. The expert practice: always set
   ExpiryDate on cross-account grants and implement a grant-refresh
   mechanism in the consuming account. Never create open-ended grants
   for cross-account access.

3. **Scheduled key deletion 7-30 day window.** After scheduling deletion,
   the key enters PendingDeletion and stops accepting API requests, but
   the $1/month billing continues until the window expires and the key
   is permanently deleted. The minimum is 7 days, maximum is 30 days
   standard (120 days via support case). The expert practice: for keys
   with no encrypted data, use 7 days to minimize billing. For keys that
   may encrypt historical data, use 30 days as a safety buffer for
   discovering missed associations. Never use the extended 120-day window
   unless regulatory mandates require it.

## Recent AWS features (2024-2026)

- **Automatic key rotation for customer-managed keys (2022-2024 GA):**
  Annual automatic rotation is available for all symmetric customer-
  managed keys. Rotation is transparent — same key ARN, new backing key.
  Enabled via `aws kms enable-key-rotation`.
- **Key rotation transparency (2024-2025):** AWS published detailed
  documentation confirming that automatic rotation preserves all key
  metadata (ARN, alias, policy, grants). No application changes needed.
- **Multi-region key replicas (2024):** GA support for multi-region
  keys. Each replica is independently billable at $1/month per region.
- **Grant limits increase (2024-2025):** Per-key grant limit increased
  to ~2500 grants. Grant bloat still degrades evaluation latency.
- **Cost Optimization Hub KMS recommendations (2025-2026):** Automated
  detection of unused customer-managed keys. Use as input to this skill.
- **CloudTrail KMS event filtering (2024):** Enhanced CloudTrail
  lookup-events supports filtering by KMS event name (Decrypt, Encrypt,
  GenerateDataKey) for efficient API call volume analysis.
- **KMS key tags for cost allocation (2024):** Tags on KMS keys flow
  through to Cost Explorer for per-application cost attribution.
