---
name: cloudfront-invalidation-operator
description: 'Operates CloudFront cache invalidation workflows — invalidation creation with path patterns (/* all, /images/* directory, /images/*.css wildcard, single-path), invalidation cost tiering (first 1,000 paths/month free then $0.005 per path), cache-busting strategy (invalidation vs versioned filenames), invalidation status polling (InvalidationStatus: InProgress→Completed), bulk invalidation patterns, continuous deployment staging invalidation, and diagnostic loops (get-invalidation, list-invalidations). Runs deterministic pre-checks (distribution Deployed, caller has cloudfront:CreateInvalidation, path count under free tier, path syntax valid) behind a CONFIRM gate and emits a READY, BLOCKED, or COMPLETED verdict. Use when creating invalidations, waiting for completion, choosing invalidation vs cache-busting, or diagnosing invalidation cost.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline plan classification. Live-account operations use aws cloudfront create-invalidation, get-invalidation, list-invalidations, get-distribution, list-distributions, get-distribution-config (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: 'true'
  phase: '4'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Networking
  task_type: operate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY | BLOCKED | COMPLETED
  when_to_use: Creating a CloudFront cache invalidation (/* all, /images/* directory, /images/*.css wildcard, or single-object path), waiting for an invalidation to reach Completed status, deciding whether to invalidate or use versioned filenames for cache-busting, planning a bulk invalidation that exceeds the 1,000-path free tier, invalidating a staging distribution in a continuous deployment workflow, or diagnosing why an invalidation is stuck InProgress or costs more than expected.
  activation_triggers: invalidate CloudFront cache, CloudFront invalidation, create-invalidation, get-invalidation, InvalidationStatus, InProgress invalidation, cache busting, versioned filenames, CloudFront continuous deployment, staging distribution invalidation, invalidate /*, bulk invalidation, CloudFront edge cache, clear CDN cache, invalidation cost
  invocation_schema: 'Input: either (a) a CloudFront distribution configuration (get-distribution output) plus the intended operation (create-invalidation, wait-invalidation, cost-analysis, compare-strategy, diagnose-invalidation), OR (b) a distribution-id + operation for live-account execution. Output: deterministic OPERATION / VERDICT / PRE_CHECKS / STEPS / POST_VERIFY / NOTES block per invalidation, where VERDICT is one of READY, BLOCKED, COMPLETED.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: CloudFront, invalidation, cache busting, edge cache, CDN, path pattern, wildcard invalidation, CreateInvalidation, GetInvalidation, InvalidationStatus, continuous deployment, staging distribution, cache policy, versioned filenames, origin, distribution, InProgress, Completed
  tags: aws, cloudfront, networking, cdn, cache, invalidation, operate
---

# CloudFront Invalidation Operator

## What this skill does

Executes CloudFront cache invalidation operations correctly and
cost-effectively. Runs deterministic pre-checks before any
state-changing CLI (distribution is Deployed, caller has
`cloudfront:CreateInvalidation` permission, path patterns are
syntactically valid, path count is under the free-tier threshold or
cost is acknowledged), executes the `create-invalidation` CLI behind
a CONFIRM gate, and verifies the result by polling
`get-invalidation` until `InvalidationStatus: Completed`. Every
invalidation produces a cost note (1-1000 paths free per month, then
$0.005/path) and a cache-busting strategy comparison (invalidation vs
versioned filenames). Continuous deployment distributions route to
the staging distribution for invalidation before promotion.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **§ Quick reference** | Verdict thresholds (BLOCKED/READY/COMPLETED) + pre-check priority | Before any operation |
| **§ Mindset** | Why invalidation is a blunt tool, the free-tier trap, the cache-busting hierarchy | Understanding the cost model |
| **§ Pre-flight** | Distribution metadata gate — Deployed state, caller IAM, path syntax | Before executing any CLI |
| **§ Process** | Per-operation planning: create, wait, cost-analysis, compare-strategy, diagnose | When choosing which operation to run |
| **§ Output format** | STRICT output contract — OPERATION/VERDICT/PRE_CHECKS/STEPS/POST_VERIFY template | Formatting the response |
| **§ Anti-Patterns** | NEVER list — top mistakes that waste money or leave stale cache | Review before risky operations |
| **§ Pre-flight safety** | Capture pre-state, distribution config verification, cost capture | Defense-in-depth |

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `BLOCKED` | One or more pre-checks failed (distribution not Deployed, caller lacks `cloudfront:CreateInvalidation`, path pattern syntax invalid, continuous deployment primary without staging awareness) | List failures, do NOT execute |
| `READY` | All pre-checks passed; awaiting CONFIRM gate | Emit exact CLI sequence, wait for operator yes |
| `COMPLETED` | Invalidation created and `InvalidationStatus: Completed` confirmed via `get-invalidation` | Emit verification results, cost summary, monitoring plan |

**Priority order for pre-checks (apply in this sequence, all must pass
for READY):**

1. **Distribution reachability** — distribution exists
   (`get-distribution` does not return `NoSuchResource`), and the
   distribution ID is valid.
2. **Distribution is Deployed** — `Status: Deployed` (not
   `InProgress`, `Deleting`, or `Suspended`). Invalidation on a
   non-Deployed distribution may fail or have no effect.
3. **Path pattern syntax** — each path starts with `/`, uses
   ASCII-safe characters, and wildcard `*` appears only at the end
   of a path segment (e.g. `/images/*.jpg` is valid;
   `/images/*/header.jpg` is NOT valid).
4. **Path count vs free tier** — the first 1,000 invalidation paths
   per month are free; paths beyond 1,000 cost $0.005 each. If the
   path count exceeds 1,000, surface a cost warning in the plan.
5. **Caller IAM permission** — the calling identity must have
   `cloudfront:CreateInvalidation` on the distribution ARN. Without
   it, `create-invalidation` returns `AccessDenied`.
6. **Continuous deployment awareness** — if the distribution has a
   `ContinuousDeploymentPolicyId`, invalidations should target the
   STAGING distribution for testing before promotion to the primary.
7. **CallerRef uniqueness** — `CallerReference` must be unique per
   invalidation. Reusing a CallerReference silently deduplicates
   (returns the existing invalidation without creating a new one).

**Cost/time baselines (2026):**

- First 1,000 invalidation paths per month: free (across all
  distributions in the account).
- Paths 1,001+: $0.005 per path per month.
- A single `/*` invalidation counts as ONE path (covers all objects).
- A `/images/*` invalidation also counts as ONE path.
- Listing each object individually (`/index.html`, `/style.css`,
  `/logo.png`) counts as one path EACH — 3 paths for 3 objects.
- Invalidation propagation: typically 10-120 seconds for global
  edge locations. CloudFront does not publish a strict SLA for
  invalidation completion.
- `InvalidationStatus: InProgress` → `Completed` transition: usually
  under 60 seconds for small path counts, up to 10+ minutes for
  large wildcard invalidations.

## Mindset

**One-line takeaway:** CloudFront invalidation is a blunt instrument
— `/*` clears everything in one free path, but listing individual
objects burns through the 1,000-path free tier and costs $0.005 per
extra path. Driven by three CloudFront realities:

- **Versioned filenames beat invalidation for routine deploys.** If
  your CI/CD pipeline renames assets on every build (`app.abc123.js`
  instead of `app.js`), the new file is fetched on first request with
  no invalidation needed. Invalidation is for emergency content
  removal, hotfixes to unversioned assets, or removing sensitive data
  already cached at the edge. Always prefer versioned filenames for
  routine releases.

- **`/*` is the most cost-effective invalidation.** A single `/*`
  invalidation counts as ONE path (free tier) and invalidates every
  object in the distribution. Listing 500 individual paths consumes
  500 of your 1,000 free paths. If you need to invalidate more than
  ~60% of your site, `/*` is cheaper than per-path invalidation.

- **Continuous deployment changes the invalidation target.** With a
  CloudFront continuous deployment policy, traffic is split between
  the primary and staging distributions. Invalidation on the primary
  does NOT invalidate the staging distribution's edge cache. You must
  invalidate both (or invalidate staging first, then promote).

## Pre-flight: distribution metadata gate

Run before classification. Misclassifying these produces wrong plans.

**Pagination:** `list-distributions` paginates at 200/page — drain
`--marker`/`--next-marker` to completion. `list-invalidations`
paginates at 100/page.

**Live-account pre-flight (skip if offline plan audit):**
1. `aws cloudfront get-distribution --id <id>` — capture `Status`,
   `DomainName`, `LastModifiedTime`, `DistributionConfig.Enabled`,
   `DistributionConfig.Origins`, `ContinuousDeploymentPolicyId`
   (if present).
2. `aws cloudfront list-invalidations --distribution-id <id>
   --max-items 20` — capture recent invalidation history, including
   `Status`, `CreateTime`, `InvalidationBatch.Paths.Quantity`.
3. For continuous deployment: `aws cloudfront
   get-continuous-deployment-policy --id <policy-id>` — capture
   `StagingDistributionDnsName`, traffic percentage, and type
   (`TrafficConfig`).
4. For cost analysis: count the total paths invalidated this month
   across all distributions (`list-invalidations` per distribution,
   sum `Paths.Quantity`, subtract 1,000).

**Malformed input:** if the input is invalid or missing required
fields, emit `VERDICT: ERROR` with `REASON: Distribution
configuration is not valid or is missing required fields — cannot
plan.` and `REMEDIATION: Re-fetch with aws cloudfront get-distribution
--id <id> --output json and re-plan.`

| Distribution attribute | Effect on operation |
|---|---|
| `Status: InProgress` | BLOCKED — distribution update in flight. Wait for `Deployed`. |
| `Status: Deployed` | OK — distribution is live, invalidation can proceed. |
| `Status: Suspended` | BLOCKED — distribution is suspended. Restore via `update-distribution` with `Enabled: true`. |
| `Status: Deleting` | BLOCKED — distribution being deleted. No invalidation possible. |
| `Enabled: false` | BLOCKED — distribution disabled. Invalidation may fail or have no effect. |
| `ContinuousDeploymentPolicyId` present | INFO — continuous deployment active. Invalidation should target staging first, then primary on promotion. |
| Path count > 1,000 (monthly cumulative) | ADVISORY — paths beyond 1,000 cost $0.005 each. Surface cost in the plan. |
| Path contains `*` mid-segment | BLOCKED — wildcard only valid at end of a path segment. |
| `CallerReference` collides with existing | BLOCKED — CallerReference must be unique. Generate a new one. |

## Process — operation planning (apply in order)

### Step 0: Expert heuristic — non-obvious CloudFront behaviors

These behaviors are easy to misjudge without operational invalidation
experience. Each changes a plan if ignored:

- **`/*` counts as ONE path, not N paths.** The single most
  misunderstood invalidation cost fact. `/*` invalidates every object
  in the distribution but the billing system counts it as one path.
  This is always cheaper than listing more than one individual object
  path — and it is free for the first 1,000 `/*` invalidations per
  month.

- **Versioned filenames eliminate the need for invalidation.** If
  your build process appends a hash to asset names
  (`main.a1b2c3.js`), the new version is a different URL. CloudFront
  fetches it from the origin on first request. No invalidation
  needed. This is the AWS-recommended cache-busting strategy for
  routine deploys. Reserve invalidation for emergencies, hotfixes to
  unversioned HTML, or removal of sensitive content.

- **`CallerReference` is a deduplication key, not a description.**
  CloudFront uses `CallerReference` to ensure idempotency. If you
  reuse a CallerReference, CloudFront returns the PREVIOUS
  invalidation (if it exists) without creating a new one. This is a
  silent failure — the invalidation appears to succeed but does
  nothing new. Always use a unique value (UUID or timestamp).

- **Wildcard `*` matches only within a single path segment.**
  `/images/*.jpg` matches `/images/photo.jpg` but NOT
  `/images/thumbnails/photo.jpg`. There is no recursive wildcard.
  To invalidate a directory tree, use `/images/*` (matches
  everything under `/images/`).

- **Invalidation does NOT purge the browser cache.** CloudFront
  invalidation clears edge cache. End-user browsers still have their
  local cache. To force browser refresh, use versioned filenames or
  short `Cache-Control: max-age` values. Invalidation + long
  browser cache TTLs = stale content for users.

- **Continuous deployment requires invalidating BOTH distributions.**
  With a continuous deployment policy, traffic is split between
  primary and staging. An invalidation on the primary does not
  affect staging's edge cache (and vice versa). When testing a
  deployment, invalidate staging first; when promoting, invalidate
  the primary.

- **Invalidation does not roll back the origin.** If you deployed a
  broken build and invalidate `/*`, CloudFront will re-fetch the
  broken content from the origin. You must fix the origin (redeploy,
  rollback) BEFORE or SIMULTANEOUSLY with the invalidation. The
  invalidation only clears the cache — it does not change what the
  origin serves.

- **`list-invalidations` does not show per-edge-location status.**
  The `InvalidationStatus` is a global aggregate. `Completed` means
  all edge locations have processed the invalidation. There is no
  per-region or per-edge status. For debugging "some users still see
  old content," check browser cache, DNS TTL, and origin health —
  not per-edge invalidation status.

- **Multipart invalidation batches have a 3,000-path hard limit per
  request.** `create-invalidation` accepts up to 3,000 paths per API
  call (including wildcards). For more than 3,000 paths, use
  multiple `create-invalidation` calls, or replace with a single
  `/*` invalidation.

- **Lambda@Edge and CloudFront Functions are not invalidated.**
  Function code updates propagate independently of cache
  invalidation. If you updated a Lambda@Edge function, the function
  update can take up to 5 minutes (CloudFront Functions) or up to
  15 minutes (Lambda@Edge) to propagate to all edge locations.
  Invalidation does not speed this up.

- **S3 origin vs custom origin invalidation behavior is identical.**
  The origin type does not affect invalidation. CloudFront tracks
  cached objects by URL regardless of origin type. The invalidation
  path pattern matches the URL path as seen by the viewer.

### Step 1: Pre-check gate — BLOCKED if any check fails

Run ALL pre-checks for the chosen operation. If ANY fails, the verdict
is BLOCKED with the failed checks in PRE_CHECKS. Do NOT execute.

**For ALL operations:**
1. Distribution exists (`get-distribution` does not return
   `NoSuchResource`).
2. Distribution `Status: Deployed`.
3. `DistributionConfig.Enabled: true`.

**For create-invalidation:**
4. Path patterns are syntactically valid (start with `/`, wildcard
   only at segment end, no more than 3,000 paths per batch).
5. Calling identity has `cloudfront:CreateInvalidation` on the
   distribution ARN.
6. `CallerReference` is unique (not in recent `list-invalidations`).
7. (Advisory) Path count + monthly cumulative > 1,000: surface cost
   warning.

**For wait-invalidation (read-only):**
4. `get-invalidation --id <id>` returns a valid invalidation with
   `InvalidationStatus`.
5. (Advisory) If `InvalidationStatus: InProgress` for > 15 minutes,
   surface a warning (typically completes in under 5 minutes).

**For cost-analysis (read-only):**
4. `list-invalidations` for all distributions this month — sum
   `Paths.Quantity` across all invalidations.
5. Compare cumulative path count vs the 1,000-path free tier.

**For compare-strategy (read-only):**
4. Analyze the deployment workflow: are assets versioned? Is the
   origin S3 or custom? What is the typical change frequency?
5. Recommend invalidation vs versioned filenames based on workflow.

**For diagnose-invalidation (read-only):**
4. Read `get-invalidation`, `list-invalidations`, distribution config,
   and the failure-mode table to identify why an invalidation is
   stuck, not working, or unexpectedly expensive.

**Invalidation failure-mode table (use during diagnose-invalidation):**

| Symptom | Root cause | Fix |
|---|---|---|
| `create-invalidation` returns `AccessDenied` | Caller lacks `cloudfront:CreateInvalidation` on the distribution ARN | Add the permission to the caller's IAM policy |
| `create-invalidation` returns `InvalidArgument: Your request has a path that contains an invalid character` | Path contains characters not allowed (spaces, `?`, `#`, or wildcard mid-segment) | Fix the path syntax: start with `/`, URL-encode special chars, wildcard only at segment end |
| `create-invalidation` returns `TooManyInvalidationsInProgress` | More than 15 concurrent InProgress invalidations for the distribution | Wait for existing invalidations to Complete, or consolidate into fewer batches with wildcards |
| `create-invalidation` returns `CNAMEAlreadyExists` | Unrelated to invalidation — distribution config conflict | This is a distribution-update error, not an invalidation error |
| Invalid path count exceeds 3,000 | Hard limit per API call | Split into multiple `create-invalidation` calls, or use `/*` |
| `InvalidationStatus: InProgress` for > 15 minutes | Large wildcard invalidation or edge propagation delay | Wait; if > 30 minutes, check CloudFront service health |
| Invalidation Completed but users still see old content | Browser cache, DNS TTL, or CDN in front of CloudFront | Check `Cache-Control` headers, DNS resolution, intermediate CDN caches |
| Invalidation returns existing invalidation (no new one created) | `CallerReference` collision with a previous invalidation | Generate a new unique `CallerReference` (UUID or timestamp) |
| `create-invalidation` on staging distribution fails | Staging distribution ID is different from the primary; caller may lack permissions on the staging distribution | Use the staging distribution ID from `get-continuous-deployment-policy`; ensure IAM policy covers both |
| Cost is higher than expected | Individual paths counted instead of wildcards; monthly cumulative exceeds 1,000 | Use `/*` or directory wildcards; monitor monthly path count |

### Step 2: READY — emit operation plan

If all pre-checks pass, emit `VERDICT: READY` with the exact CLI
sequence and the CONFIRM gate. The plan includes:

- The exact AWS CLI command with all flags populated from the
  distribution configuration.
- The expected path count and cost (free tier or $0.005/path beyond
  1,000).
- The `CallerReference` value (unique per invalidation).
- The expected side-effects (edge cache cleared for matching paths,
  next request fetches fresh content from origin).
- The CONFIRM gate prompt.
- The verification step (`get-invalidation` polling until Completed).

### Step 3: Execute behind CONFIRM gate

- **MANDATORY CONFIRMATION GATE.** Before any state-changing CLI
  (`create-invalidation`), emit:
  `CONFIRM: About to create a CloudFront invalidation on distribution
  <id> (domain <domain>). Paths: <path-list-or-pattern>. Estimated
  cost: <$X or "free tier">. This will clear edge cache for matching
  paths. Proceed? (yes/no)`. Do NOT execute until the operator
  confirms.
- Capture pre-state for audit: `aws cloudfront list-invalidations
  --distribution-id <id> --max-items 5 --output json >
  /tmp/<id>-invalidations-pre-$(date +%s).json`.
- Execute the CLI. `create-invalidation` returns immediately with an
  `Invalidation` object containing the `Id` and
  `InvalidationStatus: InProgress`.
- For continuous deployment: execute on the STAGING distribution
  first (if testing), then the PRIMARY distribution after promotion.

### Step 4: Post-verification — COMPLETED

After the CLI completes, run post-verification. ALL checks must pass
for `COMPLETED`.

1. `get-invalidation --distribution-id <id> --id <invalidation-id>`
   — confirm `InvalidationStatus: Completed`.
2. `list-invalidations --distribution-id <id>` — confirm the new
   invalidation appears in the list with `Completed` status.
3. Spot-check: `curl -I https://<domain>/<path>` — confirm
   `X-Cache: RefreshHit from CloudFront` (re-fetched from origin) or
   `X-Cache: Miss from CloudFront` (first fetch after invalidation).
4. (Continuous deployment) Confirm the staging distribution
   invalidation (if applicable) is also Completed.
5. Cost verification: confirm the path count billed matches the plan
   (first 1,000 free, $0.005/path beyond).

If ANY verification fails, emit `VERDICT: ERROR` with the failure
details — do not claim COMPLETED.

## Output format (STRICT output contract — per operation)

```text
OPERATION: <create-invalidation | wait-invalidation | cost-analysis | compare-strategy | diagnose-invalidation>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <distribution-id> (domain: <domain-name>, account <account>)
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. <CLI command with flags populated>
  2. <wait / monitoring command>
  3. <next step>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
COST: <free tier | $X.XX for N paths beyond free tier>
NOTES: <cache-busting recommendation, monitoring, caveats>
```

### Worked example — create-invalidation /* (all paths)

```text
OPERATION: create-invalidation
VERDICT: READY
TARGET: E1ABC2DEF3GHI4 (domain: d111111abcdef8.cloudfront.net,
        account 111111111111)
PRE_CHECKS:
  - [PASS] Distribution exists
  - [PASS] Status: Deployed
  - [PASS] Enabled: true
  - [PASS] Path pattern: /* (valid — single wildcard path)
  - [PASS] Calling role has cloudfront:CreateInvalidation on
    arn:aws:cloudfront::111111111111:distribution/E1ABC2DEF3GHI4
  - [PASS] CallerReference: inv-20260810-001 (unique)
  - [INFO] Path count: 1 (free tier — 1 of 1,000 monthly paths used)
STEPS:
  1. CONFIRM: About to create a CloudFront invalidation on
     distribution E1ABC2DEF3GHI4 (d111111abcdef8.cloudfront.net).
     Paths: /* (all objects). Cost: free tier. This will clear edge
     cache for ALL objects globally. Next requests will fetch from
     origin. Proceed? (yes/no)
  2. aws cloudfront create-invalidation \
       --distribution-id E1ABC2DEF3GHI4 \
       --invalidation-batch '{"CallerReference":"inv-20260810-001",
         "Paths":{"Quantity":1,"Items":["/*"]}}'
  3. Capture the Invalidation Id from the response.
  4. Poll until Completed:
     aws cloudfront get-invalidation \
       --distribution-id E1ABC2DEF3GHI4 \
       --id <invalidation-id>
POST_VERIFY:
  - (pending execution)
COST: Free tier (1 path of 1,000 monthly)
NOTES:
  - /* invalidation counts as 1 path regardless of how many objects
    the distribution serves. This is the most cost-effective way to
    clear all edge cache.
  - Propagation typically completes in 30-120 seconds globally.
  - Consider versioned filenames (app.<hash>.js) for routine deploys
    to avoid invalidation entirely.
```

### Worked example — create-invalidation specific paths (cost advisory)

```text
OPERATION: create-invalidation
VERDICT: READY
TARGET: E1ABC2DEF3GHI4 (domain: d111111abcdef8.cloudfront.net,
        account 111111111111)
PRE_CHECKS:
  - [PASS] Distribution exists, Status: Deployed
  - [PASS] Calling role has cloudfront:CreateInvalidation
  - [PASS] CallerReference: inv-20260810-002 (unique)
  - [WARN] Path count: 1,247 individual paths. Monthly cumulative:
    1,247 (247 paths beyond the 1,000 free-tier limit).
  - [WARN] Estimated cost: $0.005 x 247 = $1.24
  - [INFO] Consider replacing with /* (1 path, free) or
    /images/* + /css/* + /js/* (3 paths, free) if the majority of
    paths share common directory prefixes.
STEPS:
  1. CONFIRM: About to create a CloudFront invalidation on
     distribution E1ABC2DEF3GHI4 with 1,247 paths. Estimated cost:
     $1.24 (247 paths at $0.005 each beyond the free tier).
     Proceed? (yes/no)
  2. aws cloudfront create-invalidation \
       --distribution-id E1ABC2DEF3GHI4 \
       --invalidation-batch file://invalidation-batch.json
POST_VERIFY:
  - (pending execution)
COST: $1.24 (247 paths beyond free tier at $0.005/path)
NOTES:
  - Replacing the 1,247 individual paths with /* would cost $0.00
    (1 path, free tier). Consider this if all paths need clearing.
  - Replacing with /images/* + /css/* + /js/* (3 wildcard paths)
    would also be free. Consider if only these directories changed.
```

### Worked example — wait-invalidation (COMPLETED)

```text
OPERATION: wait-invalidation
VERDICT: COMPLETED
TARGET: E1ABC2DEF3GHI4 (domain: d111111abcdef8.cloudfront.net)
PRE_CHECKS:
  - [PASS] Invalidation I2XYZ5678UVW90 exists
  - [PASS] InvalidationStatus: Completed
POST_VERIFY:
  - [PASS] InvalidationStatus: Completed (confirmed via
    get-invalidation)
  - [PASS] Invalidation appears in list-invalidations with Completed
  - [PASS] Spot-check: curl -I returns X-Cache: Miss from CloudFront
    (content re-fetched from origin)
COST: N/A (no new invalidation created)
NOTES:
  - Invalidation I2XYZ5678UVW90 completed in 47 seconds.
  - All edge locations have purged the specified paths.
  - Next viewer requests for these paths will fetch fresh content
    from the origin.
```

### Worked example — continuous deployment staging invalidation

```text
OPERATION: create-invalidation
VERDICT: READY
TARGET: E1ABC2DEF3GHI4 (primary) + E5STAGING123 (staging, via
        continuous deployment policy CDP1XYZ)
PRE_CHECKS:
  - [PASS] Primary distribution exists, Status: Deployed
  - [PASS] ContinuousDeploymentPolicyId: CDP1XYZ (active)
  - [PASS] Staging distribution E5STAGING123 identified
  - [PASS] Calling role has cloudfront:CreateInvalidation on BOTH
    distribution ARNs
  - [PASS] Path pattern: /api/v2/* (valid wildcard)
  - [INFO] Plan: invalidate STAGING first, verify, then promote.
    After promotion, invalidate PRIMARY if needed.
STEPS:
  1. CONFIRM: About to create an invalidation on the STAGING
     distribution E5STAGING123 for /api/v2/*. This is a continuous
     deployment test. Proceed? (yes/no)
  2. aws cloudfront create-invalidation \
       --distribution-id E5STAGING123 \
       --invalidation-batch '{"CallerReference":"stg-20260810-001",
         "Paths":{"Quantity":1,"Items":["/api/v2/*"]}}'
  3. Verify staging serves fresh content via the staging DNS:
     curl -I https://<staging-dns>.cloudfront.net/api/v2/health
  4. If staging is correct, promote (update-distribution with the
     continuous deployment policy). Primary will serve the new
     content after promotion.
POST_VERIFY:
  - (pending execution)
COST: Free tier (1 path on staging, 1,000 monthly budget)
NOTES:
  - Continuous deployment staging invalidation is independent from
    the primary distribution's edge cache.
  - After promotion, the primary may need its own invalidation if
    the traffic shift causes cache misses.
  - Do NOT invalidate the primary before promoting — the primary
    still serves the old (stable) version until promotion.
```

## Anti-Patterns — NEVER (top mistakes)

- NEVER list individual object paths when a wildcard (`/*` or
  `/images/*`) covers the same set. Each individual path counts
  against the 1,000-path free tier; a wildcard counts as ONE path.
  500 individual paths = 500 free-tier paths consumed; `/*` = 1
  free-tier path for the same effect.

- NEVER reuse a `CallerReference` across invalidations. CloudFront
  treats CallerReference as a deduplication key — a reused value
  silently returns the old invalidation without creating a new one.
  This is the most common cause of "I invalidated but nothing
  happened." Always use a UUID or timestamp.

- NEVER rely on invalidation as your primary cache-busting strategy
  for routine deploys. Use versioned filenames (`app.<hash>.js`) so
  new deploys are new URLs that CloudFront fetches automatically.
  Invalidation is for emergencies, hotfixes to unversioned assets,
  and sensitive-data removal. Routine invalidation burns the free
  tier and costs $0.005/path beyond 1,000.

- NEVER invalidate a distribution whose origin still serves the old
  (broken) content. Invalidation clears the edge cache, but the next
  request re-fetches from the origin. If the origin has not been
  fixed (redeployed, rolled back), the invalidation re-caches the
  broken content. Fix the origin first, then invalidate.

- NEVER forget to invalidate the staging distribution in a continuous
  deployment workflow. The primary and staging distributions have
  independent edge caches. Invalidating the primary does NOT clear
  the staging cache. If you test on staging and it serves stale
  content, the staging distribution needs its own invalidation.

- NEVER assume `InvalidationStatus: Completed` means all users see
  fresh content immediately. Completed means CloudFront edge caches
  are cleared. End-user browser caches, intermediate CDN caches, and
  DNS resolvers may still serve old content. Use short
  `Cache-Control` headers or versioned filenames to address browser
  cache staleness.

- NEVER use mid-segment wildcards (`/images/*/photo.jpg`). CloudFront
  only supports wildcard `*` at the END of a path segment. Use
  `/images/*` to match the entire directory tree, or list individual
  paths.

- NEVER exceed 15 concurrent InProgress invalidations per
  distribution. CloudFront returns `TooManyInvalidationsInProgress`.
  Consolidate into fewer wildcard-based batches, or wait for
  existing invalidations to complete.

- NEVER use invalidation to manage cache behavior for dynamic API
  responses. API responses should use `Cache-Control: no-cache` or
  short TTLs in the cache policy. Invalidation is for static assets,
  not for clearing dynamic content that changes on every request.

- NEVER create an invalidation without first checking the monthly
  cumulative path count. If you have already used 950 of your 1,000
  free paths, a 200-path invalidation costs $0.75 (150 paths at
  $0.005). Track cumulative usage via `list-invalidations` across
  all distributions.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any `create-invalidation`
  call, emit: `CONFIRM: About to create a CloudFront invalidation on
  distribution <id> (domain <domain>). Paths: <pattern>. Estimated
  cost: <$X or "free tier">. Proceed? (yes/no)`. Do NOT execute until
  the operator confirms.

- **Capture pre-state for audit.** Before any invalidation:
  `aws cloudfront list-invalidations --distribution-id <id>
  --max-items 10 --output json > /tmp/<id>-inv-pre-$(date +%s).json`.

- **Verify distribution status.** `get-distribution --id <id>` —
  confirm `Status: Deployed` and `Enabled: true`. An invalidation on
  a Suspended or InProgress distribution may silently fail.

- **Verify origin health before invalidation.** If the origin is S3,
  verify the S3 bucket has the updated content. If the origin is a
  custom HTTP server, verify the server serves the correct response.
  Invalidating against a broken origin re-caches broken content.

- **Verify CallerReference uniqueness.** Check the last 20
  invalidations via `list-invalidations` to ensure the CallerReference
  has not been used before.

- **Prefer additive changes over destructive ones.** Versioned
  filenames (additive) are always safer than invalidation
  (destructive — clears cache). Only invalidate when versioned
  filenames are not possible (unversioned HTML, sensitive data
  removal, emergency content changes).

## Recent AWS features (2024-2026)

- **CloudFront continuous deployment (2022 GA, 2024-2026 hardening):**
  Traffic-splitting between a primary and staging distribution.
  Invalidation on the primary does NOT affect staging. Staging has
  its own distribution ID and edge cache. Test changes on staging,
  then promote to primary via `update-distribution`.

- **CloudFront KeyValueStore (2024):** Edge key-value store for
  CloudFront Functions. Updates to KeyValueStore propagate
  independently of cache invalidation. Do not use invalidation to
  force KeyValueStore updates — use `update-key-value-store` directly.

- **CloudFront response headers policies (2024-2025):** Managed
  response headers policies now include `Cache-Control` overrides.
  These are applied at the edge independently of origin headers.
  Verify the response headers policy before assuming the origin's
  `Cache-Control` is being respected.

- **CloudFront origin access control (OAC, 2023-2024):** Replaces
  origin access identity (OAI). Does not affect invalidation
  behavior — invalidation operates on edge cache, not origin access.

- **CloudFront Metrics (2025):** Enhanced real-time metrics now
  include per-status-code cache hit/miss rates. Use these to verify
  that an invalidation had the expected effect (cache miss rate
  spikes after invalidation, then normalizes as the new content is
  cached).

- **CloudFront Functions vs Lambda@Edge propagation (2024-2026):**
  CloudFront Functions updates propagate in ~5 minutes; Lambda@Edge
  updates propagate in ~15 minutes. These are independent of cache
  invalidation. If a function change is not reflected, check
  function propagation status, not invalidation status.

- **S3 Object Lambda with CloudFront (2024):** When using S3 Object
  Lambda as a CloudFront origin, invalidation clears the edge cache
  but the Object Lambda transformation is applied on each origin
  fetch. Verify the transformation is correct before invalidating.

## Domain

AWS CloudOps / CloudFront Cache Invalidation, Cache-Busting Strategy
& Continuous Deployment.

## AWS documentation

- **CloudFront Developer Guide** — https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/
- **Invalidating files** — https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Invalidation.html
- **CreateInvalidation API** — https://docs.aws.amazon.com/cloudfront/latest/APIReference/API_CreateInvalidation.html
- **GetInvalidation API** — https://docs.aws.amazon.com/cloudfront/latest/APIReference/API_GetInvalidation.html
- **Continuous deployment** — https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/continuous-deployment.html
- **CloudFront pricing** — https://aws.amazon.com/cloudfront/pricing/
- **CloudFront CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/cloudfront/
- **Cache policies** — https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/controlling-the-cache-key.html
