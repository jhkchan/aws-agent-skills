# Auto Scaling Group Auditor — Advanced Patterns

Expert-knowledge deep dives, ASG internals, and recent-feature notes
moved from SKILL.md. Load on demand before classifying edge-case ASGs.


## Step 0: Expert knowledge — non-obvious ASG behaviors that change classification (moved from SKILL.md)

These behaviors are easy to misjudge without operational Auto Scaling
experience. Each changes a verdict if ignored:

- **HealthCheckGracePeriod counts from instance launch, not ELB
  registration.** ELB target registration takes 30-60 seconds. A 60-second
  grace period gives the application effectively 0-30 seconds to boot,
  register, and pass health checks before evaluation begins. The safe minimum
  for most web apps is 300 seconds; JVM/.NET workloads often need 600+.
  A grace period under 60 seconds with an ELB health check is almost certainly
  a misconfiguration that causes premature termination of healthy instances.

- **ELB health check without a target group is a silent infinite loop.** When
  `HealthCheckType` is `ELB` but no `TargetGroupARNs` or `LoadBalancerNames`
  are attached, the ASG queries the ELB for health status, receives no target
  health data, and treats every instance as Unhealthy from launch. The ASG
  terminates and relaunches indefinitely. CloudWatch shows `GroupTotalInstances`
  cycling — it looks like "high churn," not a broken config.

- **Launch configurations are END-OF-LIFE and incompatible with MIP.** AWS
  deprecated new launch-configuration creation as of December 2023. Existing
  LCs still function but cannot enforce IMDSv2 (no `MetadataOptions` field),
  cannot be used with `MixedInstancesPolicy` (MIP requires a launch template),
  and cannot specify credit specifications or capacity reservations. An ASG
  with `LaunchConfigurationName` is locked into legacy infrastructure.

- **`$Latest` launch template version can split your fleet.** Updating a launch
  template immediately redirects `$Latest`. New instances use the new version;
  existing instances keep their pinned version. If the new version is broken
  (bad AMI, bad userdata, missing packages), new instances fail health checks
  and get replaced — an infinite loop because `$Latest` still points to the
  broken version. Pin a specific version number for production ASGs and update
  deliberately via instance refresh.

- **Spot single-instance-type is a total outage waiting to happen.** A
  `MixedInstancesPolicy` with only one instance type and Spot allocation
  (`OnDemandPercentageAboveBaseCapacity < 100`) means a single Spot
  interruption event affects 100% of Spot capacity. Minimum recommended: 3+
  instance types across 2+ AZs. Use `capacity-optimized` strategy to diversify
  across the most stable pools.

- **`OnDemandBaseCapacity` defines a fixed On-Demand floor;
  `OnDemandPercentageAboveBaseCapacity` applies ABOVE it.** Example: Base=2,
  Percentage=50, Desired=6 produces 2 On-Demand (base) + 2 On-Demand (50% of
  4 remaining) + 2 Spot (50% of 4 remaining) = 4 On-Demand, 2 Spot. Many
  operators misread this as "50% On-Demand of total capacity."

- **`SpotAllocationStrategy: capacity-optimized` ignores `SpotInstancePools`.**
  `SpotInstancePools` only applies to the `lowest-price` strategy. Setting both
  is dead configuration. For production Spot-backed ASGs, use
  `capacity-optimized` (or `price-capacity-optimized`) to minimize
  interruption frequency.

- **EC2 health checks do not detect application failure.** EC2 status checks
  only verify hypervisor-level health (network reachability, hardware). A hung
  application process (TCP listener up but not serving requests) passes EC2
  checks. If the ASG fronts traffic via an ELB, use `HealthCheckType: ELB`
  (or the comma-separated `ELB,EC2` for both layers).

- **`HealthCheckType: "ELB,EC2"` requires BOTH checks to pass.** A
  comma-separated value is an AND condition, not OR. This is stronger than
  either alone — the instance must pass the EC2 status check AND the ELB
  health check to be Healthy.

- **CapacityRebalance must be enabled for Spot-backed ASGs.** Without it, the
  ASG only reacts AFTER a Spot instance is terminated (2-minute warning
  received but no proactive action). With it, the ASG proactively launches a
  replacement when AWS sends a rebalance recommendation (up to 5 minutes before
  termination), draining the old instance via a lifecycle hook.

- **Standby instances count against MaxSize but not DesiredCapacity.** Putting
  instances in Standby (for debugging or patching) does not reduce the group's
  total capacity ceiling. If MaxSize is tight, standby instances block
  scale-out during traffic spikes.

- **MIP `LaunchTemplateSpecification` silently overrides the top-level
  `LaunchTemplate`.** When both the ASG's top-level `LaunchTemplate` and the
  `MixedInstancesPolicy.LaunchTemplate.LaunchTemplateSpecification` are set,
  the MIP's template wins — always. An operator who updates the top-level
  template expecting new instances to pick up the change will see no effect
  if an MIP is active. Always update the MIP's specification when an MIP
  exists.

- **WeightedCapacity absence causes silent capacity variance.** Without
  `WeightedCapacity` in each Override entry, every instance type counts as
  exactly 1 unit toward DesiredCapacity. A fleet mixing c5.large (2 vCPU) and
  c5.4xlarge (16 vCPU) at DesiredCapacity=4 could land anywhere between 8 and
  64 vCPUs depending on which types the ASG picks. Set WeightedCapacity based
  on vCPU or memory to normalize capacity units across diverse types.

- **`MaxInstanceLifetime` forces silent instance rotation.** If set (minimum
  86,400 seconds = 1 day), the ASG automatically terminates and replaces
  instances older than the limit. This is a security-rotation feature (limits
  the lifetime of potentially compromised instances), but operators are often
  surprised when long-running stateful instances are replaced without warning.
  If absent (the default), instances run indefinitely.

- **EC2 health check polling is a fixed 60-second interval, not configurable.**
  The ASG polls EC2 status checks every 60 seconds — there is no
  `--health-check-interval` flag. For ELB health checks, the ASG queries the
  ELB API (not the target directly) on the same ~60s cadence. The target
  group's own `HealthCheckIntervalSeconds` is independent — it controls how
  often the ELB checks the target, not how often the ASG queries the ELB.
  This means the effective detection time for an unhealthy instance is
  `HealthCheckGracePeriod + polling_interval + ELB_unhealthy_threshold`.

- **The Spot two-minute interruption warning is best-effort, not guaranteed.**
  AWS issues a 2-minute Spot Instance interruption notice when possible, but
  some capacity-reclaim events (EC2 spare-capacity reclaim, capacity blocks)
  may provide less than 2 minutes or no warning at all. CapacityRebalance uses
  the earlier rebalance-recommendation signal (up to 5 minutes before), making
  it strictly more reliable than relying on the 2-minute warning alone.

- **Suspending AZRebalance during deployments prevents churn.** While
  AZRebalance is enabled by default and beneficial at steady state, suspending
  it during a deployment (instance refresh, manual scaling) prevents the ASG
  from prematurely terminating instances in over-represented AZs before the
  new instances in under-represented AZs pass health checks. An ASG with
  AZRebalance suspended after a deployment will NOT correct AZ skew until it
  is re-enabled — flag this in the audit as an operational note.


## Deep reference: Auto Scaling internals (moved from SKILL.md)

### Health check evaluation lifecycle

When an instance launches in an ASG with `HealthCheckType: ELB`:

1. **Instance boots** (1-3 min): EC2 status checks transition from
   `initializing` to `ok`.
2. **ELB target registration** (30-60s): The target group registers the
   instance. During this window, the target is in `initial` state.
3. **Health check grace period** (starts at boot, not registration): The ASG
   waits `HealthCheckGracePeriod` seconds before evaluating health. If the
   grace period expires during registration, the instance may be marked
   Unhealthy prematurely.
4. **ELB health evaluation**: The target group's health check (configured
   separately) runs at `HealthCheckInterval` seconds. The target must pass
   `HealthyThreshold` consecutive checks to become `healthy`. Total time:
   `HealthyThreshold * HealthCheckInterval` (e.g., 3 * 30 = 90s).
5. **ASG health decision**: After the grace period, the ASG queries the ELB
   for target health. If `unhealthy`, the ASG schedules termination.

**Effective warmup budget** = `HealthCheckGracePeriod - registration_delay -
ELB_evaluation_time`. For a 300s grace period with 60s registration and 90s
evaluation, the app has ~150 seconds to boot and serve.

### Spot rebalancing timeline

- **Rebalance recommendation**: AWS sends a Spot Instance rebalance
  recommendation up to 5 minutes before the 2-minute interruption warning.
  This signal is available via EventBridge and the instance metadata service.
- **Without CapacityRebalance**: The ASG only reacts after the 2-minute
  warning — it launches a replacement but the old instance is terminated
  before the new one is ready, creating a capacity gap.
- **With CapacityRebalance**: The ASG immediately launches a new instance on
  the rebalance recommendation (up to 5 min earlier). When the new instance
  is healthy, the ASG puts the old instance in Standby (or terminates it if
  a lifecycle hook drains it). This minimizes the capacity gap.

### OnDemand/Spot capacity math

Given `OnDemandBaseCapacity=B`, `OnDemandPercentageAboveBaseCapacity=P`, and
`DesiredCapacity=D`:

- On-Demand instances = `B + ceil((D - B) * P / 100)`
- Spot instances = `D - On-Demand instances`

Example: B=2, P=50, D=6 → On-Demand = 2 + ceil(4 * 0.5) = 4, Spot = 2.

### AZ rebalancing

When `AZRebalance` is enabled (default), the ASG maintains even distribution
across AZs. If an AZ fails and recovers, AZRebalance launches instances in the
recovered AZ and terminates extras in other AZs. This can temporarily exceed
`MaxSize` (ASG allows brief over-capacity during rebalance). If `AZRebalance`
is suspended, the ASG does not rebalance after AZ failures — capacity remains
uneven until manual intervention.


## Recent AWS features (2024-2026) (moved from SKILL.md)

- **Instance maintenance policy (2024):** ASGs now support an instance maintenance policy that defines behavior (STOP, TERMINATE, or WAIT) during infrastructure events. Auditors should check whether critical ASGs have this policy configured — without it, AWS may take default actions that disrupt workloads during scheduled maintenance.
- **Warm pools GA (2024):** Warm pools keep pre-initialized instances ready to scale out faster. Auditors should verify that warm pool size and min/max limits are appropriate — a misconfigured warm pool can silently drain capacity budget without serving traffic.
- **Predictive scaling v2 (2024-2025):** Enhanced predictive scaling with custom metric specifications and forecast-only mode. Auditors should check whether predictive scaling is enabled for stateful ASGs with predictable traffic patterns, and whether the custom metric pair (load vs utilization) is correctly configured.
- **Capacity rebalance GA:** The skill already covers this, but note that capacity rebalance is now the recommended setting for Spot-backed ASGs — without it, Spot interruptions can cause cascading failures when replacement instances launch after the old ones are marked for termination.
