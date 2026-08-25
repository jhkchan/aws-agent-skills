# Advanced Patterns — Route 53 ARC Deployer

Deep-dive material moved out of the SKILL.md body so the procedure stays scannable. Loaded on demand.


## Common misconceptions (from Mindset)

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


## Configuration dependency graph (sequencing notes)

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


## Failover execution patterns (from Step 8)

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


## Recent AWS features (2023-2026)

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
