---
name: route53-application-recovery-controller-deployer
description: >-
  Provisions Route 53 Application Recovery Controller (ARC) with
  production defaults: recovery cluster (five Route 53 regional
  clusters across AWS regions for quorum), routing controls (boolean
  on/off toggles for traffic to a cell), control panels (groupings of
  routing controls), safety rules (prevent unsafe failover —
  disallow all routing controls OFF simultaneously), resource sets
  (by resource type: NLB, ASG, DynamoDB table, Aurora cluster, EC2,
  etc.), readiness checks (validate each cell has required resources
  before failover), cells (groupings of resources representing an
  application instance for failover), readiness scopes, cross-region
  readiness assessment, and CloudWatch routing control state
  monitoring. Emits a READY_TO_DEPLOY checklist with verification
  commands. Use when creating ARC readiness checks, configuring
  routing controls for failover, setting up safety rules, creating
  cells for active-active or active-standby, or building a recovery
  cluster. Triggers: route 53 arc, application recovery controller,
  routing control, safety rule, readiness check, recovery cluster,
  control panel, cell failover, resource set, readiness scope.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). For live deployment: AWS CLI v2 with
  route53-recovery-control-config, route53-recovery-readiness, and
  route53-recovery-cluster access. Works with Terraform
  aws_route53recoverycontrolconfig_* and
  aws_route53recoveryreadiness_* resources and CloudFormation
  AWS::Route53RecoveryControl::* templates.
keywords:
  - aws
  - route 53 arc
  - application recovery controller
  - routing control
  - safety rule
  - readiness check
  - recovery cluster
  - control panel
  - cell failover
  - resource set
  - cloudops
  - deploy
  - provisioning
  - disaster recovery
  - failover
tags:
  - aws
  - route-53-arc
  - application-recovery-controller
  - cloudops
  - deploy
  - networking
  - disaster-recovery
  - failover
  - routing-control
  - readiness-check
  - safety-rule
dependencies:
  - aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: Networking
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  version: 0.1.0
  author: "Jacky Chan — AWS Community Builder"
  tags:
    - aws
    - route-53-arc
    - application-recovery-controller
    - cloudops
    - deploy
    - networking
    - disaster-recovery
    - failover
    - routing-control
    - readiness-check
    - safety-rule
  dependencies:
    - aws-orchestrator
  keywords:
    - route 53 arc
    - application recovery controller
    - routing control
    - safety rule
    - readiness check
    - recovery cluster
    - control panel
    - cell failover
    - resource set
    - readiness scope
  when_to_use: >-
    Invoke when the user wants to set up Route 53 Application Recovery
    Controller for application failover orchestration — creating routing
    controls (traffic on/off switches), safety rules (prevent unsafe
    failover), readiness checks (validate cells before failover),
    resource sets, cells, control panels, or recovery clusters. Do NOT
    invoke for Route 53 health checks (use health-check skills), Route
    53 DNS failover (use dns-failover skills), or Elastic Disaster
    Recovery (use drs skills).
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

Three misconceptions dominate ARC misdesign at provisioning time:

- **"ARC is just another health check."** It is NOT. Route 53 health
  checks monitor endpoint health and shift DNS routing. ARC provides
  APPLICATION-LEVEL routing controls — explicit on/off toggles
  operated by humans or automation to fail over entire application
  stacks. Health checks react automatically; routing controls are
  deliberate traffic shifts with safety guardrails. The two
  complement each other but serve different purposes.

- **"You can toggle routing controls freely."** Not safely. Without
  safety rules, toggling all routing controls OFF simultaneously
  takes the entire application down. Safety rules enforce invariants
  like "at least one routing control must be ON" or "routing control
  A and B must not both be ON" (preventing split-brain). Every
  control panel with failover semantics MUST have at least one safety
  rule.

- **"Readiness checks are optional."** They are NOT optional for safe
  failover. Without readiness checks, you may fail over to a cell
  that is missing required resources (e.g., missing DynamoDB table,
  empty Aurora cluster, no ASG). Readiness checks validate resource
  parity across cells BEFORE failover. They are the difference
  between planned failover and blind failover.

## Configuration dependency graph (novel heuristic)

ARC configurations are NOT independent. The recovery cluster must
exist before routing controls. Routing controls must exist before
safety rules. Resource sets must exist before readiness checks. Use
this graph to sequence provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Recovery cluster | Five regional clusters auto-provisioned by AWS on cluster creation | cluster creation takes ~10-15 minutes; cannot be rushed | routing controls, control panels |
| Control panel | Recovery cluster exists | control panel is a logical grouping; no traffic impact until routing controls are toggled | routing controls |
| Routing control | Control panel exists; recovery cluster ACTIVE | routing control state is ON or OFF (boolean); toggling is atomic (takes ~10 seconds) | traffic shifting per cell |
| Safety rule | At least one routing control in the same cluster | safety rule type: AND (enforce) or OR (allow); MUST be configured before production failover | prevents unsafe toggling |
| Resource set | Resources (by ARN and type) exist in target regions | resource type must match expected template; mismatched types cause readiness check failure | readiness checks |
| Readiness check | Resource set exists; at least one resource mapped per cell | readiness check evaluates ALL cells; a single missing resource marks the cell NOT READY | pre-failover validation |
| Cell (readiness scope) | Resources grouped logically per cell | a cell is a logical grouping; readiness checks compare across cells | cross-cell comparison |

**The safety-rule-before-production row is the one a baseline model
misses.** Creating routing controls without safety rules means an
operator (or automation) can toggle all controls OFF, causing a
complete outage. Safety rules are the guardrails. The procedure below
forces an explicit safety rule for every control panel.

**Cross-dependency gotchas:**
- Routing controls are toggled via a SEPARATE API endpoint
  (`route53-recovery-cluster`) from the configuration API
  (`route53-recovery-control-config`). This is because the data plane
  (cluster) is decoupled from the control plane (config).
- Safety rules are evaluated at toggle time. If a toggle would
  violate a safety rule, the API rejects it. This is synchronous
  enforcement, not advisory.
- Readiness checks run on a schedule (every ~5 minutes) and on
  demand. A cell can become NOT READY between checks.
- Resource sets map by resource type. Each resource type has a
  different readiness template (e.g., NLB checks target health, ASG
  checks desired capacity, DynamoDB checks table exists).

## Expert heuristic: routing control as a boolean toggle

A baseline model treats routing controls as complex network routing
rules. The correct heuristic recognizes that a routing control is a
single boolean: ON (traffic flows to this cell) or OFF (traffic does
not flow to this cell).

```text
Active-Active (two cells, both serving):
  Cell-A routing control: ON  → traffic flows to Cell-A
  Cell-B routing control: ON  → traffic flows to Cell-B
  Safety rule: (A OR B must be ON) → prevents total outage

Failover (Cell-A → Cell-B):
  1. Verify Cell-B readiness check: READY
  2. Toggle Cell-B routing control: ON  (traffic now flows to BOTH)
  3. Toggle Cell-A routing control: OFF (traffic flows ONLY to Cell-B)
  Result: traffic shifted from Cell-A to Cell-B

Recovery (Cell-A → Cell-B):
  1. Toggle Cell-A routing control: OFF (immediate traffic loss)
  2. Toggle Cell-B routing control: ON  (traffic restored)
  Result: failover complete
```

**Key implication:** the routing control toggle is atomic and takes
~10 seconds. During the toggle, traffic may be in both cells or
neither cell, depending on the sequence. Safety rules prevent the
"neither cell" scenario.

## Expert heuristic: safety rule types

Safety rules come in two types: AND rules (enforce that ALL listed
routing controls are OFF — used to prevent a specific combination
from being ON) and OR rules (enforce that at least one listed
routing control is ON — used to prevent total outage).

```text
Safety rule types:

  AND rule (assertive):
    "Routing controls A, B, and C must all be OFF"
    Use case: prevent A and B from both being ON (no split-brain)
    When you try to turn A ON while B is ON → REJECTED

  OR rule (permissive):
    "At least one of routing controls A, B, C must be ON"
    Use case: prevent total outage (at least one cell serving)
    When you try to turn the last ON control OFF → REJECTED
```

**Key implication:** OR rules are the most common safety rule type.
They prevent the "all controls OFF" scenario. AND rules are used for
mutual exclusion (e.g., two cells should never serve simultaneously
for data consistency reasons).

## Expert heuristic: readiness check resource templates

Readiness checks use predefined resource-type templates. Each
template knows what "ready" means for that resource type. A baseline
model may not know which attributes are checked.

```text
Resource type → Readiness template:
  AWS::ElasticLoadBalancingV2::LoadBalancer
    → NLB/ALB: checks listener count, target health, subnet mapping
  AWS::AutoScaling::AutoScalingGroup
    → ASG: checks desired capacity, min size, instance health
  AWS::DynamoDB::Table
    → DynamoDB: checks table status (ACTIVE), provisioned throughput
  AWS::RDS::DBCluster
    → Aurora: checks cluster status (available), writer instance
  AWS::EC2::NatGateway
    → NAT GW: checks state (available), ENI attachment
  AWS::S3::Bucket
    → S3: checks bucket exists, versioning config
  AWS::Lambda::Function
    → Lambda: checks function exists, runtime configured
```

**Key implication:** resource sets must map resources by their
correct CloudFormation resource type. Mapping an ALB as
`AWS::ElasticLoadBalancingV2::LoadBalancer` is correct; mapping it
as `AWS::EC2::Instance` causes readiness check failure.

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

```text
Cell-A (us-east-1):
  NLB: arn:aws:elasticloadbalancing:us-east-1:...:loadbalancer/net/app-nlb-a/...
  ASG: arn:aws:autoscaling:us-east-1:...:autoScalingGroup:...
  DynamoDB: arn:aws:dynamodb:us-east-1:...:table/app-table

Cell-B (us-west-2):
  NLB: arn:aws:elasticloadbalancing:us-west-2:...:loadbalancer/net/app-nlb-b/...
  ASG: arn:aws:autoscaling:us-west-2:...:autoScalingGroup:...
  DynamoDB: arn:aws:dynamodb:us-west-2:...:table/app-table

Resource Set 1 (NLB):
  Type: AWS::ElasticLoadBalancingV2::LoadBalancer
  Resources: [Cell-A NLB, Cell-B NLB]

Resource Set 2 (ASG):
  Type: AWS::AutoScaling::AutoScalingGroup
  Resources: [Cell-A ASG, Cell-B ASG]

Resource Set 3 (DynamoDB):
  Type: AWS::DynamoDB::Table
  Resources: [Cell-A table, Cell-B table]
```

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

```bash
aws route53-recovery-cluster get-routing-control-state \
  --routing-control-arn "$RC_A_ARN"
# Expected: RoutingControlState: "On"
```

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

```bash
aws route53-recovery-readiness get-readiness-check \
  --readiness-check-name "app-readiness-check"

# Get readiness for a specific cell
aws route53-recovery-readiness get-cell-readiness \
  --cell-name "Cell-B"
```

**Readiness states:**

| State | Meaning |
|---|---|
| READY | All resources in the cell pass readiness checks |
| NOT_READY | At least one resource is missing or unhealthy |
| UNKNOWN | Readiness check has not run yet or has insufficient data |
| NOT_AUTHORIZED | ARC lacks IAM permission to check the resource |

**Create multiple readiness checks (one per resource set):**

```bash
for RS_NAME in app-nlb-resource-set app-asg-resource-set app-ddb-resource-set; do
  aws route53-recovery-readiness create-readiness-check \
    --readiness-check-name "${RS_NAME}-check" \
    --resource-set-name "$RS_NAME"
done
```

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

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "arc-routing-control-changed" \
  --namespace AWS/Route53RecoveryControl \
  --metric-name RoutingControlState \
  --dimensions Name=RoutingControlName,Value=cell-a-traffic \
  --statistic Maximum \
  --period 60 \
  --evaluation-periods 1 \
  --threshold 0 \
  --comparison-operator LessThanThreshold \
  --alarm-actions "arn:aws:sns:us-east-1:123456789012:arc-alerts"
```

This alarm fires when Cell-A's routing control transitions from ON
(1) to OFF (0), alerting the team of a failover event.

## Step 8 — Failover execution patterns

**Active-Standby failover (Cell-A primary, Cell-B standby):**

```text
1. Check Cell-B readiness: aws route53-recovery-readiness get-cell-readiness
   → Must be READY
2. Toggle Cell-B routing control ON:
   aws route53-recovery-cluster update-routing-control-state --state On
3. Wait for DNS propagation (~30-60 seconds for Route 53)
4. Toggle Cell-A routing control OFF:
   aws route53-recovery-cluster update-routing-control-state --state Off
   → Safety rule (OR, threshold 1) permits this because Cell-B is ON
```

**Active-Active load shifting (gradual):**

```text
1. Both cells ON (normal active-active)
2. To drain Cell-A: toggle Cell-A routing control OFF
   → All traffic shifts to Cell-B immediately
   → Safety rule (OR) ensures Cell-B remains ON
3. To restore: toggle Cell-A routing control ON
   → Traffic resumes to both cells
```

**Failback (return to Cell-A):**

```text
1. Verify Cell-A readiness: READY
2. Toggle Cell-A routing control ON (traffic to both cells)
3. Verify Cell-A is serving traffic
4. Toggle Cell-B routing control OFF (traffic only to Cell-A)
```

## Step 9 — Integration with Route 53 health checks

ARC routing controls integrate with Route 53 DNS failover via health
checks. The routing control state can be used as a health check input,
so DNS failover follows the routing control toggle.

**Create a Route 53 health check backed by a routing control:**

```bash
aws route53 create-health-check \
  --caller-reference "arc-health-check-cell-a" \
  --health-check-config '
{
  "Type": "RECOVERY_CONTROL",
  "RoutingControlArn": "'"$RC_A_ARN"'"
}'
```

When the routing control is ON, the health check returns HEALTHY.
When OFF, it returns UNHEALTHY. Associate this health check with a
Route 53 record set for automatic DNS-level failover.

## Step 10 — Recent features

**Recent AWS features (2023-2026):**

- **Routing control APIs in route53-recovery-cluster (2023-2024):**
  Enhanced data plane API stability and reduced toggle latency from
  ~15 seconds to ~10 seconds.

- **Safety rule types expansion (2023-2024):** Additional support for
  complex multi-cell safety rule compositions, including nested AND/OR
  logic for multi-region active-active topologies.

- **Readiness check new resource types (2023-2024):** Added readiness
  templates for AWS::SQS::Queue, AWS::SNS::Topic, and
  AWS::StepFunctions::StateMachine.

- **CloudWatch enhanced metrics (2023-2024):** New dimensions for
  per-control-panel and per-safety-rule metrics, enabling more
  granular alerting on ARC state.

- **Terraform provider maturity (2023-2024):** The Terraform
  aws_route53recoverycontrolconfig_* resources now support full
  control panel, routing control, and safety rule lifecycle
  management.

- **Multi-account ARC support (2024-2025):** Enhanced support for
  multi-account readiness checks, allowing resource sets to span
  AWS Organizations member accounts.

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

### Cluster stuck in CREATING
- Recovery cluster creation takes 10-15 minutes. If it exceeds 20
  minutes, check IAM permissions and service-linked role creation.
  Do not create resources until the cluster is ACTIVE.

### Routing control toggle rejected
- A safety rule is preventing the toggle. Check which safety rule is
  blocking by reviewing the rule config. For OR rules, at least one
  other control must remain ON. For AND rules, the other control
  must be OFF first.

### Readiness check returns NOT_AUTHORIZED
- ARC lacks IAM permission to access the resource. Add the
  `route53-recovery-readiness` service-linked role or grant
  cross-account read permissions for resources in other accounts.

### Resource set type mismatch
- The resource was mapped with the wrong CloudFormation type. Delete
  the resource set entry and recreate with the correct type. Verify
  the resource type matches the actual AWS resource type.

### Routing control state stuck
- The cluster may have lost quorum. Check
  `describe-cluster` for quorum status. If fewer than 3 of 5 clusters
  are available, toggles will fail. This is extremely rare and
  typically resolves automatically.

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
