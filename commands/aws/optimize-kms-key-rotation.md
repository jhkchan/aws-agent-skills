---
description: Optimise KMS key rotation and lifecycle cost through key inventory audit (unused key deletion, orphaned key cleanup), rotation strategy (enable automatic annual rotation on customer-managed keys), grant optimization (retire expired grants), alias management for rotation transparency, cross-account grant token lifecycle, multi-region replica cost reduction, and deletion window management with monthly savings estimates.
nl_triggers:
  - "optimise KMS cost"
  - "KMS key inventory audit"
  - "KMS unused keys"
  - "KMS key rotation strategy"
  - "KMS grant cleanup"
  - "KMS stale grants"
  - "KMS cross-account cost"
  - "KMS multi-region keys cost"
  - "KMS key deletion window"
  - "KMS FinOps savings"
  - "reduce KMS bill"
  - "KMS orphaned keys"
  - "KMS API call analysis"
  - "KMS monthly savings estimate"
  - "KMS key lifecycle"
routes_to: kms-key-rotation-optimizer
---

# /aws:optimize-kms-key-rotation

Activate the `kms-key-rotation-optimizer` skill and optimize a KMS key
inventory across seven dimensions: key inventory, rotation configuration,
grant lifecycle, alias management, cross-account usage, multi-region
replicas, and deletion window management.

## What it does

Reads a KMS key's CloudTrail API call history (Decrypt, Encrypt,
GenerateDataKey), key configuration, grant inventory, alias mappings,
and resource associations, then applies the ordered optimization logic:

1. **Pre-flight** — data sufficiency gate. If CloudTrail data is absent
   or window < 14 days, extend the lookup window.
2. **Key inventory audit** — detect keys with 0 API calls in 30 days.
   Verify no encrypted resources depend on the key. Schedule deletion
   for orphaned keys ($1/month each).
3. **Rotation strategy** — enable automatic annual rotation on
   customer-managed keys where disabled. Rotation is free and
   transparent (same key ARN, new backing key).
4. **Grant optimization** — identify expired grants (deleted IAM
   principals, past ExpiryDate). Retire stale grants to reduce key
   policy evaluation latency.
5. **Alias management** — ensure applications reference aliases (not key
   IDs) for rotation transparency. Clean up orphaned aliases pointing at
   deleted keys.
6. **Cross-account usage** — audit cross-account grants. Set ExpiryDate
   on open-ended grants. Evaluate whether per-account AWS managed keys
   are cheaper than shared customer-managed keys.
7. **Multi-region keys** — detect unused replica keys (0 API calls in
   30 days per region). Delete unused replicas ($1/month per region).
8. **Deletion window** — use the 7-day minimum for keys with no
   encrypted data. Use 30 days for keys that may encrypt historical
   data. Audit PendingDeletion keys for billing continuation.
9. **Impact estimation** — monthly + annual savings, assumptions
   documented.
10. **Verdict** — FURTHER_OPTIMIZATION_AVAILABLE (any dimension has a
    recommendation), OPTIMIZED (applied and verified), or
    ALREADY_OPTIMAL.

Emits a deterministic optimization block per key:

```text
TARGET: <key-id or key-alias>
VERDICT: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
REASON: <1-2 sentences naming the recommendation and supporting data>
RECOMMENDATION:
  Current: <key/config description>
  Proposed: <key/config description>
  Dimensions changed: <inventory | rotation | grants | aliases | cross_account | multi_region | deletion>
  Confidence: <HIGH/MEDIUM/LOW> — <rationale>
ESTIMATED_SAVINGS:
  Monthly: $<amount>
  Annual: $<amount>
  Assumptions: <list>
REMEDIATION_STEPS:
  1. <action with CLI command>
  2. <verification step>
```

## When to invoke

Paste a KMS key's configuration and ask any of:

- "optimise this KMS key's cost"
- "is this KMS key still needed?"
- "should I enable key rotation?"
- "should I clean up these KMS grants?"
- "are multi-region replicas worth the cost?"
- "can I delete this orphaned KMS key?"
- "how do I reduce my KMS bill?"
- "KMS key fleet cost optimization review"

A bare key ID or alias + any optimization verb also routes here via the
orchestrator.

## Inputs

- Key metadata: key ID, alias, key state, key manager (AWS/CUSTOMER),
  key spec, region.
- CloudTrail API calls (last 14-30 days):
  - `Decrypt` (count)
  - `Encrypt` (count)
  - `GenerateDataKey` (count)
- Optional: rotation status (enabled/disabled, last rotated date).
- Optional: grant inventory (count, active vs expired, grantee
  principals).
- Optional: multi-region status (primary region, replica regions, per-
  region API call counts).
- Optional: resource associations (S3 buckets, EBS volumes, RDS
  instances, Secrets Manager secrets referencing the key).
- Optional: Cost Explorer KMS cost breakdown.

## Outputs

- One optimization block per key.
- Confidence level with rationale.
- Estimated monthly and annual savings, broken down by dimension.
- Specific remediation steps with CLI commands (retire-grant,
  enable-key-rotation, schedule-key-deletion, cancel-key-deletion).
- Seven-dimension check (inventory, rotation, grants, aliases,
  cross-account, multi-region, deletion).
- IRREVERSIBLE deletion warning for any key deletion recommendation.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 3 Optimize specialist for KMS key lifecycle cost).
- `/aws:audit-kms-key-policy` for KMS key policy security auditing (not
  cost optimization).
- `/aws:deploy-kms-key` for KMS key deployment.
- `/aws:operate-kms-key-rotation` for operational rotation execution.
