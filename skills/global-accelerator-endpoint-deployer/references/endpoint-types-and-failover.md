# Endpoint Types and Failover — Global Accelerator Endpoint Deployer

Deep reference on endpoint types (ALB, NLB, EC2 IP, EIP), endpoint
weight configuration, health check customization, and endpoint group
failover strategies. Loaded on demand by the skill — kept out of the
main SKILL.md body so the provisioning procedure stays scannable.

## Endpoint type comparison

### ALB endpoints

Application Load Balancer endpoints are referenced by ARN. The ALB
must exist in the same region as the endpoint group.

```bash
aws globalaccelerator update-endpoint-group \
  --endpoint-group-arn "$EG_PRIMARY" \
  --endpoint-configurations \
    EndpointId=arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/my-alb/50dc6c495c0c9188,Weight=128
```

- Client IP preservation: Enabled by default (source IP preserved).
- Health check: Independent from the ALB's target group health checks.
- Multi-AZ: The ALB handles multi-AZ distribution; Global Accelerator
  handles multi-region distribution.

### NLB endpoints

Network Load Balancer endpoints are referenced by ARN. The NLB must
exist in the same region as the endpoint group.

```bash
aws globalaccelerator update-endpoint-group \
  --endpoint-group-arn "$EG_PRIMARY" \
  --endpoint-configurations \
    EndpointId=arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/net/my-nlb/abc123,Weight=128
```

- Client IP preservation: Enabled by default, BUT disabled if the NLB
  has TLS termination configured.
- Health check: Independent from the NLB's target group health checks.

### EC2 IP endpoints

EC2 instance endpoints are referenced by private or public IP address.
The instance must be in the same region as the endpoint group.

```bash
aws globalaccelerator update-endpoint-group \
  --endpoint-group-arn "$EG_PRIMARY" \
  --endpoint-configurations \
    EndpointId=10.0.1.10,Weight=128
```

- Client IP preservation: Enabled by default.
- Health check: Global Accelerator checks the IP directly.

### EIP endpoints

Elastic IP endpoints are referenced by allocation ID.

```bash
aws globalaccelerator update-endpoint-group \
  --endpoint-group-arn "$EG_PRIMARY" \
  --endpoint-configurations \
    EndpointId=eipalloc-abcdef1234567890,Weight=128
```

- Client IP preservation: Enabled by default.
- The EIP can be associated with any instance or NAT gateway.

## Health check customization

### Independent from target group health checks

Global Accelerator performs its own health checks on endpoints. These
are independent from ALB/NLB target group health checks. An endpoint
can be:

- Healthy at target group level, unhealthy at Global Accelerator level.
- Unhealthy at target group level, healthy at Global Accelerator level.

The Global Accelerator health check determines whether the endpoint
receives traffic from the accelerator.

### Health check parameters

| Parameter | Values | Default | Impact |
|---|---|---|---|
| Interval | 10 or 30 seconds | 30 | Shorter = faster detection |
| Protocol | TCP, HTTP, HTTPS | TCP | HTTPS recommended for TLS endpoints |
| Path | HTTP path | / | e.g., /health |
| Port | 1-65535 | Listener port | Usually matches listener port |
| Threshold | Integer | 3 | Consecutive successes/failures |

### Failover timing calculation

```text
Time to detect failure = threshold * interval
Time to recover = threshold * interval

Interval 10s, threshold 3:
  Detection: 30s, Recovery: 30s, Total failover: ~30-60s

Interval 30s, threshold 3:
  Detection: 90s, Recovery: 90s, Total failover: ~90-180s
```

## Failover strategies

### Active-passive failover

Primary region serves all traffic. DR region is standby (traffic dial
0.0). When primary endpoints fail health checks, traffic shifts to DR.

```text
Normal state:
  us-east-1: traffic dial 1.0, endpoints healthy → 100% traffic
  us-west-2: traffic dial 0.0, endpoints healthy → 0% traffic

Failover state (us-east-1 endpoints unhealthy):
  us-east-1: traffic dial 1.0, endpoints UNHEALTHY → 0% traffic
  us-west-2: traffic dial 0.0, endpoints healthy → 100% traffic
  (Global Accelerator redirects to healthy endpoints regardless of dial)

Recovery (us-east-1 endpoints healthy again):
  Traffic returns to us-east-1 automatically
```

### Active-active with weighted distribution

Both regions serve traffic simultaneously. If one fails, the other
absorbs 100%.

```text
us-east-1: traffic dial 0.5 → 50% traffic
eu-west-1: traffic dial 0.5 → 50% traffic

If eu-west-1 fails → 100% to us-east-1
If us-east-1 fails → 100% to eu-west-1
```

### Manual failover (drain and promote)

```bash
# Drain primary
aws globalaccelerator update-endpoint-group \
  --endpoint-group-arn "$EG_PRIMARY" --traffic-dial 0.0

# Promote DR
aws globalaccelerator update-endpoint-group \
  --endpoint-group-arn "$EG_DR" --traffic-dial 1.0
```

## Common endpoint pitfalls

### Pitfall 1: Wrong region for endpoint

Endpoints must be in the same region as their endpoint group. An ALB in
us-east-1 cannot be added to an endpoint group in us-west-2.

### Pitfall 2: NLB TLS disabling client IP preservation

If an NLB endpoint has TLS termination, client IP preservation is
implicitly disabled. The backend sees the NLB's internal IP instead of
the client's source IP.

### Pitfall 3: Health check protocol mismatch

Using TCP health checks for an HTTPS endpoint may report healthy even
if the application is not responding correctly. Use HTTPS health checks
with a dedicated health endpoint for application-level verification.

### Pitfall 4: Forgetting DR region health checks

In active-passive, the DR region's endpoints must be healthy for
failover to work. If DR endpoints are unhealthy, there is no failover
target. Monitor DR endpoint health continuously.
