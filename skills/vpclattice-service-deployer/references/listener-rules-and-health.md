# Listener Rules and Target Group Health — VPC Lattice Deployer

Deep reference on listener rule configuration (path-based, header-based,
method-based routing, weighted forwarding for traffic splitting), target
group health checks (routing eligibility, health check parameters, failure
modes), and the three-tier Lattice model (service network → service →
target group + listener rules). Loaded on demand by the skill — kept out
of the main SKILL.md body so the provisioning procedure stays scannable.

## The three-tier Lattice model

### Hierarchy

```text
Account
  └── Service Network (account-level, 1 per account typical)
        ├── VPC Associations (which VPCs can use this network)
        ├── Service A (HTTP)
        │     ├── Listener (port 80)
        │     │     ├── Rule 1 (priority 10): path match → TG-A1
        │     │     └── Rule 2 (default):     → TG-A2
        │     ├── Target Group TG-A1 (INSTANCE)
        │     └── Target Group TG-A2 (INSTANCE)
        └── Service B (gRPC)
              └── Listener (port 443)
                    └── ...
```

Every resource hangs off the service network. The service network is
the first thing to create. VPCs are associated with it (not the other
way around). Services exist within the network. Listeners and target
groups are attached to services.

### Why the service network is account-level

The service network is the routing plane. It is NOT a VPC construct.
Multiple VPCs (including cross-account VPCs via RAM) are associated
with the same service network. This allows services in one VPC to be
reached by instances in another VPC (or another account) without VPC
peering.

## Listener rule configuration

### Rule evaluation order

Rules within a listener are evaluated in **priority order** (ascending).
The first matching rule wins. The listener's default action is the
fallback when no rule matches.

```text
Listener (port 80):
  Rule priority 10: path /v2/*           → TG-canary (20) + TG-stable (80)
  Rule priority 20: header x-env=beta    → TG-canary (100)
  Rule priority 30: method POST, /api/*  → TG-write (100)
  Default action:                        → TG-stable (100)
```

### Path-based matching

```bash
aws vpc-lattice create-rule \
  --service-identifier svc-bbb222 \
  --listener-identifier lstn-ccc333 \
  --name v2-path-rule --priority 10 \
  --match '{"httpMatch":{"path":{"prefix":"/v2"}}}' \
  --actions '[{"type":"FORWARD","forward":{"targetGroups":[{"targetGroupIdentifier":"tgc-stable","weight":100}]}}]'
```

Path match types: `exact` (exact match), `prefix` (path prefix match).

### Header-based matching

```bash
aws vpc-lattice create-rule \
  --service-identifier svc-bbb222 \
  --listener-identifier lstn-ccc333 \
  --name beta-header-rule --priority 20 \
  --match '{"httpMatch":{"headerMatches":[{"name":"x-env","match":{"exact":"beta"}}]}}' \
  --actions '[{"type":"FORWARD","forward":{"targetGroups":[{"targetGroupIdentifier":"tgc-canary","weight":100}]}}]'
```

Header match types: `exact` (exact string), `prefix` (prefix match).

### Method-based matching

```bash
aws vpc-lattice create-rule \
  --service-identifier svc-bbb222 \
  --listener-identifier lstn-ccc333 \
  --name post-api-rule --priority 30 \
  --match '{"httpMatch":{"method":"POST","path":{"prefix":"/api"}}}' \
  --actions '[{"type":"FORWARD","forward":{"targetGroups":[{"targetGroupIdentifier":"tgc-write","weight":100}]}}]'
```

Method + path can be combined in a single rule for more specific
routing.

## Weighted traffic splitting (canary)

### How weights work

Weights in a forwarding action are **relative**, not percentage. The
distribution is calculated as `weight_i / sum(weights)`.

```text
Rule: forward to TG-canary (weight 20) + TG-stable (weight 80)
  → canary gets 20/(20+80) = 20%
  → stable gets 80/(20+80) = 80%

Same split with different weights:
  TG-canary (weight 1) + TG-stable (weight 4)
  → canary gets 1/5 = 20%
  → stable gets 4/5 = 80%
```

The sum does NOT need to be 100. Lattice normalizes.

### Progressive canary deployment

```bash
# Phase 1: 5% canary
aws vpc-lattice update-rule \
  --service-identifier svc-bbb222 \
  --listener-identifier lstn-ccc333 \
  --rule-identifier rul-canary \
  --action '{"forward":{"targetGroups":[{"targetGroupIdentifier":"tgc-canary","weight":5},{"targetGroupIdentifier":"tgc-stable","weight":95}]}}'

# Phase 2: 20% canary
# ...update weights to 20 and 80...

# Phase 3: 100% canary (promote)
# ...update weights to 100 and 0 (or remove stable from the rule)...
```

### Health checks and traffic splitting

If the canary target group has unhealthy targets, Lattice routes ALL
traffic to the stable target group (healthy targets only). This is a
safety feature — unhealthy canary targets do not cause errors.

## Target group health checks

### Health check parameters

| Parameter | Default | Range | Description |
|---|---|---|---|
| enabled | true | true/false | Whether health checks are active |
| path | / | any path | Endpoint Lattice probes (e.g., /health) |
| protocol | HTTP | HTTP/HTTPS | Protocol for probe |
| intervalSeconds | 30 | 5-300 | Seconds between probes |
| timeoutSeconds | 5 | 1-60 | Seconds before probe times out |
| healthyThresholdCount | 2 | 2-10 | Consecutive successes to mark healthy |
| unhealthyThresholdCount | 2 | 2-10 | Consecutive failures to mark unhealthy |
| matcher.httpCode | 200 | any code/range | HTTP status codes that count as success |

### How health check determines routing

```text
Target Group TG-stable:
  Target 1 (i-aaa): health check /health → 200 → HEALTHY ✓
  Target 2 (i-bbb): health check /health → 500 → UNHEALTHY ✗
  Target 3 (i-ccc): health check /health → 200 → HEALTHY ✓

Traffic distribution:
  Lattice routes to Target 1 and Target 3 only.
  Target 2 receives ZERO traffic until health check passes again.

If ALL targets become UNHEALTHY:
  Lattice returns 503 (no healthy targets) to all clients.
```

### Verifying health status

```bash
# List targets and their health status
aws vpc-lattice list-targets \
  --target-group-identifier tgc-stable \
  --query 'items[*].{Target:id,Port:port,Status:status,Reason:reason}' \
  --output table

# Expected output:
# ------------------------------
# |Target       |Port|Status  |
# --------------|----|---------
# |i-aaa111     |8080|HEALTHY |
# |i-bbb222     |8080|UNHEALTHY|
# |i-ccc333     |8080|HEALTHY |
# ------------------------------
```

### Common health check failures

1. **Wrong path.** The health check path (e.g., `/health`) must return
   200. If the application serves a different health endpoint, update
   the health check path.

2. **Wrong port.** The health check probes the target's port. If the
   application listens on 8080 but the health check targets 80, probes
   fail.

3. **Matcher too strict.** If the matcher is `200` but the app returns
   `204` (no content), the health check fails. Use a range like
   `200-299`.

4. **Interval too short.** If the interval is 5s but the app takes 10s
   to respond, all probes time out. Increase the interval or timeout.

5. **Unhealthy threshold too low.** If set to 2, a transient error
   marks the target unhealthy after 2 failures. For production, consider
   3-5 consecutive failures before marking unhealthy.

## Target group types comparison

| Type | Requires VPC | Health check | Use case |
|---|---|---|---|
| INSTANCE | Yes | HTTP/HTTPS | EC2-based services |
| IP | Yes | HTTP/HTTPS | ECS awsvpc, ENI-attached |
| LAMBDA | No | Not applicable | Serverless functions |
| ALB | Yes | Inherits from ALB | ALB as Lattice upstream |

**Lambda target groups** do NOT use health checks — Lambda functions
are invoked on demand. The `lambdaEventStructureVersion` (2.0)
determines the event format passed to the function.

**ALB target groups** inherit the ALB's health check configuration.
Lattice routes to the ALB; the ALB handles its own target health.

## Terraform example

```hcl
# Service network
resource "aws_vpclattice_service_network" "main" {
  name      = "prod-network"
  auth_type = "AWS_IAM"

  tags = {
    Environment = "production"
  }
}

# Target group
resource "aws_vpclattice_target_group" "stable" {
  name = "tg-stable"
  type = "INSTANCE"

  config {
    port     = 8080
    protocol = "HTTP"
    vpc_identifier = "vpc-aaa11122"

    health_check {
      enabled                = true
      path                   = "/health"
      protocol               = "HTTP"
      interval_seconds       = 30
      timeout_seconds        = 5
      healthy_threshold_count   = 2
      unhealthy_threshold_count = 2
      matcher {
        http_code = "200"
      }
    }
  }
}

# Service
resource "aws_vpclattice_service" "payments" {
  name               = "payments-svc"
  auth_type          = "AWS_IAM"
  custom_domain_name = "payments.internal.example.com"
}

# Listener
resource "aws_vpclattice_listener" "main" {
  name               = "payments-listener"
  protocol           = "HTTP"
  port               = 80
  service_identifier = aws_vpclattice_service.payments.id

  default_action {
    forward {
      target_group {
        target_group_identifier = aws_vpclattice_target_group.stable.id
        weight                  = 100
      }
    }
  }
}

# VPC association
resource "aws_vpclattice_service_network_vpc_association" "main" {
  vpc_identifier            = "vpc-aaa11122"
  service_network_identifier = aws_vpclattice_service_network.main.id
}
```
