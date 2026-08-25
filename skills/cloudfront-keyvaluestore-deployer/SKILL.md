---
name: cloudfront-keyvaluestore-deployer
description: 'Provisions CloudFront KeyValueStore (KVS) with production defaults: KVS creation and key-value pair management, CloudFront Functions integration (read KVS data at the edge without redeploy), A/B testing request routing via KVS, feature flag toggles at the edge, IP allowlists and blocklists, URL redirects and rewrites driven by KVS, KVS size limits (1 MB max store, key/value constraints), KVS propagation and eventual consistency model, and the latest CloudFront Functions KVS API (cloudfront-js-2.0 with cf.openKvs). Emits a READY_TO_DEPLOY checklist with verification commands. Use when provisioning a CloudFront KeyValueStore, integrating CloudFront Functions with KVS for edge-side routing, implementing A/B testing or feature flags at the CDN edge, or building IP allowlist logic. Triggers: create CloudFront KeyValueStore, KVS CloudFront Functions, edge A/B testing, feature flags KVS, IP allowlist KVS, cf.openKvs, cloudfront-js-2.0.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with cloudfront and cloudfront-keyvaluestore access. Works with Terraform aws_cloudfront_key_value_store / aws_cloudfront_function resources and CloudFormation AWS::CloudFront::KeyValueStore templates.'
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Networking
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, cloudfront, keyvaluestore, cloudfront-functions, networking, cloudops, deploy, edge-computing, provisioning, feature-flags, ab-testing
  dependencies: aws-orchestrator
  keywords: aws, cloudfront, keyvaluestore, kvs, cloudfront functions, edge computing, cloudops, deploy, provisioning, a/b testing, feature flags, ip allowlist, ip blocklist, url redirect, edge routing, cloudfront-js-2.0, cf.openkvs, eventual consistency
  when_to_use: Invoke when the user wants to create a CloudFront KeyValueStore (KVS), integrate CloudFront Functions with KVS for edge-side data lookup, implement A/B testing or canary routing at the CDN edge, deploy feature flags that toggle without function redeployment, build IP allowlist or blocklist logic in CloudFront Functions, or drive URL redirects/rewrites from externally managed key-value data. Do NOT invoke for Lambda@Edge (different runtime, no KVS access), for CloudFront origin failover (use origin groups, not KVS), for caching behavior changes (use cache policies, not KVS), or for auditing existing CloudFront distributions (use cloudfront-distribution-auditor).
---

# CloudFront KeyValueStore Deployer

An AWS CloudOps agent skill that provisions CloudFront KeyValueStore
(KVS) with correct defaults. Walks the operator through KVS creation,
key-value pair management, CloudFront Functions integration, and
use-case patterns (A/B testing, feature flags, IP allowlists), and
emits a READY_TO_DEPLOY checklist with verification commands.

## Activation keywords

create CloudFront KeyValueStore, KVS CloudFront Functions, edge A/B
testing, feature flags KVS, IP allowlist KVS, cf.openKvs,
cloudfront-js-2.0 runtime, KVS propagation, KVS 1MB limit.

## STRICT output contract

When this skill is invoked with a CloudFront-KVS-provisioning request
(KVS creation, Functions integration, A/B testing, feature flags, IP
allowlist, or a partial configuration), the agent MUST respond with the
READY_TO_DEPLOY checklist defined in the "Output format" section using
the literal all-caps labels `KVS_DEPLOYMENT:`, `VERDICT:`, `CHECKLIST:`,
and `VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels breaks
automation silently.

If any prerequisite is missing, the verdict is
`PREREQUISITES_MISSING` with a specific gap citation in the checklist
(marked `[✗]`), and `READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — KVS creation (store + key-value pairs) | Store setup |
| Step 2 — Key-value pair management (put/get/delete) | Data management |
| Step 3 — CloudFront Functions integration (cf.openKvs) | Function linkage |
| Step 4 — A/B testing routing via KVS | Traffic splitting |
| Step 5 — Feature flags via KVS | Flag toggles |
| Step 6 — IP allowlists / blocklists via KVS | Access control |
| Step 7 — KVS size limits (1 MB store, key/value constraints) | Sizing |
| Step 8 — KVS propagation and eventual consistency | Consistency model |
| Step 9 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/kvs-functions-integration.md | Functions KVS API detail |
| references/provisioning-cli-commands.md | Copy-pasteable CLI sequence |

## Mindset

**One-line takeaway:** CloudFront KeyValueStore (KVS) is a managed key-
value data store that CloudFront Functions read at the edge. It lets
you change routing, feature flags, IP lists, and redirect rules WITHOUT
redeploying function code — update the KVS data and the change
propagates to edge locations within seconds.

Three misconceptions dominate KVS misdesign at provisioning time:

- **"I can store large datasets in KVS."** You cannot. The total store
  size is limited to 1 MB (including keys, values, and metadata). KVS is
  for small, high-velocity configuration data — not a general-purpose
  database. Exceeding 1 MB returns `SizeLimitExceeded`.

- **"KVS updates are instantly visible at every edge."** They are not.
  KVS is eventually consistent. Updates propagate to edge locations
  within seconds to minutes. Functions at different PoPs may read stale
  data briefly. If you need immediate consistency, KVS is the wrong tool.

- **"I can write to KVS from inside a CloudFront Function."** You
  cannot. Functions have READ-ONLY access to KVS. All writes (put-key,
  delete-key) happen via the AWS API (CLI, SDK, Console, IaC). The
  function reads; the operator writes.

## Configuration dependency graph (novel heuristic)

KVS configurations are NOT independent. The function runtime, KVS
association, and data schema interact in ways that silently break at
the edge. Use this graph both to sequence provisioning and to debug
"why isn't my function reading the KVS?" later.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| KVS store | none — `create-key-value-store` | store name is immutable after creation (must delete + recreate to rename) | key-value pairs |
| Key-value pairs | KVS store exists (`--kvs-arn`) | total store size MUST stay under 1 MB (keys + values); `SizeLimitExceeded` on overflow | edge reads from Functions |
| Function runtime | `cloudfront-js-2.0` (required for KVS API) | `cloudfront-js-1.0` does NOT support `cf.openKvs()` — function silently fails | KVS read access |
| Function-KVS link | function `FunctionConfig.Runtime` = `cloudfront-js-2.0` | KVS is associated at function level, NOT at distribution level; unlinked function gets `null` from `openKvs()` | edge data lookup |
| Distribution association | function exists + published (`PublishFunction`) | unpublished functions (`DEVELOPMENT` stage) are NOT invoked at the edge; test with `TestFunction` first | live edge execution |
| KVS data schema | consistent key naming across all edge locations | inconsistent key casing (`userID` vs `userId`) causes `get()` to return `undefined` silently | correct routing decisions |
| etag (concurrency) | `--if-match <etag>` for all updates | stale etag → `PreconditionFailed`; always re-fetch etag before update | safe concurrent writes |

**The runtime and etag rows are the ones a baseline model misses.** A
function created with `cloudfront-js-1.0` cannot read KVS — the
`cf.openKvs()` call does not exist in that runtime. And every KVS
update requires the current etag; a stale etag silently fails.

**Cross-dependency gotchas:**
- The function runtime MUST be `cloudfront-js-2.0` for KVS access.
- KVS is linked to the FUNCTION, not the distribution. Multiple
  distributions can use the same function (and thus the same KVS).
- The function must be PUBLISHED (`PublishFunction`) before it executes
  at the edge. A function in `DEVELOPMENT` stage runs only in tests.
- KVS data is eventually consistent. Do not use KVS for time-critical
  kill switches that must be instant across all PoPs.
- The etag changes on every KVS update. Scripts that batch-update keys
  must re-fetch the etag between each `put-key` call.

## Expert heuristic: KVS read-write asymmetry and etag concurrency

Expert heuristic on KVS read-write asymmetry and etag concurrency (write path vs read path, A/B rotation pattern, etag chaining, propagation window) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when planning KVS updates or debugging stale reads.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites.
If any are missing, the verdict is **PREREQUISITES_MISSING** with a
specific gap citation.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| AWS account with CloudFront access | Can't provision without it | `aws sts get-caller-identity` |
| KVS data size under 1 MB | Hard limit; `SizeLimitExceeded` on overflow | Estimate total key+value bytes |
| Function runtime `cloudfront-js-2.0` | KVS API (`cf.openKvs`) requires this runtime | Check function config |
| CloudFront distribution exists | KVS + Function are attached to a distribution | `aws cloudfront list-distributions` |
| KVS key naming convention | Inconsistent casing causes silent `undefined` reads | Define and document key schema |
| Write path identified (CLI/SDK/IaC) | Functions cannot write to KVS | Confirm update mechanism |
| etag handling in update scripts | Stale etag → `PreconditionFailed` | Script must re-fetch or chain etags |

## Step 1 — KVS creation (store + key-value pairs)

The first step is creating the KVS store. The store is a container for
key-value pairs. Once created, you populate it with data.

**Create the KVS store:**

```bash
KVS_ARN=$(aws cloudfront create-key-value-store \
  --name "ab-testing-kvs" \
  --comment "A/B testing traffic split configuration" \
  --query 'KeyValueStore.ARN' --output text)

echo "KVS ARN: $KVS_ARN"
```

**KVS store attributes:**
- `name`: immutable after creation. To rename, delete and recreate.
- `comment`: mutable via `update-key-value-store`.
- `status`: `READY` when the store is available for reads.
- `size`: current size in bytes (must stay under 1 MB).
- `itemCount`: number of key-value pairs.
- `etag`: concurrency token; changes on every mutation.

**Retrieve the KVS etag (required for all writes):**

```bash
ETAG=$(aws cloudfront-keyvaluestore describe-key-value-store \
  --kvs-arn "$KVS_ARN" \
  --query 'ETag' --output text)
```

**Common mistake:** creating the KVS with a generic name like "kvs1"
and later needing to rename it. The name is immutable — choose a
descriptive name reflecting the use case.

## Step 2 — Key-value pair management (put/get/delete)

Key-value pairs are managed via the `cloudfront-keyvaluestore` API
namespace (separate from the `cloudfront` namespace for store creation).

**Put a key:**

```bash
# Re-fetch etag before each write (etag changes on every mutation)
ETAG=$(aws cloudfront-keyvaluestore describe-key-value-store \
  --kvs-arn "$KVS_ARN" --query 'ETag' --output text)

aws cloudfront-keyvaluestore put-key \
  --kvs-arn "$KVS_ARN" \
  --key "traffic-split" \
  --value "variant-b" \
  --if-match "$ETAG"
```

**List all keys:**

```bash
aws cloudfront-keyvaluestore list-keys \
  --kvs-arn "$KVS_ARN"
```

**Delete a key:**

```bash
ETAG=$(aws cloudfront-keyvaluestore describe-key-value-store \
  --kvs-arn "$KVS_ARN" --query 'ETag' --output text)

aws cloudfront-keyvaluestore delete-key \
  --kvs-arn "$KVS_ARN" \
  --key "traffic-split" \
  --if-match "$ETAG"
```

**Key-value constraints:**
- Key length: up to 512 characters.
- Value length: up to 3 KB (3072 bytes) per value.
- Total store size: 1 MB maximum (all keys + values combined).
- Key characters: alphanumeric, hyphens, underscores, periods, colons,
  forward slashes. No spaces.
- Key matching is case-SENSITIVE. `UserID` and `userId` are different keys.

**Common mistake:** using inconsistent key casing across the write path
(CLI) and read path (function). The CLI writes `traffic-split` but the
function reads `TrafficSplit`. The `get()` returns `undefined` silently.

## Step 3 — CloudFront Functions integration (cf.openKvs)

The KVS is read by a CloudFront Function at the edge. The function
must use the `cloudfront-js-2.0` runtime and link to the KVS.

**Create a CloudFront Function with KVS access:**

```bash
# function.js — reads KVS at the edge
cat > function.js << 'EOF'
import cf from 'cloudfront';

const kvs = cf.openKvs();  // opens the KVS linked to this function

function handler(event) {
    const request = event.request;
    const cohort = kvs.get('traffic-split');

    if (cohort === 'variant-b') {
        request.uri = request.uri.replace('/api/', '/api-v2/');
    }
    return request;
}
EOF

aws cloudfront create-function \
  --name "ab-test-router" \
  --function-config '{"Comment":"A/B test router via KVS","Runtime":"cloudfront-js-2.0"}' \
  --function-code fileb://function.js \
  --key-value-store-associations '["'"$KVS_ARN"'"]'
```

**Publish the function (required for edge execution):**

```bash
aws cloudfront publish-function \
  --name "ab-test-router" \
  --if-match "$FUNCTION_ETAG"
```

**Associate the function with a distribution:**

```bash
aws cloudfront update-distribution \
  --id "$DIST_ID" \
  --if-match "$DIST_ETAG" \
  --distribution-config '{
    ...,
    "DefaultCacheBehavior": {
      ...,
      "FunctionAssociations": {
        "Quantity": 1,
        "Items": [{
          "FunctionARN": "arn:aws:cloudfront::123456789012:function/ab-test-router",
          "EventType": "viewer-request"
        }]
      }
    }
  }'
```

**Critical integration rules:**
- The function runtime MUST be `cloudfront-js-2.0`. The `cloudfront-js-1.0`
  runtime does NOT have the `cf.openKvs()` API.
- The KVS is linked to the FUNCTION via `--key-value-store-associations`,
  NOT at the distribution level.
- The function must be PUBLISHED before edge execution. Unpublished
  functions (`DEVELOPMENT` stage) only run in `test-function`.
- `EventType` is typically `viewer-request` for routing/redirect logic.

**Common mistake:** creating the function with the default
`cloudfront-js-1.0` runtime. The `cf.openKvs()` call does not exist in
1.0. Always verify the runtime is `cloudfront-js-2.0`.

## Step 4 — A/B testing routing via KVS

A/B testing is the canonical KVS use case. The KVS stores the traffic
split; the function reads it and routes accordingly. Changing the split
is a KVS data update — no code redeployment needed.

**KVS data schema for A/B testing:**

| Key | Value | Purpose |
|---|---|---|
| `ab-active` | `true` / `false` | Master kill switch |
| `ab-cohort` | `variant-a` / `variant-b` | Which variant to route to |
| `ab-percentage` | `0` to `100` | Percentage of traffic to variant-b |

Step 4 percentage-based A/B routing function code moved verbatim to [references/kvs-functions-integration.md](references/kvs-functions-integration.md).
Load it when writing the router function.

Step 4 traffic-split change CLI (describe etag, put-key ab-percentage) moved verbatim to [references/provisioning-cli-commands.md](references/provisioning-cli-commands.md).
Load it when rotating an A/B split without redeployment.

**Common mistake:** using `Math.random()` for traffic assignment instead
of a deterministic hash. Random assignment bounces the same user between
variants on every request. Use a hash of a stable request property.

## Step 5 — Feature flags via KVS

Step 5 feature-flag pattern (schema, maintenance-mode/checkout function code, toggle CLI, JSON-value mistake) moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load it when provisioning feature flags.

## Step 6 — IP allowlists / blocklists via KVS

Step 6 IP allowlist/blocklist pattern (schema, blocklist function code, CIDR limitation, KVS-vs-WAF table) moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load it when provisioning edge IP filtering.

## Step 7 — KVS size limits (1 MB store, key/value constraints)

The 1 MB total store limit is the most commonly hit constraint. Plan
the data schema to stay within limits.

**Size budget calculation:**

```text
Total store size = sum of (key_length + value_length) for all pairs
Maximum = 1 MB (1,048,576 bytes)

  100 keys × 20-char key × 100-char value  = ~12 KB   ✓
  1,000 keys × 30-char key × 500-char value = ~530 KB  ✓
  5,000 keys × 40-char key × 200-char value = ~1.2 MB  ✗ OVER
```

**Check current KVS size:**

```bash
aws cloudfront-keyvaluestore describe-key-value-store \
  --kvs-arn "$KVS_ARN" \
  --query 'Size'
```

**Size optimization strategies:**
- Use short, abbreviated keys (`v2` instead of `api-version-2-flag`).
- Store booleans as single chars (`1`/`0` instead of `true`/`false`).
- Use prefix-based namespacing (`flg:checkout` instead of nested JSON).
- Offload large data to S3; store only the pointer in KVS.
- Split large datasets across multiple KVS stores (one per use case).

## Step 8 — KVS propagation and eventual consistency

KVS is eventually consistent (see the expert heuristic above for the
propagation timeline). Key consistency characteristics:

- **Read-your-writes:** NOT guaranteed. A write via CLI followed by an
  immediate function read may return stale data.
- **Monotonic reads:** Guaranteed. Once a PoP sees a new value, it will
  never revert to an older value.
- **Eventual convergence:** All PoPs converge within seconds to minutes.

**When acceptable:** A/B testing, feature flags, gradual rollouts.
**When NOT acceptable:** security kill switches (use WAF), rate-limit
thresholds (use WAF rate-based rules).

## Step 9 — Recent features

Step 9 recent features (KVS GA, cloudfront-js-2.0, IaC support, test-function KVS, CloudWatch metrics) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when using IaC or KVS metrics.

## NEVER do these things

1. **NEVER use the `cloudfront-js-1.0` runtime for KVS-enabled
   functions.** The `cf.openKvs()` API exists ONLY in
   `cloudfront-js-2.0`. A function created with 1.0 silently fails to
   read KVS data. Always verify the runtime before publishing.

2. **NEVER exceed the 1 MB total store size.** The hard limit includes
   all keys, values, and metadata. `put-key` returns
   `SizeLimitExceeded` when the store is full. Monitor `KvsSize` and
   plan data schemas to stay within budget.

3. **NEVER attempt to write to KVS from inside a CloudFront Function.**
   Functions have READ-ONLY access to KVS. The `cf.openKvs()` handle
   provides only `.get(key)`. All writes (put, delete) must go through
   the AWS API (CLI, SDK, IaC).

4. **NEVER reuse a stale etag for KVS mutations.** Every `put-key` and
   `delete-key` requires the CURRENT etag. A stale etag returns
   `PreconditionFailed`. Scripts must re-fetch the etag before each write.

5. **NEVER deploy an unpublished function to production.** Functions in
   `DEVELOPMENT` stage only run via `test-function`. You MUST call
   `publish-function` before the function executes at the edge.

6. **NEVER use KVS for security-critical instant-propagation rules.**
   KVS is eventually consistent (seconds to minutes across PoPs). For
   IP blocklists that must propagate instantly, use AWS WAF IP sets.

7. **NEVER use `Math.random()` for A/B test assignment.** Random
   assignment causes the same user to bounce between variants on every
   request. Use a deterministic hash of a stable request property.

8. **NEVER assume KVS key matching is case-insensitive.** Keys are
   case-SENSITIVE. `FeatureFlag` and `featureflag` are different keys.
9. **NEVER link a KVS at the distribution level.** KVS is linked to
   the FUNCTION, not the distribution.

## Output format

```text
KVS_DEPLOYMENT: <kvs-name> (<kvs-arn>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] KVS store: <name> — created | existing
  [✓|✗] Store size: <current-size> / 1 MB (<percentage>% used)
  [✓|✗] Key count: <count> keys
  [✓|✗] Key schema: <convention> (e.g., kebab-case with prefixes)
  [✓|✗] Use case: A/B testing | Feature flags | IP allowlist | Redirects | Custom
  [✓|✗] Function name: <function-name>
  [✓|✗] Function runtime: cloudfront-js-2.0 (REQUIRED for KVS)
  [✓|✗] Function stage: LIVE (published) | DEVELOPMENT (unpublished)
  [✓|✗] KVS-function link: associated via --key-value-store-associations
  [✓|✗] Distribution: <distribution-id> — viewer-request event
  [✓|✗] Write path: CLI | SDK | IaC (Terraform/CloudFormation)
  [✓|✗] etag handling: re-fetch before each write | chain from response
  [✓|✗] Propagation: eventual consistency acknowledged (seconds to minutes)
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws cloudfront-keyvaluestore describe-key-value-store --kvs-arn <arn>
  aws cloudfront-keyvaluestore list-keys --kvs-arn <arn>
  aws cloudfront describe-function --name <function-name>
  aws cloudfront get-distribution-config --id <distribution-id>
```

### Worked example — A/B testing KVS with CloudFront Functions

```text
KVS_DEPLOYMENT: ab-testing-kvs (arn:aws:cloudfront::123456789012:key-value-store/abc-123)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] KVS store: ab-testing-kvs — created
  [✓] Store size: 156 bytes / 1 MB (0.01% used)
  [✓] Key count: 4 keys
  [✓] Key schema: kebab-case with ab- prefix
  [✓] Use case: A/B testing
  [✓] Function name: ab-test-router
  [✓] Function runtime: cloudfront-js-2.0 (REQUIRED for KVS)
  [✓] Function stage: LIVE (published)
  [✓] KVS-function link: associated via --key-value-store-associations
  [✓] Distribution: E1234567890ABC — viewer-request event
  [✓] Write path: CLI (put-key for traffic-split changes)
  [✓] etag handling: re-fetch before each write
  [✓] Propagation: eventual consistency acknowledged (seconds to minutes)
  [✓] Tags: Environment=production, UseCase=ab-testing
VERIFICATION_COMMANDS:
  aws cloudfront-keyvaluestore describe-key-value-store --kvs-arn arn:aws:cloudfront::123456789012:key-value-store/abc-123
  aws cloudfront-keyvaluestore list-keys --kvs-arn arn:aws:cloudfront::123456789012:key-value-store/abc-123
  aws cloudfront describe-function --name ab-test-router
  aws cloudfront get-distribution-config --id E1234567890ABC
```

## Error handling

Error handling (SizeLimitExceeded, PreconditionFailed, undefined reads, silent edge failures, unpublished functions) moved verbatim to [references/error-handling.md](references/error-handling.md).
Load it when a KVS deployment errors.

## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) — KVS read-write asymmetry and etag concurrency heuristic, recent features moved from SKILL.md
- [references/worked-examples.md](references/worked-examples.md) — Step 5 feature-flag and Step 6 IP allowlist patterns moved from SKILL.md; the primary A/B testing example stays in SKILL.md
- [references/error-handling.md](references/error-handling.md) — KVS/Functions error catalog moved from SKILL.md
- [references/kvs-functions-integration.md](references/kvs-functions-integration.md) — Functions KVS API detail (now also holds the Step 4 A/B routing function code)
- [references/provisioning-cli-commands.md](references/provisioning-cli-commands.md) — copy-pasteable CLI sequence (now also holds the Step 4 traffic-split CLI)

## Domain

AWS CloudOps / CloudFront Edge Computing & KeyValueStore Provisioning.

## AWS documentation

- **CloudFront KeyValueStore** — https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/kvs-with-functions.html
- **CloudFront Functions** — https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/cloudfront-functions.html
- **cloudfront-js-2.0 runtime** — https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/functions-javascript-runtime-2.0.html
- **KVS API reference** — https://docs.aws.amazon.com/cloudfront/latest/APIReference/API_o_KeyValueStore.html
- **Terraform aws_cloudfront_key_value_store** — https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudfront_key_value_store
