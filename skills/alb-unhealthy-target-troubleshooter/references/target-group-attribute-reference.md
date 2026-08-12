# ALB Target Group Attribute Reference Guide

Supplementary reference for the ALB Unhealthy Target Troubleshooter skill.
Loaded on-demand when a diagnostic needs target group attribute details,
health check parameter ranges, target type differences, or listener
protocol compatibility.

## Health check parameter defaults and ranges

| Parameter | Default | Range | Notes |
|---|---|---|---|
| `HealthCheckIntervalSeconds` | 30 | 5-300 | Lower = faster detection but more load on the target |
| `HealthCheckTimeoutSeconds` | 5 | 2-60 | Must be strictly less than `HealthCheckIntervalSeconds` |
| `HealthyThresholdCount` | 5 | 2-10 | Consecutive successes required to mark a target healthy |
| `UnhealthyThresholdCount` | 2 | 2-10 | Consecutive failures required to mark a target unhealthy |
| `HealthCheckPath` | `/` | 1-1024 chars | Case-sensitive; must start with `/` |
| `HealthCheckPort` | `traffic-port` | `traffic-port` or 1-65535 | Overrides the target's registered port for health checks only |
| `HealthCheckProtocol` | `HTTP` | `HTTP` / `HTTPS` | HTTPS does not validate the target certificate |
| `Matcher.HttpCode` | `200` | `200`-`599`, comma-separated | E.g., `200,204` to accept both; `200-299` for range |

### Health check timing calculation

A target that just failed transitions to unhealthy after:
`UnhealthyThresholdCount * HealthCheckIntervalSeconds`

A target recovering transitions to healthy after:
`HealthyThresholdCount * HealthCheckIntervalSeconds`

Example with defaults (interval 30s, unhealthy 2, healthy 5):
- Time to unhealthy: 2 * 30 = 60 seconds
- Time to healthy: 5 * 30 = 150 seconds (2.5 minutes)

## Target group attributes

| Attribute | Default | Range | Effect |
|---|---|---|---|
| `deregistration_delay.timeout_seconds` | 300 | 0-3600 | Time to drain in-flight requests after deregistration |
| `stickiness.enabled` | false | true/false | Pin clients to targets via cookie |
| `stickiness.type` | lb_cookie | lb_cookie / app_cookie | Cookie mechanism |
| `stickiness.duration_seconds` | 86400 | 1-604800 | Cookie lifetime (lb_cookie type) |
| `stickiness.app_cookie.cookie_name` | (none) | string | Required for app_cookie type |
| `load_balancing.algorithm.type` | round_robin | round_robin / least_outstanding_requests | Load distribution algorithm |
| `load_balancing.algorithm.request_count` | (none) | integer | TCP-idle timeout for least_outstanding_requests |
| `slow_start.duration_seconds` | 0 | 0, 30-900 | Ramp-up time for new healthy targets (instance and IP only) |
| `proxy_protocol_v2.enabled` | false | true/false | PROXY protocol v2 header prepended to traffic |
| `preserve_client_ip.enabled` | false | true/false | Target sees client IP instead of ALB IP |
| `target.group_health.dns_failover.healthy_threshold` | 3 | 2-10 | Healthy host threshold for DNS failover |
| `target.group_health.unhealthy_state_code` | (none) | HTTP code | Code returned when all targets unhealthy |

### Deregistration delay semantics

When a target is deregistered:
1. The target immediately enters `draining` state.
2. In-flight requests are allowed to complete (up to the delay timeout).
3. New requests are not sent to the draining target.
4. After `deregistration_delay.timeout_seconds`, the target is removed.

Setting the delay to 0 means the target is removed immediately upon
deregistration, which drops all in-flight requests. This is appropriate
only for non-critical, idempotent workloads.

### Slow start mode semantics

When `slow_start.duration_seconds` is set (ALB, instance/IP targets only):
1. A newly-healthy target enters the slow-start ramp.
2. The ALB sends a small fraction of traffic initially.
3. Traffic increases linearly over the configured duration.
4. After the duration, the target receives its full share.

During slow start, the target shows state `healthy` but receives less
traffic than established targets. This is normal, not a routing issue.

Slow start is NOT available for Lambda target groups.

### Proxy protocol v2

When `proxy_protocol_v2.enabled` is true:
- The ALB prepends a PROXY protocol v2 binary header to each connection.
- The target application MUST be configured to parse PROXY protocol.
- Common applications with PROXY protocol support: NGINX (with
  `proxy_protocol` directive), HAProxy, Envoy.
- If the target does not parse the header, it receives garbled data and
  health checks fail.

### Preserve client IP

When `preserve_client_ip.enabled` is true:
- The target sees the client's real IP address in connections (not the
  ALB's private IP).
- The target SG must allow inbound from the CLIENT CIDR range, not just
  the ALB SG.
- This affects connection tracking and can increase connection counts.
- Not supported for Lambda target groups.

## TargetType differences

| TargetType | Health check mechanism | Slow start | Stickiness | Notes |
|---|---|---|---|---|
| `instance` | TCP + HTTP/HTTPS probe to HealthCheckPort | Yes | Yes | EC2 instances; health check port configurable |
| `ip` | TCP + HTTP/HTTPS probe to HealthCheckPort | Yes | Yes | IP addresses; supports targets outside the VPC (peered VPC, on-prem) |
| `lambda` | Synchronous Lambda invoke with GET request | No | No (sticky sessions not supported) | No health check path/port; function must return 200 |
| `alb` | Cascaded via nested target group | No | No | Target group as a target (weighted routing); health delegates |

## Cross-zone load balancing

| Setting | Effect |
|---|---|
| `load_balancing.cross_zone.enabled = true` (default) | Each ALB node distributes traffic across all registered targets in all AZs |
| `load_balancing.cross_zone.enabled = false` | Each ALB node only sends traffic to targets in its own AZ |

When cross-zone is disabled and a target group has targets in an AZ
without an ALB node, those targets show as `unused`.

## Listener protocol compatibility matrix

| Listener Protocol | TG Protocol | TLS Termination | Notes |
|---|---|---|---|
| HTTP | HTTP | None | Plain text end-to-end |
| HTTPS | HTTP | At ALB | ALB terminates TLS; target receives HTTP |
| HTTPS | HTTPS | End-to-end | ALB terminates and re-encrypts; ALB does NOT verify target cert |

The ALB always communicates with targets using HTTP/1.1. Targets that
only support HTTP/1.0 or HTTP/2 (without HTTP/1.1 fallback) will fail
health checks.

## ECS health check grace period

For ECS services using an ALB:

```bash
aws ecs describe-services \
  --cluster <cluster> --services <service> --output json | \
  jq '.services[].healthCheckGracePeriodSeconds'
```

During the grace period, ECS ignores ELB health check failures for
newly started tasks. If the grace period is too short, tasks are killed
before the application finishes starting. If too long, genuinely broken
tasks persist.

Typical values: 30-300 seconds, depending on application startup time.

## AWS CLI quick reference

```bash
# Modify health check configuration
aws elbv2 modify-target-group \
  --target-group-arn <arn> \
  --health-check-path /healthz \
  --health-check-port 8080 \
  --health-check-protocol HTTP \
  --health-check-interval-seconds 30 \
  --health-check-timeout-seconds 5 \
  --healthy-threshold-count 3 \
  --unhealthy-threshold-count 3 \
  --matcher HttpCode=200,204

# Modify target group attributes
aws elbv2 modify-target-group-attributes \
  --target-group-arn <arn> \
  --attributes \
    Key=deregistration_delay.timeout_seconds,Value=60 \
    Key=slow_start.duration_seconds,Value=60 \
    Key=stickiness.enabled,Value=true \
    Key=stickiness.type,Value=lb_cookie \
    Key=stickiness.duration_seconds,Value=3600

# Modify cross-zone on the ALB
aws elbv2 modify-load-balancer-attributes \
  --load-balancer-arn <alb-arn> \
  --attributes Key=load_balancing.cross_zone.enabled,Value=true

# Add SG ingress for ALB health checker
aws ec2 authorize-security-group-ingress \
  --group-id <target-sg> \
  --ip-permissions \
    IpProtocol=tcp,FromPort=<port>,ToPort=<port>,UserIdGroupPairs=[{GroupId=<alb-sg>}]
```
