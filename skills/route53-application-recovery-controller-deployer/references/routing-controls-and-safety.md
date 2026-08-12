# Routing Controls and Safety Rules — Route 53 ARC Deployer

Deep reference on routing control architecture (boolean toggle, cluster
data plane, config-vs-cluster API split), safety rule types (AND/OR,
threshold semantics, enforcement mechanics), and failover execution
patterns. Loaded on demand by the skill — kept out of the main SKILL.md
body so the provisioning procedure stays scannable.

## Routing control architecture

### The config vs cluster API split

ARC uses two separate API namespaces:

- **`route53-recovery-control-config`** — the control plane. Used to
  CREATE, DELETE, and DESCRIBE clusters, control panels, routing
  controls, and safety rules. Changes here are configuration, not
  runtime state.

- **`route53-recovery-cluster`** — the data plane. Used to TOGGLE
  routing control state (ON/OFF) and GET current state. This API goes
  directly to the five-cluster quorum data plane for maximum
  availability.

```text
Provisioning flow (config API):
  create-cluster → create-control-panel → create-routing-control → create-safety-rule

Runtime flow (cluster API):
  get-routing-control-state → update-routing-control-state (ON/OFF toggle)
```

**Why the split?** The config API depends on standard AWS control
plane infrastructure. The cluster API is backed by five independent
regional clusters designed for 99.999% availability. Even if the AWS
control plane is degraded, the cluster API continues to serve routing
control state. This separation ensures failover works when you need
it most — during an AWS event.

### Routing control as a boolean

Each routing control has exactly two states:

| State | Integer | Meaning |
|---|---|---|
| On | 1 | Traffic flows to this cell |
| Off | 0 | Traffic does not flow to this cell |

There are no intermediate states. The toggle is atomic — the cluster
quorum (3 of 5) agrees on the new state before returning success.
This takes ~10 seconds.

### How routing controls affect traffic

Routing controls do NOT directly route traffic. They are evaluated by:

1. **Route 53 health checks** (type `RECOVERY_CONTROL`) — the health
   check returns HEALTHY when the routing control is ON, UNHEALTHY
   when OFF. Route 53 DNS failover follows the health check status.

2. **Application-level polling** — applications can call
   `get-routing-control-state` to determine if their cell should
   serve traffic.

```text
Routing control ON  → Health check HEALTHY → DNS resolves to this cell
Routing control OFF → Health check UNHEALTHY → DNS resolves to other cell
```

## Safety rule mechanics

### OR rules (permissive — minimum ON)

An OR rule with threshold N asserts that at least N of the listed
routing controls must be ON. If a toggle would drop below N, the API
rejects it.

```json
{
  "Type": "OR",
  "Inverted": false,
  "Threshold": 1
}
```

**Semantics:** `count(ON controls in list) >= Threshold`

**Enforcement:** when you try to turn OFF a control that would make
the count drop below Threshold, the API returns:

```
An error occurred (ValidationException) when calling the
UpdateRoutingControlState operation: Safety rule <rule-name> would
be violated by this update.
```

**Common OR rules:**
- Threshold 1: at least 1 cell ON (prevent total outage)
- Threshold 2: at least 2 cells ON (active-active with minimum 2)

### AND rules (assertive — maximum ON)

An AND rule with threshold N asserts that at most N of the listed
routing controls can be ON. If a toggle would exceed N, the API
rejects it.

```json
{
  "Type": "AND",
  "Inverted": false,
  "Threshold": 1
}
```

**Semantics:** `count(ON controls in list) <= Threshold`

**Enforcement:** when you try to turn ON a control that would make
the count exceed Threshold, the API rejects the toggle.

**Common AND rules:**
- Threshold 1: at most 1 cell ON (strict active-standby, no split-brain)
- Threshold 0: all controls must be OFF (maintenance mode)

### Combining AND and OR rules

A control panel can have multiple safety rules. They are ALL enforced
simultaneously. For example:

- OR threshold 1: at least 1 cell ON (prevent outage)
- AND threshold 1: at most 1 cell ON (prevent split-brain)

Together, these enforce exactly 1 cell ON at all times. This is the
strict active-standby pattern.

### The Inverted flag

The `Inverted` flag inverts the rule evaluation. It is rarely used
but can express complex constraints:

- OR, Inverted=true, Threshold=1: at most 1 control OFF (all but one
  must be ON)
- AND, Inverted=true, Threshold=1: at least 1 control OFF

Most use cases do not need inversion. Use `Inverted: false`.

## Failover execution patterns

### Active-standby failover (Cell-A primary → Cell-B)

```bash
# 1. Verify Cell-B readiness
aws route53-recovery-readiness get-cell-readiness \
  --cell-name "Cell-B" \
  --query 'Readiness'
# Must return: "READY"

# 2. Toggle Cell-B ON (traffic to both cells briefly)
aws route53-recovery-cluster update-routing-control-state \
  --routing-control-arn "$RC_B_ARN" \
  --routing-control-state "On"

# 3. Wait for DNS propagation
sleep 60

# 4. Toggle Cell-A OFF (traffic only to Cell-B)
aws route53-recovery-cluster update-routing-control-state \
  --routing-control-arn "$RC_A_ARN" \
  --routing-control-state "Off"

# OR safety rule (threshold 1) allows this because Cell-B is ON
```

### Active-active cell drain (drain Cell-A)

```bash
# Toggle Cell-A OFF — traffic shifts entirely to Cell-B
aws route53-recovery-cluster update-routing-control-state \
  --routing-control-arn "$RC_A_ARN" \
  --routing-control-state "Off"
# OR safety rule (threshold 1) allows this because Cell-B is ON
```

### Failback (return to Cell-A)

```bash
# 1. Verify Cell-A readiness
aws route53-recovery-readiness get-cell-readiness --cell-name "Cell-A"

# 2. Toggle Cell-A ON (traffic to both)
aws route53-recovery-cluster update-routing-control-state \
  --routing-control-arn "$RC_A_ARN" --routing-control-state "On"

# 3. Toggle Cell-B OFF (traffic only to Cell-A)
aws route53-recovery-cluster update-routing-control-state \
  --routing-control-arn "$RC_B_ARN" --routing-control-state "Off"
```

## Terraform examples

```hcl
# Recovery cluster
resource "aws_route53recoverycontrolconfig_cluster" "main" {
  name = "app-recovery-cluster"
}

# Control panel
resource "aws_route53recoverycontrolconfig_control_panel" "main" {
  name        = "app-failover"
  cluster_arn = aws_route53recoverycontrolconfig_cluster.main.arn
}

# Routing controls
resource "aws_route53recoverycontrolconfig_routing_control" "cell_a" {
  name             = "cell-a-traffic"
  cluster_arn      = aws_route53recoverycontrolconfig_cluster.main.arn
  control_panel_arn = aws_route53recoverycontrolconfig_control_panel.main.arn
}

resource "aws_route53recoverycontrolconfig_routing_control" "cell_b" {
  name             = "cell-b-traffic"
  cluster_arn      = aws_route53recoverycontrolconfig_cluster.main.arn
  control_panel_arn = aws_route53recoverycontrolconfig_control_panel.main.arn
}

# Safety rule: prevent total outage (OR, threshold 1)
resource "aws_route53recoverycontrolconfig_safety_rule" "prevent_outage" {
  name              = "prevent-total-outage"
  control_panel_arn = aws_route53recoverycontrolconfig_control_panel.main.arn

  rule_config = jsonencode({
    Type      = "OR"
    Inverted  = false
    Threshold = 1
  })

  routing_controls {
    routing_control_arn = aws_route53recoverycontrolconfig_routing_control.cell_a.arn
  }

  routing_controls {
    routing_control_arn = aws_route53recoverycontrolconfig_routing_control.cell_b.arn
  }
}

# Route 53 health check backed by routing control
resource "aws_route53_health_check" "cell_a_arc" {
  type                = "RECOVERY_CONTROL"
  routing_control_arn = aws_route53recoverycontrolconfig_routing_control.cell_a.arn
}
```
