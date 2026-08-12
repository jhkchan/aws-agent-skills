# Rate Control and Targets — SSM Association Operator

Deep reference on association rate control (integer counts vs
percentage strings, max-concurrency semantics, max-errors semantics,
how to choose values for fleet size and blast radius) and association
targeting (tag targets vs instance IDs vs resource groups, dynamic
membership, targeting across accounts and regions). Loaded on demand
by the skill — kept out of the main SKILL.md body so the operating
procedure stays scannable.

## Rate control fundamentals

### max-concurrency — how many instances run in parallel

`max-concurrency` controls the parallelism of an association run.
SSM fans the document execution out across the targeted instances in
batches of size `max-concurrency`.

```text
Targeted fleet: 100 instances
max-concurrency: 10
  → batches of 10 run in parallel
  → 10 batches total
  → if each run takes 60s, total ≈ 10 minutes
```

**Accepted forms:**

| Form | Example | Behavior | Recommended |
|---|---|---|---|
| Integer count | `10` | Exactly N instances in parallel | Yes — deterministic |
| Percentage string | `"10%"` | N% of fleet in parallel | No — fleet-size-dependent |
| Special: `"1"` | `1` | Strict one-at-a-time | Yes — for fragile rollouts |

**Why the integer form is preferred:** it is deterministic across
fleet sizes. `max-concurrency: 10` means exactly 10 instances in
parallel whether the fleet is 3 instances (one batch of 3, the limit
is moot) or 3000 (300 batches of 10). The percentage form `"10%"` is
0.3 (rounds to 1) on a 3-instance fleet and 300 on a 3000-instance
fleet — radically different behavior in dev vs prod.

**Setting max-concurrency via CLI:**

```bash
aws ssm create-association \
  --name "AWS-ApplyPatchBaseline" \
  --targets "Key=tag:Environment,Values=production" \
  --max-concurrency 10 \
  --max-errors 3 \
  --region us-east-1
```

### max-errors — when to stop

`max-errors` is the circuit breaker. When the cumulative error count
reaches `max-errors`, the association stops scheduling new runs. Runs
already in flight continue to completion.

```text
Fleet: 100 instances
max-concurrency: 10
max-errors: 3

Execution timeline:
  Batch 1 (10 instances): 0 errors → continue
  Batch 2 (10 instances): 1 error  → continue (cumulative: 1)
  Batch 3 (10 instances): 2 errors → continue (cumulative: 3 — at limit)
  Batch 4: STOPPED — max-errors reached
  Batches 5..10: never run
```

**Choosing max-errors:**

| Strategy | max-errors | Effect |
|---|---|---|
| Strict (one error stops) | `1` | Use for dangerous operations; catches regressions early |
| Conservative (small fleet) | `3` | Allows transient errors while still tripping on systemic failure |
| Looser (large fleet) | `5-10` | Tolerates a small percentage of misconfigured hosts |
| Never stop | `0` | Runs the entire fleet regardless of errors (risky) |

**Critical:** `max-errors: 0` means "do not stop on errors." This is
rarely correct — it means a broken document will be applied to the
entire fleet without any circuit breaker.

### Interaction between the two knobs

The two knobs interact. With `max-concurrency: 10` and `max-errors:
3`, the worst case is 12 instances receive a broken document before
the run stops (10 in flight when the third error lands, plus the 2
that errored). Plan blast radius accordingly:

```text
Worst-case blast radius (approx):
  max-concurrency + max-errors - 1

  Example: max-concurrency=10, max-errors=3 → up to 12 instances affected
  Example: max-concurrency=1,  max-errors=1 → up to 1 instance affected (strict)
```

### Percentage strings: why the skill normalizes them away

The API technically accepts `max-concurrency: "10%"` and `max-errors:
"5%"`. The skill always normalizes to integer counts and flags
percentage strings as a REVIEW_REQUIRED finding when the user supplies
them. Reasons:

1. **Fleet-size-dependent.** `"10%"` of a 3-instance fleet is 0 or 1
   (rounding-dependent); of a 3000-instance fleet is 300. The same
   configuration behaves differently across environments.

2. **Rounding is implementation-defined.** AWS does not document the
   rounding behavior for sub-instance percentages. Empirically, AWS
   rounds up for concurrency and down for errors, but this is not
   guaranteed.

3. **Audit and review friction.** A reviewer reading
   `max-concurrency: "10%"` in a Terraform state file cannot reason
   about blast radius without knowing the fleet size at apply time.

4. **Incompatible with strict rollout.** `max-concurrency: "1%"` is
   not the same as `max-concurrency: 1`. For strict one-at-a-time
   rollouts, the integer form is the only safe choice.

**Normalization rule:** for any user-supplied percentage string, the
skill computes the equivalent integer for the current fleet size,
rounds up, and emits the integer. If the fleet size is unknown, the
skill requests it (REVIEW_REQUIRED) before applying.

## Target types

### Tag targets (dynamic)

Tag targets use `Key=tag:<tag-key>,Values=<values>`. They are
DYNAMIC: any instance that gains the tag is automatically picked up
at the next association run.

```bash
# Target all instances tagged Environment=production
aws ssm create-association \
  --name "AWS-ApplyPatchBaseline" \
  --targets "Key=tag:Environment,Values=production" \
  --region us-east-1
```

```text
At time T0: 3 instances tagged Environment=production
  → association runs on 3 instances

At time T1: Auto Scaling adds 2 more instances with Environment=production
  → next run automatically picks up 5 instances — no association update
```

**When to use tag targets:**
- Auto Scaling fleets
- Dynamic environments where instances are added/removed
- Cross-team shared fleets identified by a tag

**Multi-value tag targets:**

```bash
# Target instances tagged Environment=production OR Environment=staging
aws ssm create-association \
  --name "AWS-ApplyPatchBaseline" \
  --targets "Key=tag:Environment,Values=production,staging" \
  --region us-east-1
```

**Multi-tag intersection (logical AND):**

To target instances matching multiple tags simultaneously (e.g.,
Environment=production AND Role=web), pass multiple `--targets`
entries:

```bash
aws ssm create-association \
  --name "AWS-ApplyPatchBaseline" \
  --targets \
    "Key=tag:Environment,Values=production" \
    "Key=tag:Role,Values=web" \
  --region us-east-1
```

Both `--targets` entries are combined with logical AND — only
instances matching ALL target filters are included.

### Instance-ID targets (static)

Instance-ID targets use `Key=InstanceIds,Values=<id1>,<id2>,...`.
They are STATIC: only the listed instance IDs are targeted, ever.

```bash
aws ssm create-association \
  --name "Custom-HardenBaseline" \
  --targets "Key=InstanceIds,Values=i-aaa111bb222,i-ccc333dd444" \
  --region us-east-1
```

**When to use instance-ID targets:**
- Fixed pet servers that never scale
- One-off instances with unique configuration
- Targeted remediation of specific known-bad hosts

**When NOT to use instance-ID targets:**
- Auto Scaling fleets (new instances will not be picked up)
- Dynamic environments
- Any case where the instance set changes

**Updating the target list:** to add or remove instances from a
static-target association, you must call `update-association` with the
new `--targets` value. There is no incremental add/remove API.

### Resource-group targets

Resource groups allow more complex membership rules defined ahead of
time. Use `Key=ResourceGroups,Values=<rg-arn>`.

```bash
aws ssm create-association \
  --name "AWS-ApplyPatchBaseline" \
  --targets "Key=ResourceGroups,Values=arn:aws:resource-groups:us-east-1:123456789012:group/web-fleet" \
  --region us-east-1
```

Resource groups are dynamic like tags but support more complex
queries (e.g., "instances in account X, region Y, with tag Z AND
launched after date W"). Manage the group definition via
`aws resource-groups`.

### All managed instances

To target all SSM-managed instances in the account/region, use the
special wildcard:

```bash
aws ssm create-association \
  --name "AWS-GatherSoftwareInventory" \
  --targets "Key=InstanceIds,Values=*" \
  --region us-east-1
```

**Warning:** this is rarely the right choice for state-changing
documents. Use it only for read-only inventory collection or agent
updates.

## Multi-account and multi-region targeting

For multi-account/multi-region fan-out, use `--target-locations` (a
feature added in 2023-2024). This requires AWS Organizations
integration and a delegated administrator account for SSM.

```bash
aws ssm create-association \
  --name "AWS-ApplyPatchBaseline" \
  --schedule-expression "rate(30 minutes)" \
  --target-locations \
    '[{"ExecutionRoleName":"AWS-SystemsManager-AutomationExecutionRole","Accounts":["111111111111","222222222222"],"Regions":["us-east-1","us-west-2"],"TargetLocationMaxConcurrency":10,"TargetLocationMaxErrors":3}]' \
  --region us-east-1
```

Each account and region combination receives the association
independently. The `ExecutionRoleName` must exist in each target
account.

## Common targeting pitfalls

### Pitfall 1: instance-ID target on an autoscaling fleet

The most common targeting mistake. A user creates an association
targeting specific instance IDs, then the Auto Scaling group replaces
an instance. The new instance is not picked up because it has a new
instance ID. The association silently runs on zero instances.

**Fix:** switch to tag-based targets. Tag the Auto Scaling group's
launch template, so every launched instance inherits the tag.

### Pitfall 2: tag-key vs tag:<key>

Tag targets use `Key=tag:<tag-key>`, NOT `Key=<tag-key>` or
`Key=tag-key`. The `tag:` prefix is mandatory.

**Wrong:** `Key=Environment,Values=production`
**Right:** `Key=tag:Environment,Values=production`

### Pitfall 3: percentage rate control on a small fleet

A user sets `max-concurrency: "10%"` on a 5-instance fleet. 10% of 5
is 0.5, which rounds to 0 or 1 depending on the implementation. The
association may run on zero instances or run strictly one-at-a-time,
neither of which matches the user's intent.

**Fix:** use the integer form. For a 5-instance fleet,
`max-concurrency: 5` runs all of them in parallel; `max-concurrency:
1` runs them one at a time.

### Pitfall 4: max-errors too strict for large fleets

A user sets `max-errors: 1` on a 1000-instance fleet. The first
transient error stops the entire run. 999 instances never receive the
document.

**Fix:** scale `max-errors` with the fleet size. A common rule of
thumb is `max-errors` = max(3, 1% of fleet size) — but always emit it
as an integer.

## Terraform examples

```hcl
resource "aws_ssm_association" "patch_production" {
  name = "AWS-ApplyPatchBaseline"

  targets {
    key    = "tag:Environment"
    values = ["production"]
  }

  schedule_expression = "rate(30 minutes)"
  max_concurrency     = 10
  max_errors          = 3
  compliance_severity = "HIGH"

  parameters = {
    Operation  = "Install"
    SnapshotId = "latest"
  }

  output_location {
    s3_bucket_name = "my-ssm-output"
    s3_key_prefix  = "ssm-output/"
    s3_region      = "us-east-1"
  }

  apply_only_at_cron_interval = false  # apply at creation

  tags = {
    Environment = "production"
    Owner       = "cloudops"
  }
}
```

**Critical:** `apply_only_at_cron_interval = false` is the Terraform
equivalent of `--apply-at-creation`. The default is `true` (do not
apply at creation), so you must explicitly set it to `false` for an
immediate first run.
