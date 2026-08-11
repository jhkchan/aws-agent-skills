# Example usage: lambda-cold-start-optimizer

A walkthrough showing the skill optimizing a Java Spring Boot API
function with high cold-start latency, demonstrating the SnapStart
enablement decision, the latency impact math, and the staged cutover
with versioned aliases.

## Input (user prompt)

> Our Java order API behind API Gateway has p95 cold-start latency of
> 5 seconds and our SLO is 1 second. Help me optimize the cold starts.

```text
FunctionName: order-api-prod
Runtime: java21
MemorySize: 512 MB
Architecture: x86_64
Region: us-east-1
SnapStart: NOT_ENABLED
VpcConfig: none
TracingConfig: Passthrough
Package size: 48 MB (fat JAR)
ProvisionedConcurrency: 0
SLO: p95 cold-start < 1000 ms

Metrics (last 30 days):
  - Duration avg: 1800 ms, p95: 2400 ms
  - InitDuration avg: 3100 ms (cold start), p95: 3200 ms
  - Invocations: 5,000,000/month
  - ColdStarts: ~75,000/month (1.5% of invocations)
  - Errors: 0

Workload context: Java 21 Spring Boot REST API behind API Gateway
(sync, user-facing). Uses standard Corretto distribution. No
container-image. DB connections initialized in global scope.
```

## Skill output

```text
TARGET: order-api-prod
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Java 21 function with InitDuration p95 of 3200 ms and SnapStart
  NOT enabled. Enabling SnapStart eliminates 90% of init phase (snapshot
  restore drops InitDuration from 3200 ms to ~200 ms). Sync API with
  cold-start p95 exceeding the 1000 ms SLO.
RECOMMENDATION:
  Current: 512 MB, java21, x86_64, SnapStart OFF, no PC, 48 MB
  Proposed: 512 MB, java21, x86_64, SnapStart ON, no PC, 48 MB
  Dimensions changed: snapstart (Step 3)
  Dimensions checked: memory ✓  provisioned_concurrency ✓  snapstart → (enable)
    init_phase ✓  vpc ✓  runtime ✓  package ✓
  Confidence: HIGH — SnapStart supported on java21; Corretto; no
    container-image; DB connections at global scope (handles restore reset).
ESTIMATED_LATENCY_IMPACT:
  Current cold-start p95: 5000 ms (InitDuration: 3200 ms + Duration: 1800 ms)
  Projected cold-start p95: 2000 ms (InitDuration: 200 ms + Duration: 1800 ms)
  Latency reduction: 3000 ms (60%)
  SLO: p95 < 1000 ms — SnapStart alone does NOT meet SLO; pair with
    provisioned concurrency for full SLO compliance.
MIGRATION_STEPS:
  1. Enable SnapStart:
     aws lambda update-function-configuration --function-name order-api-prod
       --snap-start '{"ApplyOn":"PublishedVersions"}'
  2. Publish a version:
     aws lambda publish-version --function-name order-api-prod
  3. Update the production alias:
     aws lambda update-alias --function-name order-api-prod
       --name prod --function-version <new-version>
  4. Verify SnapStart optimization status:
     aws lambda get-function-configuration --function-name order-api-prod
       --qualifier <new-version> --query 'SnapStart.OptimizationStatus'
     Expect: "On" after 1-2 minutes.
  5. Monitor InitDuration for 7 days.
  6. If SLO still not met (projected p95 = 2000 ms > 1000 ms SLO),
     add provisioned concurrency sized to p50-p75 ConcurrentExecutions.
CONFIRM: About to enable SnapStart on order-api-prod (publish version,
  update alias). Projected cold-start reduction: 3000 ms (60%).
  Proceed? (yes/no)
```

## What the skill caught that a generic assistant misses

1. **SnapStart is the heaviest single lever for Java.** A generic
   assistant might suggest "increase memory" or "use provisioned
   concurrency." The skill identifies SnapStart as the highest-impact,
   lowest-cost optimization (no code change, no idle spend).

2. **SnapStart alone does NOT meet the SLO.** The skill projects the
   post-SnapStart p95 at 2000 ms — still above the 1000 ms SLO. It
   flags this explicitly and recommends provisioned concurrency as a
   follow-up. A generic assistant would claim SnapStart "fixes" the
   problem without verifying against the SLO.

3. **Versioned alias workflow.** The skill publishes a version, updates
   the alias, and verifies SnapStart status — never enables SnapStart
   on `$LATEST`. A generic assistant goes straight to
   `update-function-configuration` without the version safety net.

4. **DB connection reset warning.** SnapStart resets TCP connections
   on restore. The skill notes that DB connections are already at global
   scope, which means the lazy-reconnect pattern must handle the reset.
   A generic assistant ignores this caveat entirely.

5. **Seven-dimension checklist.** The skill verifies all seven
   dimensions (memory, provisioned concurrency, SnapStart, init phase,
   VPC, runtime, package) and marks each. A generic assistant focuses
   on one dimension and misses the others.

6. **Latency arithmetic is shown explicitly.** The skill shows
   `InitDuration: 3200 ms → 200 ms` so the operator can verify the 60%
   reduction claim.

## Slash-command invocation

```
/aws:optimize-lambda-cold-start
```

Or via the orchestrator:

```
/aws:pipeline
You: "optimize our Lambda cold-start latency"
```

The orchestrator emits
`[Phase: Optimize | Skills routed: lambda-cold-start-optimizer]` and
hands off to this skill for the optimization block.

## Live-account follow-up (optional, requires AWS CLI)

After enabling SnapStart, validate the new configuration:

```bash
# Confirm SnapStart is enabled and optimized
aws lambda get-function-configuration \
  --function-name order-api-prod --qualifier prod \
  --profile default --output json | \
  jq '{SnapStart, Runtime, MemorySize, Architectures}'

# Monitor InitDuration for 7 days post-change
aws cloudwatch get-metric-statistics --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=order-api-prod \
  --start-time $(date -d '-7 days' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 3600 --statistics Average,p95 --output json
```

If InitDuration does not drop to ~200 ms after SnapStart, verify:
1. The alias points at a published version (not `$LATEST`).
2. The `OptimizationStatus` shows `"On"`.
3. The function has no incompatibility (container-image functions do
   not support SnapStart).

## Fleet-wide extension

For a fleet of N Lambda functions, run the skill in batch mode:

1. Pull all functions with `aws lambda list-functions`.
2. Filter to Java functions (highest cold-start potential).
3. Check SnapStart status for each.
4. For functions without SnapStart, emit per-function MIGRATION_STEPS.
5. For non-Java functions with high InitDuration, evaluate init phase
   optimization and provisioned concurrency.
6. Slice into batches of 5 functions.
7. For each batch: emit recommendations, then a single CONFIRM.
8. Verify each batch before proceeding.
