---
description: Operate CloudFront cache invalidation — create-invalidation with path patterns (/* all, /images/* wildcard, single-path), invalidation cost tiering (1-1000 paths free then $0.005/path), cache-busting strategy (invalidation vs versioned filenames), wait for InvalidationStatus Completed, continuous deployment staging invalidation, and post-verify with X-Cache spot-check.
nl_triggers:
  - "invalidate CloudFront cache"
  - "CloudFront invalidation"
  - "create-invalidation"
  - "clear CDN cache"
  - "CloudFront edge cache"
  - "cache busting"
  - "versioned filenames"
  - "invalidation cost"
  - "invalidate /*"
  - "bulk invalidation"
  - "CloudFront continuous deployment invalidation"
  - "staging distribution invalidation"
  - "InvalidationStatus InProgress"
  - "CloudFront stale cache"
  - "invalidate specific paths CloudFront"
routes_to: cloudfront-invalidation-operator
---

# /aws:operate-cloudfront-invalidation

Activate the `cloudfront-invalidation-operator` skill and plan/execute
a CloudFront cache invalidation operation with deterministic
pre-checks, CONFIRM gate, and post-verification.

## What it does

Reads a distribution configuration plus the intended operation and
applies the priority-ordered pre-check sequence:

1. Pre-flight distribution metadata gate — Deployed status, Enabled
   flag, continuous deployment policy detection.
2. Pre-check gate — BLOCKED if any check fails (distribution not
   Deployed, caller lacks `cloudfront:CreateInvalidation`, path
   pattern syntax invalid, CallerReference collision, concurrent
   invalidation limit exceeded).
3. READY — emit the exact CLI sequence with all flags populated, cost
   analysis (1,000-path free tier then $0.005/path), cache-busting
   strategy comparison, and the CONFIRM gate prompt.
4. Execute behind CONFIRM gate — capture pre-state for rollback,
   execute `create-invalidation`, poll `get-invalidation` until
   `InvalidationStatus: Completed`.
5. Post-verification — `get-invalidation` shows Completed,
   `list-invalidations` confirms, `curl -I` spot-check shows
   `X-Cache: Miss from CloudFront`, cost verified; COMPLETED only if
   ALL post-verification checks pass.

Emits a deterministic VERDICT per operation:

```text
OPERATION: <create-invalidation | wait-invalidation | cost-analysis | compare-strategy | diagnose-invalidation>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <distribution-id> (domain: <domain-name>)
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. <CLI command with flags populated>
  2. <wait/poll command>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
COST: <free tier | $X.XX for N paths beyond free tier>
NOTES: <cache-busting recommendation, monitoring, caveats>
```

## When to invoke

Paste a distribution configuration plus the intended operation, or
just describe the scenario and ask any of:

- "invalidate /* on E1ABC2DEF3GHI4"
- "clear the CloudFront cache"
- "how much will this invalidation cost?"
- "should I invalidate or use versioned filenames?"
- "my invalidation is stuck InProgress"
- "invalidate the staging distribution"

A bare distribution ID + any invalidation verb ("clear cache on
E1ABC2DEF3GHI4", "invalidate these paths") also routes here via the
orchestrator.

## Inputs

- Distribution configuration (`get-distribution`,
  `list-invalidations` JSON).
- The intended operation: `create-invalidation`,
  `wait-invalidation`, `cost-analysis`, `compare-strategy`,
  `diagnose-invalidation`.
- For create-invalidation: the path patterns (`/*`, `/images/*`,
  `/index.html`, or a list of individual paths) and a unique
  CallerReference.
- For continuous deployment: the `ContinuousDeploymentPolicyId` and
  staging distribution ID.

## Outputs

- One VERDICT block per operation.
- PRE_CHECKS list with `[PASS]` / `[FAIL]` per check and reason for
  failure.
- For READY: the exact CLI sequence, expected timeline, estimated
  cost, cache-busting strategy recommendation, and the CONFIRM gate
  prompt.
- For COMPLETED: POST_VERIFY list with `[PASS]` per check, the
  observed invalidation status, X-Cache spot-check result, and cost
  summary.
- For BLOCKED: the specific failure reason (distribution not Deployed,
  IAM permission missing, path syntax invalid, CallerReference
  collision) and the alternative path.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 4 Operate specialist for CloudFront cache invalidation).
- `/aws:deploy-cloudfront-distribution` for provisioning and updating
  CloudFront distributions, including continuous deployment policies.
- `/aws:audit-cloudfront-distribution` for auditing distribution
  security posture, origin access control, and cache policy
  configuration.
