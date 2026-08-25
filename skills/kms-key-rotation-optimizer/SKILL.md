---
name: kms-key-rotation-optimizer
description: 'Optimises AWS KMS key rotation and lifecycle cost across seven dimensions: key inventory audit (orphaned keys at $1/key/month, unused key detection via CloudTrail API call analysis), rotation strategy (enable automatic annual rotation on customer-managed keys — free and transparent, same key ARN), grant optimization (retire expired grants on deleted IAM principals), alias management for rotation transparency (aliases survive key changes), cross-account key usage (grant token lifecycle, shared vs per-account keys), multi-region keys for DR (replica keys cost $1/key/month per region, detect unused replicas), and deletion window management (7-30 day pending deletion window, billing continues until expiry). Emits FURTHER_OPTIMIZATION_AVAILABLE, OPTIMIZED, or ALREADY_OPTIMAL. Use when reviewing KMS spend, auditing key inventory, or planning rotation strategy.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline recommendation classification works from pasted KMS key configurations and CloudTrail API call summaries. Live-account optimization uses aws kms list-keys, aws kms describe-key, aws kms get-key-rotation-status, aws kms list-aliases, aws kms list-grants, aws kms list-resource-tags, aws cloudtrail lookup-events (Decrypt, Encrypt, GenerateDataKey), aws ce get-cost-and-usage (AWS CLI v2, SSO or key-based...
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: 'true'
  phase: '3'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Security
  task_type: optimize
  skill_class: capability
  lifecycle_status: active
  verdict_shape: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
  when_to_use: Optimising KMS key cost, auditing key inventory, detecting unused or orphaned keys, evaluating rotation strategy (automatic vs manual), cleaning up stale grants, analysing cross-account key usage, reviewing multi-region key replicas, or managing key deletion windows.
  when_not_to_use: KMS key policy security auditing (use kms-key-policy-auditor), KMS key deployment (use kms-key-deployer), KMS key operational rotation execution (use kms-key-rotation-operator), or Secrets Manager rotation (use secrets-rotation-operator). This skill focuses on cost-driven optimization decisions, not security policy review or functional rotation execution.
  activation_triggers: optimise KMS cost, KMS key inventory audit, KMS unused keys, KMS key rotation strategy, KMS grant cleanup, KMS stale grants, KMS cross-account cost, KMS multi-region keys cost, KMS key deletion window, KMS FinOps savings, reduce KMS bill, KMS orphaned keys, KMS API call analysis, KMS monthly savings estimate
  invocation_schema: 'Input: either (a) a key identifier + live-account context, (b) a Cost Explorer KMS cost breakdown, OR (c) a CloudTrail KMS API call summary with at least 14 days of observation. Output: a deterministic TARGET/VERDICT/REASON/RECOMMENDATION/ESTIMATED_SAVINGS/REMEDIATION_STEPS block per key or key group, where VERDICT is one of OPTIMIZED, FURTHER_OPTIMIZATION_AVAILABLE.'
  invocation_example: "# Minimal valid input (offline finding classification):\nKeyId: arn:aws:kms:us-east-1:123456789012:key/abcd-1234\nKeyState: Enabled\nKeyManager: CUSTOMER\nKeySpec: SYMMETRIC_DEFAULT\nRotationStatus: Enabled (annual)\nAlias: alias/app-data-encryption\nGrants: 15 active (3 expired, not retired)\nCloudTrail (last 30 days):\n  - Decrypt: 50 calls\n  - Encrypt: 20 calls\n  - GenerateDataKey: 10 calls\nMultiRegion: False\nRegion: us-east-1\nEmit the standard optimization block (TARGET, VERDICT, REASON,\nRECOMMENDATION, ESTIMATED_SAVINGS, REMEDIATION_STEPS)."
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: KMS, key rotation, cost optimization, customer managed keys, AWS managed keys, key lifecycle, grant management, alias management, multi-region keys, key deletion, CloudTrail, cross-account, FinOps, CloudOps, security
  tags: kms, security, cost-optimization, finops, key-management, encryption, key-rotation
---

# KMS Key Rotation Optimizer

## What this skill does

Translates a KMS key inventory into a concrete cost-optimization
recommendation with a dollar-denominated savings estimate. The verdict is
the highest-leverage action across seven dimensions — key inventory,
rotation configuration, grant lifecycle, alias management, cross-account
usage, multi-region replicas, and deletion window management — applied in
priority order. Always pairs the recommendation with exact CLI commands.

## Quick navigation

| Section | What it covers | When to jump here |
|---|---|---|
| Quick start | Four headline rules and the cost formula | First read |
| Mindset | Why key inventory reduction is the #1 lever | Understanding the approach |
| Quick reference — verdict thresholds | Decision matrix at a glance | Classifying a key |
| Pre-flight data gate | CloudTrail API calls, Cost Explorer, key inventory | Before any recommendation |
| Step 0 non-obvious behaviours | Rotation transparency, grant tokens, deletion window | Edge cases |
| Step 1 Key inventory audit | Unused key detection, orphaned key cleanup | The headline savings dimension |
| Step 2 Rotation strategy | Automatic vs manual rotation | All customer-managed keys |
| Step 3 Grant optimization | Stale grant cleanup, grant lifecycle | Keys with grants |
| Step 4 Alias management | Alias-based references for rotation transparency | Keys referenced by ID |
| Step 5 Cross-account usage | Grant token lifecycle across accounts | Shared keys |
| Step 6 Multi-region keys | Replica key cost optimization | DR key configurations |
| Step 7 Deletion window | 7-30 day window, pending deletion audit | Key retirement |
| Step 8 Impact estimation | The cost formula and worked math | Every recommendation |
| Output format | VERDICT block + worked examples | Emitting the result |
| Anti-Patterns — NEVER | Common misclassifications | Self-check before emit |
| Pre-flight safety checks | CONFIRM gate, key disable, data verification | Before any apply CLI |

## Quick start

- **Customer-managed keys cost $1/month each.** Every enabled key bills
  $1/month regardless of usage. A key with 0 API calls in 30 days is
  pure waste. Inventory and delete unused keys first.
- **Cost formula (memorise this):**
  `monthly_cost = (customer_managed_keys × $1.00)
               + (api_calls_10k × $0.03)
               + (multi_region_replicas × $1.00)`
- **Automatic rotation is free and transparent.** Enabling annual
  rotation on a customer-managed key does NOT change the key ARN, key
  ID, or alias. The backing key material changes, but all references
  remain valid. There is no cost for rotation itself.
- **AWS managed keys cannot be deleted.** They are created and managed
  by AWS services (S3, EBS, etc.) and bill $0 — but they also cannot be
  turned off. Focus optimization on CUSTOMER-managed keys only.

## Mindset

Full mindset and four-principles framing moved verbatim to
[references/advanced-patterns.md](references/advanced-patterns.md).

## Quick reference — verdict thresholds

| Observation (14-30 day window) | Verdict | Recommendation |
|---|---|---|
| Customer-managed key with 0 Decrypt/Encrypt/GenerateDataKey calls in 30 days AND no resource associations | **FURTHER_OPTIMIZATION_AVAILABLE** (unused key) | Step 1 — schedule key deletion |
| Customer-managed key with < 100 API calls/month AND no compliance requirement for separate key | **FURTHER_OPTIMIZATION_AVAILABLE** (consolidation) | Step 1 — consolidate into a shared key |
| Customer-managed key with rotation Disabled AND no regulatory prohibition on rotation | **FURTHER_OPTIMIZATION_AVAILABLE** (rotation) | Step 2 — enable automatic rotation |
| Key with 5+ expired grants not retired | **FURTHER_OPTIMIZATION_AVAILABLE** (grants) | Step 3 — retire expired grants |
| Multi-region key with replica in a region that has 0 API calls in 30 days | **FURTHER_OPTIMIZATION_AVAILABLE** (replica) | Step 6 — delete the unused replica |
| Key in PendingDeletion state with deletion window > 7 days AND operator wants faster deletion | **FURTHER_OPTIMIZATION_AVAILABLE** (window) | Step 7 — shorten deletion window (minimum 7 days) |
| Two or more customer-managed keys serving the same application with identical key policies | **FURTHER_OPTIMIZATION_AVAILABLE** (consolidation) | Step 1 — consolidate into one key |
| All dimensions verified AND a change was applied and confirmed this session | **OPTIMIZED** | Emit post-state verification |
| All keys active, rotation enabled, grants clean, no orphaned replicas | **ALREADY_OPTIMAL** | None — continue monitoring |


## Pre-flight: data gate (run before any optimization decision)

Optimization decisions are only as good as the underlying data. Pull
these metrics before any recommendation. Full CLI sequences are in
`references/kms-pricing-and-lifecycle.md`.

**Required data sources** (summarized — see reference for full CLI):
Numbered data-source CLI list moved verbatim to
[references/diagnostic-commands.md](references/diagnostic-commands.md).

### Data-quality short-circuits

| Condition | Effect on optimization |
|---|---|
| `KeyState = PendingDeletion` | Key already scheduled for deletion. Report remaining window. No further optimization. |
| `KeyState = Disabled` | Key is not billing for API calls but still bills $1/month. Evaluate deletion. |
| `KeyManager = AWS` | AWS-managed key. No cost optimization available ($0/month). Skip. |
| CloudTrail lookup returns 0 events in 30 days | Key is a candidate for deletion. Cross-check resource associations. |
| CloudTrail lookup window < 14 days | Extend to minimum 14 days; 30 days preferred. |
| Key has 50+ grants | Grant bloat. Audit for expired grants to retire. |
| Key is referenced by an S3 bucket default encryption config | Key is in use. Do NOT delete without updating bucket encryption. |
| Key is referenced by an EBS volume | Key is in use. Do NOT delete — encrypted volumes become unreadable. |

## Process — Optimization logic (apply in order)

### Step 0: Non-obvious behaviours that change the recommendation

The ten non-obvious behaviours moved verbatim to
[references/advanced-patterns.md](references/advanced-patterns.md).

### Step 1: Key inventory audit (the #1 lever)

Every customer-managed key bills $1/month regardless of usage volume.
Key reduction is the highest-leverage cost action.

**Unused key detection:**
Unused-key detection procedure moved verbatim to
[references/diagnostic-commands.md](references/diagnostic-commands.md).

**Key consolidation:**
Key consolidation procedure moved verbatim to
[references/diagnostic-commands.md](references/diagnostic-commands.md).

**Decision gate:**

| API calls (30 day) | Resource associations | Verdict |
|---|---|---|
| 0 calls | None detected | Schedule deletion — saves $12/year |
| < 100 calls | Decrypt-only (historical data) | Evaluate consolidation — may save $12/year |
| < 100 calls | Active resources | Consolidate with a shared key if policy allows |
| > 100 calls | Active resources | Keep key; evaluate other dimensions |

**CRITICAL:** Before recommending deletion, verify the key does not
encrypt any active data. Data encrypted under a deleted key is
**permanently unrecoverable**.

### Step 2: Rotation strategy optimization

Rotation is a compliance and security best practice, not a cost lever.
The optimization ensures rotation is ENABLERED where required.

**Automatic rotation decision:**

| Key manager | Current rotation | Recommendation |
|---|---|---|
| AWS managed | Enabled (automatic) | No action — rotates annually, no cost |
| Customer managed | Enabled (annual) | No action — rotation is transparent and free |
| Customer managed | Disabled | Enable rotation: `aws kms enable-key-rotation --key-id <id>` |
| Customer managed | Disabled (regulatory prohibition) | Document the exception in tags |

**Manual rotation evaluation:**
- Manual rotation (create new key, re-point alias) costs $1/month for
  the new key during overlap. Only justified when:
  - Custom rotation cadence is required (e.g., quarterly)
  - Key material compromise is suspected
  - Compliance mandates fresh key material immediately
- For standard annual rotation, automatic rotation is always preferred
  (free, transparent, same ARN).

### Step 3: Grant optimization

Grants delegate specific permissions on a key to principals. Expired or
stale grants accumulate and should be retired.

**Grant audit:**
Grant audit procedure moved verbatim to
[references/diagnostic-commands.md](references/diagnostic-commands.md).

**Grant hygiene rules:**
- Grants do NOT auto-expire unless `ExpiryDate` is set at creation.
- A grant on a deleted IAM principal persists until retired.
- Grant retirement is idempotent and safe.
- Grant count per key has a soft limit of ~2500. Bloat degrades key
  policy evaluation latency.

### Step 4: Alias management for rotation transparency

Aliases provide a stable name that survives key rotation and replacement.
Applications should reference aliases, not key IDs or ARNs.

**Alias audit:**
Alias audit procedure moved verbatim to
[references/diagnostic-commands.md](references/diagnostic-commands.md).

**Alias optimization:**
- An alias is free. There is no cost benefit to reducing aliases.
- The value is operational: alias-based references allow manual key
  rotation without code changes (just re-point the alias).
- Multiple aliases can point to the same key (e.g., alias/prod and
  alias/current both → same key).
- Orphaned aliases (target key deleted) should be cleaned up:
  `aws kms delete-alias --alias-name alias/<name>`

### Step 5: Cross-account key usage optimization

Cross-account usage introduces grant token lifecycle complexity. The
cost optimization focuses on ensuring the key is not duplicated across
accounts unnecessarily.

**Cross-account audit:**
Cross-account audit procedure moved verbatim to
[references/diagnostic-commands.md](references/diagnostic-commands.md).

**Decision: shared key vs per-account keys:**
- A shared cross-account key costs $1/month total.
- Per-account customer-managed keys cost $1/month per account.
- If fine-grained isolation is required, per-account keys are justified.
- If the data is shared anyway, a single cross-account key is cheaper.

### Step 6: Multi-region key optimization

Multi-region keys have a primary key and optional replica keys. Each
replica bills $1/month per region.

**Multi-region audit:**
Multi-region audit procedure moved verbatim to
[references/diagnostic-commands.md](references/diagnostic-commands.md).

**Multi-region cost:**
Multi-region cost math moved verbatim to
[references/diagnostic-commands.md](references/diagnostic-commands.md).

### Step 7: Deletion window management

The key deletion window controls how quickly a scheduled-deletion key is
permanently removed.

**Deletion window decision:**

| Scenario | Window | Recommendation |
|---|---|---|
| Key is unused, verified no encrypted data | 7 days (minimum) | Fastest permanent deletion |
| Key may encrypt historical data | 30 days (maximum) | Allow time for audit and re-encryption if needed |
| Key is in PendingDeletion, operator wants to accelerate | Reduce to 7 days | `aws kms schedule-key-deletion --key-id <id> --pending-window-in-days 7` |

**PendingDeletion audit:**
PendingDeletion audit procedure moved verbatim to
[references/diagnostic-commands.md](references/diagnostic-commands.md).

### Step 8: Impact estimation

Compute the monthly savings for each recommendation:

```
current_monthly_cost =
  (customer_managed_keys × $1.00)
  + (api_calls_total / 10000 × $0.03)
  + (multi_region_replicas × $1.00)

projected_monthly_cost = <recalculated with proposed changes>

monthly_saving = current_monthly_cost - projected_monthly_cost
```

Always state assumptions: key count, API call volume, multi-region
replica count, pricing region.

### Step 9: Final verdict

- Any dimension recommends a change → **FURTHER_OPTIMIZATION_AVAILABLE**.
- All dimensions pass AND no waste detected → **ALREADY_OPTIMAL**.
- Change applied and verified this session → **OPTIMIZED**.

Never emit `FURTHER_OPTIMIZATION_AVAILABLE` without first discharging
every data-gate check.

## Output format

Template block moved verbatim to [references/worked-examples.md](references/worked-examples.md) —
the STRICT output contract below is authoritative.

Full worked examples are in `references/worked-examples.md`.

## STRICT output contract

The rules below are hard constraints. Violating any one produces a
misclassification or an arithmetic contradiction that breaks downstream
FinOps automation. Self-check EVERY emitted block against these rules
before returning the response.

### Required output structure

Every response MUST be a single block using these literal labels, in this
order. Do NOT substitute markdown headings, camelCase, or bold variants.

```text
TARGET: <key-id or key-alias>
VERDICT: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
REASON: <1-2 sentences naming the recommendation and the supporting data>
RECOMMENDATION:
  Current: <key/config description>
  Proposed: <key/config description>
  Dimensions changed: <inventory | rotation | grants | aliases | cross_account | multi_region | deletion>
  Dimensions checked: <list ALL seven, each ✓ (no finding) or → (finding)>
  Confidence: <HIGH/MEDIUM/LOW> — <one-line rationale>
ESTIMATED_SAVINGS:
  Current monthly: $<amount>    ← MUST show all subtotals
  Projected monthly: $<amount>
  Monthly saving: $<amount>     ← MUST equal Current − Projected, 2 decimals
  Annual saving: $<amount>      ← MUST equal Monthly × 12
REMEDIATION_STEPS:
  1. <specific action with CLI command>
  2. <verification step>
CONFIRM: <confirmation prompt text>
```

### FORBIDDEN output patterns

1. **NEVER emit `VERDICT: FURTHER_OPTIMIZATION_AVAILABLE` with `Monthly
   saving: $0.00`.** If every dimension nets zero cost delta, the verdict
   MUST be `ALREADY_OPTIMAL`. A cost-neutral security improvement (e.g.,
   enabling rotation) is surfaced in REASON, NOT as a dollar saving.

2. **NEVER show savings math that does not balance.**
   `Current monthly − Projected monthly` MUST equal `Monthly saving`,
   rounded to 2 decimal places.

3. **NEVER emit scratch lines** ("WAIT — recompute", "Hmm, let me redo",
   "corrected:") in the output. Finalize the math before emitting.

4. **NEVER recommend deleting a KMS key without verifying no encrypted
   data depends on it.** KMS key deletion is IRREVERSIBLE. Data encrypted
   under a deleted key is permanently unrecoverable. This is the single
   most dangerous recommendation in this skill.

5. **NEVER recommend consolidating two keys that serve different
   compliance domains.** A PCI-DSS key and a HIPAA key may have identical
   policies but merging them violates compliance isolation requirements.
   Check tags and compliance scope before consolidation.

6. **NEVER omit a dimension from the RECOMMENDATION block.** The
   `Dimensions checked` line MUST list all seven dimensions, each marked
   ✓ (no finding) or → (finding).

7. **NEVER round intermediate formula steps differently from the final
   figure.** Compute at full precision, round only the displayed result.

### Perfect example output — FURTHER_OPTIMIZATION_AVAILABLE with verified math

Every field below is internally consistent. Copy this shape exactly.

```text
TARGET: alias/legacy-app-encryption
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Customer-managed key with 0 Decrypt, Encrypt, or GenerateDataKey
  calls in 30 days (CloudTrail lookup). No S3 bucket default encryption,
  no EBS volume, no RDS instance, no Secrets Manager secret references
  this key. Key has 3 expired grants not retired. Rotation is disabled.
  This is an orphaned key costing $1/month with no active workload.
RECOMMENDATION:
  Current: 1 customer-managed key (Enabled), rotation Disabled,
    3 expired grants, 0 API calls/30 days
  Proposed: 0 keys (scheduled deletion), grants retired, rotation
    enabled before deletion for compliance audit trail
  Dimensions changed: inventory (delete) + grants (retire) + rotation
    (enable for audit trail)
  Dimensions checked: inventory → (delete)  rotation → (enable first)
    grants → (retire 3)  aliases ✓ (alias exists)  cross_account ✓ (none)
    multi_region ✓ (single region)  deletion → (schedule 7-day window)
  Confidence: HIGH — CloudTrail confirms zero API activity for 30 days;
    resource association audit found no encrypted resources; grant
    audit found 3 expired grants on deleted IAM roles.
ESTIMATED_SAVINGS:
  Current monthly: $1.00
    key: 1 × $1.00 = $1.00
    api: 0 calls × $0.03/10K = $0.00
  Projected monthly: $0.00
  Monthly saving: $1.00
    ($1.00 − $0.00 = $1.00 ✓)
  Annual saving: $12.00
REMEDIATION_STEPS:
  1. Retire expired grants:
     aws kms retire-grant --key-id <key-id> --grant-id <grant-1>
     aws kms retire-grant --key-id <key-id> --grant-id <grant-2>
     aws kms retire-grant --key-id <key-id> --grant-id <grant-3>
  2. Enable rotation for audit trail completeness:
     aws kms enable-key-rotation --key-id <key-id>
  3. Verify no encrypted resources depend on this key:
     aws s3api list-buckets --query 'Buckets[?DefaultEncryption'
     aws ec2 describe-volumes --query 'Volumes[?KmsKeyId==`<key-id>`]'
  4. Schedule key deletion (minimum 7-day window):
     aws kms schedule-key-deletion --key-id <key-id> --pending-window-in-days 7
  5. Document deletion in change management system.
CONFIRM: About to retire 3 grants, enable rotation, and schedule
  deletion of alias/legacy-app-encryption (7-day window). Monthly saving
  $1.00 ($12.00/year). Key deletion is IRREVERSIBLE. Proceed? (yes/no)
```


**Self-check before emit:**
- [ ] `Current monthly − Projected monthly == Monthly saving` (2 decimals)?
- [ ] `Monthly saving × 12 == Annual saving`?
- [ ] All seven dimensions listed in `Dimensions checked`?
- [ ] Every `→` dimension has a corresponding REMEDIATION_STEPS entry?
- [ ] No scratch/recompute text in the block?

## Verdict semantics

| Verdict | When to emit |
|---|---|
| `FURTHER_OPTIMIZATION_AVAILABLE` | At least one dimension has a concrete, savings-bearing recommendation. |
| `OPTIMIZED` | A change was applied and verified this session; metrics confirm the new configuration. |
| `ALREADY_OPTIMAL` | All dimensions pass (keys active, rotation enabled, grants clean, no orphaned replicas). |

**Zero-savings rule:** If MONTHLY_SAVING == $0.00 for every dimension,
verdict MUST be `ALREADY_OPTIMAL`, never `FURTHER_OPTIMIZATION_AVAILABLE`.
Exception: enabling rotation is a security improvement surfaced in
REASON, not as a dollar saving.

## Anti-Patterns — NEVER (top 5)

1. **NEVER recommend deleting a KMS key without verifying no encrypted
   data depends on it.** KMS key deletion is irreversible. Data encrypted
   under the key is permanently lost. This is the #1 most dangerous
   recommendation. Check S3, EBS, RDS, Secrets Manager, and Lambda
   encryption configs before any deletion recommendation.

2. **NEVER recommend consolidating keys that serve different compliance
   domains.** A PCI-DSS key and a HIPAA key with identical policies still
   serve different audit scopes. Merging them violates isolation. Check
   resource tags and compliance scope before consolidation.

3. **NEVER recommend disabling rotation on a customer-managed key for
   cost reasons.** Rotation is free. The only reason to disable rotation
   is a regulatory prohibition, which should be documented — not a cost
   decision.

4. **NEVER retire a grant without verifying the grantee principal no
   longer needs access.** Retiring a grant that an active Lambda or
   application depends on will immediately break decryption. Check
   CloudTrail for recent grant usage before retiring.

5. **NEVER assume a key with low API call volume is unused.** Some keys
   encrypt historical data that is rarely accessed (e.g., archived S3
   objects). Deleting the key makes that historical data permanently
   unrecoverable. Verify data access patterns, not just write patterns.

Extended anti-patterns in `references/kms-pricing-and-lifecycle.md`.


## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation,
  emit and await operator approval. Do NOT execute until confirmed.
- **KMS key deletion is IRREVERSIBLE.** Data encrypted under the key is
  permanently unrecoverable. This is the most dangerous operation in
  this skill. Triple-verify no encrypted resources depend on the key.
- **Verify resource associations before deletion.** Check S3 bucket
  encryption, EBS volumes, RDS instances, Secrets Manager secrets,
  Lambda environment variables, and Redshift clusters for references to
  the key.
- **Grant retirement breaks dependent workloads.** Before retiring a
  grant, verify the grantee principal is not actively using the key.
  Check CloudTrail for recent Decrypt/Encrypt events under the grant.
- **Multi-region replica deletion is per-region.** Deleting a replica
  does not affect the primary or other replicas, but data encrypted by
  the replica in that region becomes permanently unrecoverable.
- **Enabling rotation is safe and non-disruptive.** The key ARN does not
  change. No application changes are needed.
- **Alias updates are immediate.** Re-pointing an alias from one key to
  another takes effect instantly. Applications using the alias will
  immediately use the new key.
- **PendingDeletion keys cannot be used.** Once a key enters
  PendingDeletion, Decrypt and Encrypt calls fail. Applications relying
  on the key will break immediately.
- **Bulk-operation limit:** Process at most 5 key deletions per batch.
  Verify each batch before proceeding. Abort if any key is found to
  encrypt active data.


## References

- `references/kms-pricing-and-lifecycle.md` — pricing tables, key types,
  rotation configuration, grant lifecycle, multi-region setup, deletion
  window management, CLI reference, anti-pattern catalog.
- `references/worked-examples.md` — full worked examples (unused key
  deletion, grant cleanup, multi-region replica removal, rotation
  enablement, already-optimal, end-to-end walkthrough).

## References (load on demand)

- [references/kms-pricing-and-lifecycle.md](references/kms-pricing-and-lifecycle.md) — pricing tables, key types, rotation configuration, grant lifecycle, multi-region setup, deletion window management, CLI reference, anti-pattern catalog.
- [references/worked-examples.md](references/worked-examples.md) — full worked examples (unused key deletion, grant cleanup, multi-region replica removal, rotation enablement, already-optimal, end-to-end walkthrough); now also the secondary worked example (rotation enablement + unused replica deletion) and the Output format template moved from SKILL.md.
- [references/advanced-patterns.md](references/advanced-patterns.md) — Mindset framing, configuration dependency graph, Step 0 non-obvious behaviours, expert heuristics, and Recent AWS features moved from SKILL.md.
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — pre-flight data-source CLI list and the Step 1-7 audit/consolidation/cost/deletion procedures moved from SKILL.md.

## Domain

AWS CloudOps / KMS Key Rotation & Lifecycle Cost Optimization & FinOps.

## AWS documentation

- **AWS KMS Developer Guide** — https://docs.aws.amazon.com/kms/latest/developerguide/overview.html
- **KMS pricing** — https://aws.amazon.com/kms/pricing/
- **Rotating KMS keys** — https://docs.aws.amazon.com/kms/latest/developerguide/rotate-keys.html
- **KMS grants** — https://docs.aws.amazon.com/kms/latest/developerguide/grants.html
- **Multi-region keys** — https://docs.aws.amazon.com/kms/latest/developerguide/multi-region-keys-overview.html
- **Deleting KMS keys** — https://docs.aws.amazon.com/kms/latest/developerguide/deleting-keys.html
- **AWS CLI KMS reference** — https://docs.aws.amazon.com/cli/latest/reference/kms/
- **AWS Well-Architected Framework — Cost Optimization** — https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html
