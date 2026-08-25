# Traffic Shifting and Concurrency — Lambda Alias Deployer

Detailed reference on weighted traffic shifting strategies, rollback
procedures, provisioned concurrency placement, and Auto Scaling
configuration for Lambda aliases. Loaded on-demand when the operator
needs to reason about deployment safety and cold-start elimination.

## Traffic shifting strategies

### Canary deployment

Shift a small percentage of traffic to the new version, monitor,
then ramp to 100%.

```text
Step 1: Publish version 6
Step 2: Shift 10% to version 6 (90% stays on version 5)
Step 3: Monitor CloudWatch alarms for 5-10 minutes
Step 4a: If healthy → shift 100% to version 6
Step 4b: If errors → rollback to 100% on version 5
```

**Commands:**
```bash
# 10% canary
aws lambda update-alias \
  --function-name my-function \
  --name prod \
  --function-version 5 \
  --routing-config AdditionalVersionWeights='{"6":0.1}'

# 100% (finalize)
aws lambda update-alias \
  --function-name my-function \
  --name prod \
  --function-version 6 \
  --routing-config '{}'

# Rollback (back to old version)
aws lambda update-alias \
  --function-name my-function \
  --name prod \
  --function-version 5 \
  --routing-config '{}'
```

### Linear deployment

Gradually increase the percentage in fixed increments over time.

```text
Step 1: Publish version 6
Step 2: Shift 10% → wait 5 min
Step 3: Shift 25% → wait 5 min
Step 4: Shift 50% → wait 5 min
Step 5: Shift 75% → wait 5 min
Step 6: Shift 100% (finalize)
```

**When to use linear over canary:** high-traffic functions where a
sudden 10% shift represents significant absolute volume. Linear
gives finer control over the rollout rate.

### All-at-once (not recommended)

Point the alias directly to the new version with no shifting.

```bash
aws lambda update-alias \
  --function-name my-function \
  --name prod \
  --function-version 6
```

**Risk:** no safety net. If the new version has a bug, 100% of
traffic is affected immediately. Only use for non-production aliases
or when the change is trivially safe.

## Rollback

Rollback is instant — no redeployment needed.

```bash
# Instant rollback: shift 100% back to old version
aws lambda update-alias \
  --function-name my-function \
  --name prod \
  --function-version 5 \
  --routing-config '{}'
```

This is the primary advantage of alias-based traffic shifting. The
old version is still published and available. There is no need to
redeploy code or wait for a build pipeline.

## Pre-traffic-shift validation with pre-signed URLs

Before shifting public traffic, test the new version privately:

```bash
# Test version 6 without shifting traffic
aws lambda invoke \
  --function-name my-function:6 \
  --payload '{"test": true}' \
  response.json
```

This invokes version 6 directly (bypassing the alias) for validation
before shifting any traffic.

## Provisioned concurrency placement matrix

| Placement | Follows alias? | Survives traffic shift? | Cost behavior | Recommendation |
|---|---|---|---|---|
| Alias (`--qualifier prod`) | Yes | Yes | Stable | **BEST** |
| Version (`--qualifier 6`) | No | No — stranded on old version | Wasted on old version | Avoid |
| Function (`$LATEST`) | n/a | Not supported | n/a | Never |

## Auto Scaling for provisioned concurrency

```bash
# Register the alias as a scalable target
aws application-autoscaling register-scalable-target \
  --service-namespace lambda \
  --resource-id function:my-function:prod \
  --scalable-dimension lambda:function:ProvisionedConcurrency \
  --min-capacity 2 \
  --max-capacity 50

# Target tracking: scale to keep utilization at 70%
aws application-autoscaling put-scaling-policy \
  --policy-name prod-pc-scaling \
  --service-namespace lambda \
  --resource-id function:my-function:prod \
  --scalable-dimension lambda:function:ProvisionedConcurrency \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{
    "TargetValue": 70.0,
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "LambdaProvisionedConcurrencyUtilization"
    },
    "ScaleInCooldown": 300,
    "ScaleOutCooldown": 60
  }'
```

**Scaling behavior:**
- `TargetValue: 70.0`: scales to keep utilization at 70%.
- `ScaleOutCooldown: 60`: wait 60 seconds between scale-out actions.
- `ScaleInCooldown: 300`: wait 5 minutes between scale-in actions
  (conservative to avoid flapping).

## Monitoring traffic shift health

During a traffic shift, monitor these CloudWatch metrics:

| Metric | Dimension | Alert threshold | Action |
|---|---|---|---|
| `Errors` | `my-function:prod` | > 5 in 1 min | Rollback |
| `Throttles` | `my-function:prod` | > 0 in 1 min | Increase concurrency |
| `Duration` (p99) | `my-function:prod` | > 2x baseline | Investigate |
| `IteratorAge` (streams) | `my-function:prod` | > 10000 ms | Increase concurrency |
| `ProvisionedConcurrencySpilloverInvocations` | `my-function:prod` | > 0 | Increase provisioned capacity |

## CodeDeploy vs alias traffic shifting

| Feature | CodeDeploy | Alias routing config |
|---|---|---|
| Rollback speed | Minutes (redeploy) | Instant (weight change) |
| Pre-traffic hook | Yes (pre-traffic Lambda) | Manual (invoke version directly) |
| Traffic shift granularity | Linear/C Canary/AllAtOnce | Any weight, any time |
| CloudWatch alarm integration | Automatic rollback | Manual monitoring + rollback |
| Complexity | Higher (CodeDeploy setup) | Lower (alias update only) |

**Recommendation:** use alias routing config for most deployments.
Use CodeDeploy when you need automatic alarm-based rollback and
pre-traffic validation hooks.

## Expert heuristic: weighted traffic shifting lifecycle

Traffic shifting is NOT a single API call. It is a progressive
rollout that shifts weight from one version to another over time.
A baseline model says "update the alias"; this heuristic explains
the full lifecycle.

```text
Publish version N (new code)
  → aws lambda publish-version
  → Version N is now immutable and has a version number

Alias currently points 100% to version N-1
  → Create/update alias to shift 10% to version N (canary)
  → aws lambda update-alias --routing-config AdditionalVersionWeights={"N":0.1}
  → 90% traffic → version N-1, 10% → version N

Monitor CloudWatch alarms for version N (Errors, Throttles, Duration)
  → If healthy: progressively shift 25% → 50% → 100% to version N
  → If unhealthy: rollback by shifting 100% back to version N-1

Final state: alias points 100% to version N
  → aws lambda update-alias --function-version N --routing-config {}
  → Remove routing config; alias is now a simple pointer to N
```

**Key implication:** Traffic shifting requires TWO published
versions. You cannot shift traffic to `$LATEST` — only to a
published version. This is the #1 cause of "why can't I set a
weight?" errors: the target version does not exist.

**Canary vs linear:**
- **Canary:** small initial burst (e.g., 10%) then jump to 100%.
  Good for fast validation with rollback safety.
- **Linear:** gradual increment (e.g., 10% every 5 minutes) until
  100%. Good for high-traffic functions where a sudden 10% shift
  is significant.
- **All-at-once (no shifting):** alias directly points 100% to the
  new version. No safety net. Not recommended for production.

**Rollback:** to rollback, set the weight back to the old version.
This is instant — no redeployment needed. This is the primary
advantage of alias-based traffic shifting over CodeDeploy-based
deployments.

## Expert heuristic: provisioned concurrency on alias vs version

Provisioned concurrency eliminates cold starts by pre-initializing
execution environments. A baseline model puts it on the function;
the correct approach is to put it on the ALIAS.

| Target | Behavior during traffic shift | Recommendation |
|---|---|---|
| Alias | Provisioned capacity follows the alias. As traffic shifts, provisioned environments serve the new version. Stable through rollouts. | **RECOMMENDED** |
| Version | Provisioned capacity is bound to that version number. When the alias re-points, the provisioned capacity is on the OLD version, not the new one. | Avoid for traffic-shifting scenarios |
| Function (publish) | Provisioned capacity applies to a specific published version. Same issue as version-level. | Same as version |
| $LATEST | Not supported. Provisioned concurrency cannot be configured on $LATEST. | Never use |

**Configuration on alias:**
```bash
aws lambda put-provisioned-concurrency-config \
  --function-name my-function \
  --qualifier prod \
  --provisioned-concurrent-executions 10
```

**Key rule:** The `--qualifier` parameter is the ALIAS name (e.g.,
`prod`), not a version number. This binds provisioned concurrency
to the alias, and it follows the alias as traffic shifts.

**Cost implication:** Provisioned concurrency is billed regardless
of invocations. You pay for the pre-initialized environments even
if no traffic arrives. Right-size based on steady-state traffic,
not peak. Use Application Auto Scaling to adjust dynamically.
