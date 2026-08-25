# Error Handling — Auto Scaling Policy Deployer

## Step 1 — common mistake: skipping the baseline check

**Common mistake:** skipping this step because "the policy will adjust
capacity." A policy cannot scale beyond MaxSize; an ASG with MaxSize=1
and a CPU target tracking policy silently caps at 1 instance regardless
of load.

## Step 2 — common mistake: dual-policy trap

**Common mistake:** layering target tracking and step scaling on the
SAME metric. This is the dual-policy trap (see Expert heuristic). Use
different metric dimensions or predictive + target tracking.

## Step 3 — common mistake: custom-metric Dimensions mismatch

**Common mistake:** using a `Dimensions` value that doesn't match the
metric actually emitted. Target tracking silently sees no datapoints
and never scales — no error is surfaced. Verify the metric emits data
with `get-metric-statistics` BEFORE attaching the policy.

## Step 3 — common mistake: TargetValue units

**Common mistake:** `TargetValue` for ALB RequestCountPerTarget is
per-instance-per-minute. Setting 1000 means 1000 requests per instance
per minute (~16 RPS per instance). Operators conflate this with RPS and
under-provision.

## Step 4 — common mistake: TreatMissingData default

**Common mistake:** omitting `--treat-missing-data`. The default
behavior is `missing` (alarm stays in its prior state), which means a
metric that stops emitting never triggers a scale-in. Use `breaching`
for scale-out alarms (missing data = treat as breaching) or
`notBreaching` for scale-in alarms.

## Step 4 — common mistake: policy created before alarm

**Common mistake:** creating the policy BEFORE the alarm, then
forgetting to attach the policy ARN as an `--alarm-actions`. The
policy exists but never fires.

## Step 5 — common mistake: timezone defaults to UTC

**Common mistake:** omitting `--time-zone`. The default is UTC; an
operator who writes `0 9 * * 1-5` expecting 9 AM local gets 9 AM UTC
(5 AM Eastern). Always specify `--time-zone` and verify with
`describe-scheduled-actions`.

## Step 5 — common mistake: MinSize > MaxSize across overlapping actions

**Common mistake:** setting `MinSize > MaxSize` across overlapping
scheduled actions. Two scheduled actions at the same time with
conflicting bounds produce unpredictable capacity. Verify the schedule
chain: each action's bounds must be consistent with the next.

## Step 6 — common mistake: Running warm pool cost

**Common mistake:** setting `pool-state Running` for cost-sensitive
workloads — Running warm pool instances bill at full On-Demand/Spot
rate. Use `Stopped` (default) for the cost/performance tradeoff;
instances are pre-initialized (EBS volumes persist) but not billing
compute.

## Step 6 — common mistake: launch template breaks warm pool

**Common mistake:** a launch template change that breaks the warm
pool's AMI. The warm pool continues to hold instances from the OLD
template version; new scale-out pulls instances from the warm pool
that don't match the new template. Always trigger an instance refresh
(Step 7) after a launch template change to cycle the warm pool.

## Step 7 — common mistake: no checkpoints

**Common mistake:** omitting `CheckpointPercentages`. Without
checkpoints, the refresh runs to completion with no pause point — a
bad template version rolls through all instances before you can stop.
Set checkpoints at 50% and 100% to allow a pause-and-evaluate gate.

## Step 7 — common mistake: MinHealthyPercentage 100 without warm pool

**Common mistake:** triggering instance refresh on an ASG with no
warm pool and aggressive `MinHealthyPercentage=100`. The refresh
cannot replace any instance because doing so drops below 100% healthy.
Either set `MinHealthyPercentage <= 90` or provision a warm pool
first.

## Step 8a — common mistake: rebalance on On-Demand-only ASG

**Common mistake:** enabling capacity rebalance on an On-Demand-only
ASG. The setting is accepted but no-ops silently because there are no
Spot interruptions to respond to. Verify with
`describe-auto-scaling-groups --query ...MixedInstancesPolicy`.

## Step 8b — common mistake: ForecastOnly mode

**Common mistake:** using `Mode: ForecastOnly` and reading "predictive
scaling enabled" as "scaling is happening." `ForecastOnly` only emits
forecasts; `ForecastAndScale` is required for actual pre-provisioning.

## Step 8b — common mistake: < 24h CloudWatch history

**Common mistake:** insufficient CloudWatch history. Predictive
scaling needs >= 24h of `LoadMetric` data. On a fresh ASG, forecasts
are empty with no error surfaced. Verify with
`describe-scaling-policies` and check the `LoadForecast` datapoints.

## Step 8c — common mistake: lowest-price Spot strategy

**Common mistake:** using `SpotAllocationStrategy: lowest-price` with
`SpotInstancePools: 1`. This is the legacy strategy and picks the
single cheapest pool — it has the highest interruption rate. Use
`capacity-optimized` (recommended) or `price-capacity-optimized` for
production.

## Step 8c — common mistake: prioritized with a single override

**Common mistake:** `prioritized` strategy with only one instance type
override. The strategy silently falls back to single-type behavior;
the allocation strategy is ignored. Provide >= 2 overrides for any
diversification strategy to take effect.
