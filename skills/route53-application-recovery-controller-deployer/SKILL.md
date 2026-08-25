---
name: route53-application-recovery-controller-deployer
description: 'Provisions Route 53 Application Recovery Controller (ARC) with production defaults: recovery cluster (five Route 53 regional clusters across AWS regions for quorum), routing controls (boolean on/off toggles for traffic to a cell), control panels (groupings of routing controls), safety rules (prevent unsafe failover — disallow all routing controls OFF simultaneously), resource sets (by resource type: NLB, ASG, DynamoDB table, Aurora cluster, EC2, etc.), readiness checks (validate each cell has required resources before failover), cells (groupings of resources representing an application instance for failover), readiness scopes, cross-region readiness assessment, and CloudWatch routing control state monitoring. Emits a READY_TO_DEPLOY checklist with verification commands. Use when creating ARC readiness checks, configuring routing. Triggers: route 53 arc, application recovery controller, routing control, safety rule, readiness check, recovery cluster, control panel, cell failover, resource set, readiness...'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with route53-recovery-control-config, route53-recovery-readiness, and route53-recovery-cluster access. Works with Terraform aws_route53recoverycontrolconfig_* and aws_route53recoveryreadiness_* resources and CloudFormation AWS::Route53RecoveryControl::* templates.'
metadata:
  domain: aws-cloudops
  complexity: high
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
  tags: aws, route-53-arc, application-recovery-controller, cloudops, deploy, networking, disaster-recovery, failover, routing-control, readiness-check, safety-rule
  dependencies: aws-orchestrator
  keywords: aws, route 53 arc, application recovery controller, routing control, safety rule, readiness check, recovery cluster, control panel, cell failover, resource set, cloudops, deploy, provisioning, disaster recovery, failover
  when_to_use: Invoke when the user wants to set up Route 53 Application Recovery Controller for application failover orchestration — creating routing controls (traffic on/off switches), safety rules (prevent unsafe failover), readiness checks (validate cells before failover), resource sets, cells, control panels, or recovery clusters. Do NOT invoke for Route 53 health checks (use health-check skills), Route 53 DNS failover (use dns-failover skills), or Elastic Disaster Recovery (use drs skills).
---

# Route 53 Application Recovery Controller Deployer

An AWS CloudOps agent skill that provisions Route 53 Application
Recovery Controller (ARC) with correct defaults. The skill walks the
operator through recovery cluster topology, routing control design
(boolean toggle for traffic), safety rule construction (prevent
unsafe multi-cell failover), cell grouping, resource set creation by
resource type, readiness check configuration, and CloudWatch
monitoring of routing control state, captures topology and failover
decisions, explains why each default matters, and emits a
READY_TO_DEPLOY checklist with copy-pasteable verification commands.

## Activation keywords

route 53 ARC, application recovery controller, routing control,
safety rule, readiness check, recovery cluster, control panel, cell
failover, resource set, readiness scope.

## STRICT output contract

When this skill is invoked with an ARC provisioning request (create a
recovery cluster, routing controls, safety rules, readiness checks,
cells, resource sets, control panels, or a partial configuration),
the agent MUST respond with the READY_TO_DEPLOY checklist defined in
the "Output format" section using the literal all-caps labels
`ARC:`, `VERDICT:`, `CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do
NOT preface the checklist with prose, headings, or disclaimers — emit
the block as the first lines of the response. This contract is what
assertion-based evals and downstream provisioning pipelines rely on;
deviating from the literal labels breaks automation silently.

If any prerequisite is missing, the verdict is
`PREREQUISITES_MISSING` with a specific gap citation in the checklist
(marked `[x]`), and `READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Recovery cluster architecture | Core infrastructure |
| Step 2 — Cells and resource sets | Resource grouping |
| Step 3 — Control panels and routing controls | Traffic control |
| Step 4 — Safety rules (prevent unsafe failover) | Safety guardrails |
| Step 5 — Readiness checks | Pre-failover validation |
| Step 6 — Cross-region readiness assessment | Multi-region readiness |
| Step 7 — Routing control state and CloudWatch | Monitoring |
| Step 8 — Failover execution patterns | Operational |
| Step 9 — Integration with Route 53 health checks | DNS integration |
| Step 10 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/routing-controls-and-safety.md | Control + safety detail |
| references/readiness-and-resource-sets.md | Readiness + resource detail |

## Mindset

**One-line takeaway:** Route 53 ARC provides routing controls —
single boolean toggles that turn traffic on or off to a cell — with
safety rules that prevent unsafe failover (e.g., blocking all routing
controls from being OFF simultaneously), backed by a five-cluster
recovery control data plane that maintains quorum across AWS regions.
Readiness checks validate that a target cell has all required
resources BEFORE you fail over to it.

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#common-misconceptions-from-mindset).
> Three ARC misconceptions: just a health check, free toggling, optional readiness checks.

## Configuration dependency graph (novel heuristic)

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#configuration-dependency-graph-sequencing-notes).
> Sequencing table plus the safety-rule-before-production trap and API-split gotchas.

## Expert heuristic: routing control as a boolean toggle

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#expert-heuristic-routing-control-as-a-boolean-toggle).
> ON/OFF semantics, active-active and failover sequences, atomic ~10s toggle.

## Expert heuristic: safety rule types

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#expert-heuristic-safety-rule-types).
> AND (mutual exclusion) vs OR (minimum ON) rules with rejection semantics.

## Expert heuristic: readiness check resource templates

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#expert-heuristic-readiness-check-resource-templates).
> Per-resource-type readiness template attributes (NLB, ASG, DynamoDB, Aurora, NAT, S3, Lambda).

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Application spans 2+ regions or cells | ARC failover requires at least two cells to fail over between | Confirm multi-region or multi-cell topology |
| Resources exist in each cell | Readiness checks validate resource existence | `aws resourcegroupstaggingapi get-resources --region <region>` |
| Resource ARNs identified | Resource sets map by ARN | Collect ARNs for each resource per cell |
| Resource types identified | Readiness templates match by type | Map each resource to its CloudFormation type |
| Failover topology decided (active-active vs active-standby) | Determines routing control design | Confirm topology |
| IAM permissions for ARC APIs | Both config and cluster APIs need permissions | Verify `route53-recovery-control-config:*` and `route53-recovery-cluster:*` |
| Safety rule design decided | Prevents unsafe failover | Confirm at least one safety rule per control panel |
| Cells defined (which resources belong to which cell) | Resource grouping for failover | Confirm cell-to-resource mapping |

If any prerequisite is missing, output
`VERDICT: PREREQUISITES_MISSING` and cite the specific gap.

## Step 1 — Recovery cluster architecture

The recovery cluster is the data plane for routing controls. AWS
provisions five regional clusters across different AWS regions when
you create a recovery control configuration. These clusters maintain
quorum to ensure routing control state is consistent.

| Property | Value |
|---|---|
| Cluster count | 5 (auto-provisioned, spread across AWS regions) |
| Quorum | 3 of 5 clusters must agree for a toggle to succeed |
| Cluster creation time | ~10-15 minutes |
| Data plane API | `route53-recovery-cluster` (separate from config API) |
| Config API | `route53-recovery-control-config` |
| Availability | Designed for 99.999% availability |

**Create the recovery cluster:**

```bash
CLUSTER_ARN=$(aws route53-recovery-control-config create-cluster \
  --cluster-name "my-app-recovery-cluster" \
  --query 'Cluster.ClusterArn' --output text)

echo "Cluster ARN: $CLUSTER_ARN"
# Wait for cluster to become ACTIVE (~10-15 minutes)
aws route53-recovery-control-config describe-cluster \
  --cluster-arn "$CLUSTER_ARN" \
  --query 'Cluster.Status'
```

**The cluster ARN is required for all subsequent operations.** The
cluster provides the routing control data plane endpoints. State
toggles go through `route53-recovery-cluster` (not the config API).

## Step 2 — Cells and resource sets

A **cell** is a logical grouping of resources that represents one
complete instance of an application. A multi-region application
typically has one cell per region (Cell-A = us-east-1, Cell-B =
us-west-2).

A **resource set** groups resources by type across cells. For
example, a resource set of type `AWS::NetworkLoadBalancer::LoadBalancer`
contains the NLB ARNs from Cell-A and Cell-B.

> Moved to [references/readiness-and-resource-sets.md](references/readiness-and-resource-sets.md#cell-and-resource-set-layout-from-step-2).
> Concrete Cell-A/Cell-B to resource-set mapping example.

**Create a resource set:**

```bash
aws route53-recovery-readiness create-resource-set \
  --resource-set-name "app-nlb-resource-set" \
  --resource-set-type "AWS::ElasticLoadBalancingV2::LoadBalancer" \
  --resources \
    ResourceArn=arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/net/app-nlb-a/50dc6c495c0c9188,ReadinessScopes=Cell-A \
    ResourceArn=arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/net/app-nlb-b/60dc6c495c0c9189,ReadinessScopes=Cell-B
```

**Critical:** each resource must be tagged with its cell
(ReadinessScopes). The readiness check compares across cells using
these scopes.

## Step 3 — Control panels and routing controls

A **control panel** is a logical grouping of routing controls. A
**routing control** is a single boolean toggle (ON/OFF) that
controls traffic to a cell.

**Create a control panel:**

```bash
aws route53-recovery-control-config create-control-panel \
  --cluster-arn "$CLUSTER_ARN" \
  --control-panel-name "app-failover-control-panel"
```

**Create routing controls (one per cell):**

```bash
# Cell-A routing control
RC_A_ARN=$(aws route53-recovery-control-config create-routing-control \
  --cluster-arn "$CLUSTER_ARN" \
  --control-panel-name "app-failover-control-panel" \
  --routing-control-name "cell-a-traffic" \
  --query 'RoutingControl.RoutingControlArn' --output text)

# Cell-B routing control
RC_B_ARN=$(aws route53-recovery-control-config create-routing-control \
  --cluster-arn "$CLUSTER_ARN" \
  --control-panel-name "app-failover-control-panel" \
  --routing-control-name "cell-b-traffic" \
  --query 'RoutingControl.RoutingControlArn' --output text)
```

**Initial state:** routing controls start in the OFF position. Both
controls being OFF means no traffic. You must explicitly toggle the
active cell's control ON.

**Toggle a routing control ON (via cluster API):**

```bash
aws route53-recovery-cluster update-routing-control-state \
  --routing-control-arn "$RC_A_ARN" \
  --routing-control-state "On"
```

**Verify routing control state:**

> Moved to [references/diagnostic-commands.md](references/diagnostic-commands.md#verify-routing-control-state-step-3).
> get-routing-control-state check expecting "On".

## Step 4 — Safety rules (prevent unsafe failover)

Safety rules are the guardrails that prevent unsafe routing control
toggles. Without them, an operator or automation can turn all
controls OFF, causing a complete outage.

**Create an OR safety rule (at least one cell must be ON):**

```bash
aws route53-recovery-control-config create-safety-rule \
  --control-panel-arn "$CONTROL_PANEL_ARN" \
  --safety-rule-name "prevent-total-outage" \
  --rule-config '{"Type":"OR","Inverted":false,"Threshold":1}' \
  --routing-controls-arns "$RC_A_ARN" "$RC_B_ARN"
```

This rule means: at least 1 of the 2 listed routing controls must be
ON at all times. If you try to turn the last ON control OFF, the API
rejects the request.

**Create an AND safety rule (mutual exclusion):**

```bash
aws route53-recovery-control-config create-safety-rule \
  --control-panel-arn "$CONTROL_PANEL_ARN" \
  --safety-rule-name "prevent-split-brain" \
  --rule-config '{"Type":"AND","Inverted":false,"Threshold":1}' \
  --routing-controls-arns "$RC_A_ARN" "$RC_B_ARN"
```

This rule (Type AND, Threshold 1) means: at most 1 of the 2 listed
routing controls can be ON. If you try to turn the second control ON
while the first is already ON, the API rejects the request.

**Safety rule semantics:**

| Rule Type | Threshold | Meaning | Use case |
|---|---|---|---|
| OR | 1 | At least 1 control must be ON | Prevent total outage |
| AND | 1 | At most 1 control can be ON | Prevent split-brain (active-standby) |
| OR | N | At least N controls must be ON | Multi-cell minimum serving |

**Critical:** every control panel with production traffic MUST have
at least one safety rule. A control panel without safety rules is
an accident waiting to happen.

## Step 5 — Readiness checks

Readiness checks validate that each cell has the required resources
before failover. They run on a schedule (~5 minutes) and on demand.

**Create a readiness check:**

```bash
aws route53-recovery-readiness create-readiness-check \
  --readiness-check-name "app-readiness-check" \
  --resource-set-name "app-nlb-resource-set"
```

**Get readiness status:**

> Moved to [references/diagnostic-commands.md](references/diagnostic-commands.md#get-readiness-status-step-5).
> get-readiness-check and get-cell-readiness commands.

**Readiness states:**

| State | Meaning |
|---|---|
| READY | All resources in the cell pass readiness checks |
| NOT_READY | At least one resource is missing or unhealthy |
| UNKNOWN | Readiness check has not run yet or has insufficient data |
| NOT_AUTHORIZED | ARC lacks IAM permission to check the resource |

**Create multiple readiness checks (one per resource set):**

> Moved to [references/diagnostic-commands.md](references/diagnostic-commands.md#create-multiple-readiness-checks-one-per-resource-set-step-5).
> Bash loop creating one readiness check per resource set.

## Step 6 — Cross-region readiness assessment

Cross-region readiness assesses the readiness of ALL cells
simultaneously. It is the aggregate view used before failover.

```bash
# Get overall readiness across all cells
aws route53-recovery-readiness get-recovery-group-readiness-summary \
  --recovery-group-name "app-recovery-group"
```

**Creating a recovery group (groups multiple readiness checks):**

```bash
aws route53-recovery-readiness create-recovery-group \
  --recovery-group-name "app-recovery-group" \
  --cells Cell-A Cell-B
```

**Before failover, ALWAYS check cross-cell readiness:**

```bash
# Check if Cell-B is READY before failing over from Cell-A
aws route53-recovery-readiness get-cell-readiness \
  --cell-name "Cell-B" \
  --query 'Readiness'
# Expected: READY
```

If Cell-B is NOT_READY, DO NOT fail over. Fix the missing resource
first.

## Step 7 — Routing control state and CloudWatch

Routing control state changes are emitted to CloudWatch. This enables
alerting on failover events and monitoring control state.

**CloudWatch metrics for ARC:**

| Metric | Namespace | Description |
|---|---|---|
| RoutingControlState | AWS/Route53RecoveryControl | Current state (1=ON, 0=OFF) |
| SafetyRuleAssertions | AWS/Route53RecoveryControl | Safety rule evaluation count |
| ClusterQuorumStatus | AWS/Route53RecoveryControl | Quorum health (1=healthy) |

**Create a CloudWatch alarm for routing control state change:**

> Moved to [references/diagnostic-commands.md](references/diagnostic-commands.md#create-a-cloudwatch-alarm-for-routing-control-state-change-step-7).
> put-metric-alarm firing when a routing control flips ON to OFF.

## Step 8 — Failover execution patterns

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#failover-execution-patterns-from-step-8).
> Active-standby failover, active-active drain, and failback toggle sequences.

## Step 9 — Integration with Route 53 health checks

ARC routing controls integrate with Route 53 DNS failover via health
checks. The routing control state can be used as a health check input,
so DNS failover follows the routing control toggle.

**Create a Route 53 health check backed by a routing control:**

> Moved to [references/routing-controls-and-safety.md](references/routing-controls-and-safety.md#route-53-health-check-creation-from-step-9).
> create-health-check with Type RECOVERY_CONTROL backed by a routing control.

## Step 10 — Recent features

**Recent AWS features (2023-2026):**

> Moved to [references/advanced-patterns.md](references/advanced-patterns.md#recent-aws-features-2023-2026).
> Cluster API latency, safety-rule compositions, new readiness types, metrics, Terraform, multi-account.

## NEVER do these things

1. **NEVER deploy routing controls without safety rules.** Safety
   rules prevent unsafe toggling. Without them, an operator can turn
   all controls OFF simultaneously, causing a complete outage. Every
   control panel MUST have at least one OR safety rule.

2. **NEVER fail over to a cell without checking readiness first.**
   Failing over to a NOT_READY cell means routing traffic to a cell
   with missing or unhealthy resources. Always check
   `get-cell-readiness` before toggling.

3. **NEVER confuse the config API with the cluster API.** Routing
   controls are CREATED via `route53-recovery-control-config` but
   TOGGLED via `route53-recovery-cluster`. The config API cannot
   change control state.

4. **NEVER map resources to the wrong resource type in a resource
   set.** Readiness checks use resource-type-specific templates. An
   ALB mapped as `AWS::EC2::Instance` will fail readiness checks
   silently.

5. **NEVER assume routing control toggle is instantaneous.** Toggle
   takes ~10 seconds for quorum agreement. During this time, the old
   state is still effective. Plan for the propagation delay.

6. **NEVER create a single-cell ARC setup.** ARC requires at least
   two cells for failover. A single cell has nothing to fail over
   to. Use health checks for single-cell monitoring instead.

7. **NEVER forget IAM permissions for both APIs.** The config API
   needs `route53-recovery-control-config:*` and
   `route53-recovery-readiness:*`. The cluster API needs
   `route53-recovery-cluster:*`. Missing either set breaks
   provisioning or toggling.

8. **NEVER use AND safety rules for active-active.** AND rules limit
   to one control ON at a time (active-standby). For active-active,
   use OR rules that enforce a minimum number of cells ON, not a
   maximum.

9. **NEVER skip the recovery group creation.** Recovery groups
   aggregate multiple readiness checks into a single readiness view.
   Without a recovery group, you must check each readiness check
   individually, increasing the risk of missing one.

10. **NEVER assume readiness checks are real-time.** Readiness checks
    run on a ~5-minute schedule. A cell can become NOT_READY between
    checks. Always run `get-cell-readiness` on demand before
    failover.

## Output format

```text
ARC: <cluster-name> (<cluster-arn>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Recovery cluster: <cluster-name> — ACTIVE
  [✓|✗] Cells: Cell-A (<region>), Cell-B (<region>)
  [✓|✗] Resource sets: <list of resource sets with types>
  [✓|✗] Control panel: <panel-name>
  [✓|✗] Routing controls: cell-a-traffic (<arn>), cell-b-traffic (<arn>)
  [✓|✗] Safety rule: <rule-name> (OR, threshold <n>) — prevents total outage
  [✓|✗] Readiness checks: <list of readiness checks>
  [✓|✗] Cross-region readiness: <READY | NOT_READY>
  [✓|✗] Topology: Active-Active | Active-Standby
  [✓|✗] CloudWatch alarm: <alarm-name> for routing control state
  [✓|✗] Route 53 health check integration: <health-check-id>
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws route53-recovery-control-config describe-cluster --cluster-arn <cluster-arn>
  aws route53-recovery-cluster get-routing-control-state --routing-control-arn <rc-arn>
  aws route53-recovery-readiness get-cell-readiness --cell-name Cell-B
```

### Worked example — active-standby with safety rule

```text
ARC: app-recovery-cluster (arn:aws:route53-recovery-control-config:us-east-1:123456789012:cluster/abc123)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Recovery cluster: app-recovery-cluster — ACTIVE
  [✓] Cells: Cell-A (us-east-1), Cell-B (us-west-2)
  [✓] Resource sets: app-nlb (AWS::ElasticLoadBalancingV2::LoadBalancer), app-asg (AWS::AutoScaling::AutoScalingGroup)
  [✓] Control panel: app-failover-control-panel
  [✓] Routing controls: cell-a-traffic (arn:...:routingcontrol/a-111), cell-b-traffic (arn:...:routingcontrol/b-222)
  [✓] Safety rule: prevent-total-outage (OR, threshold 1) — prevents total outage
  [✓] Readiness checks: app-nlb-check, app-asg-check
  [✓] Cross-region readiness: READY
  [✓] Topology: Active-Standby (Cell-A primary)
  [✓] CloudWatch alarm: arc-routing-control-changed for cell-a-traffic
  [✓] Route 53 health check integration: hcc-abc123 (RECOVERY_CONTROL type)
  [✓] Tags: Environment=production, Application=app
VERIFICATION_COMMANDS:
  aws route53-recovery-control-config describe-cluster --cluster-arn arn:aws:route53-recovery-control-config:us-east-1:123456789012:cluster/abc123
  aws route53-recovery-cluster get-routing-control-state --routing-control-arn arn:aws:route53-recovery-control-config:us-east-1:123456789012:controlpanel/xyz/routingcontrol/a-111
  aws route53-recovery-readiness get-cell-readiness --cell-name Cell-B
```

## Error handling

> Moved to [references/error-handling.md](references/error-handling.md#error-handling).
> Cluster stuck CREATING, toggle rejected, NOT_AUTHORIZED, type mismatch, stuck state.

## References (load on demand)

- [advanced-patterns](references/advanced-patterns.md) — misconceptions, dependency graph, expert heuristics, failover patterns, recent features
- [diagnostic-commands](references/diagnostic-commands.md) — routing-control state, readiness status, CloudWatch alarm commands
- [error-handling](references/error-handling.md) — symptom-by-symptom troubleshooting
- [routing-controls-and-safety](references/routing-controls-and-safety.md) — control, safety-rule, and health-check detail (existing)
- [readiness-and-resource-sets](references/readiness-and-resource-sets.md) — readiness + resource-set detail (existing)

## Domain

AWS CloudOps / Route 53 Application Recovery Controller Provisioning
& Disaster Recovery Failover Orchestration.

## AWS documentation

- **ARC Overview** — https://docs.aws.amazon.com/route53/latest/ARCGuide/what-is-ARC.html
- **Routing controls** — https://docs.aws.amazon.com/route53/latest/ARCGuide/routing-control.html
- **Safety rules** — https://docs.aws.amazon.com/route53/latest/ARCGuide/safety-rules.html
- **Readiness checks** — https://docs.aws.amazon.com/route53/latest/ARCGuide/readiness-check.html
- **Recovery clusters** — https://docs.aws.amazon.com/route53/latest/ARCGuide/recovery-cluster.html
- **ARC CLI reference** — https://docs.aws.amazon.com/cli/latest/reference/route53-recovery-control-config/
- **ARC cluster CLI** — https://docs.aws.amazon.com/cli/latest/reference/route53-recovery-cluster/
- **ARC readiness CLI** — https://docs.aws.amazon.com/cli/latest/reference/route53-recovery-readiness/
