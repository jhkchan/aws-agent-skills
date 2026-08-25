# Advanced Patterns — Route 53 Routing Policy Deployer

Expert heuristics and recent AWS features moved verbatim from SKILL.md. Loaded on demand.

## Expert heuristic: the weighted-without-health-check myth

The most common misconception: "weighted routing distributes traffic
across healthy targets." It does not, by itself.

```text
Operator thinks:                  What actually happens:
Two weighted records 90/10,       Weighted returns record A 90% of the
target A up, target B down.       time and B 10% of the time regardless
Traffic: 90/10 healthy.           of health. 10% of clients get a dead
                                  IP. No alarm. No failover.
```

Weighted routing is a deterministic distribution by weight, evaluated
per DNS query, with NO awareness of target health unless you (a)
attach a health check to EACH weighted record and (b) the records'
`HealthCheckId` is set. When the HC is unhealthy, Route 53 omits that
record from the weighted distribution and re-normalizes the remaining
weights. Without the HC, the dead target keeps receiving its share.

This applies equally to latency, multivalue answer, and geoproximity:
the policy itself does not check target health. The remedy is one HC
per record, with `get-health-check-status` verification in Step 8.

## Expert heuristic: TTL and routing-policy interaction

TTL is the resolver cache duration. The interaction with routing
policy is not obvious:

- **Simple routing**: TTL = stability. 300s is the production default.
  A 60s TTL on simple is wasted (the target doesn't change).
- **Weighted routing**: TTL = canary granularity. A 300s TTL means a
  resolver caches one branch of the split for 5 minutes, so a 10%
  canary is "10% of resolvers for 5 minutes," not "10% of queries."
  Use 60s for canaries, 300s for stable weighted.
- **Failover routing**: TTL = failover speed. The PRIMARY record's TTL
  is how long a resolver caches the primary IP after the PRIMARY HC
  flips unhealthy. 60s is the production default for fast failover.
  300s means up to 5 minutes of continued traffic to a dead primary.
- **Latency / geolocation**: TTL = stability of the regional decision.
  300s is standard; clients rarely change region within 5 minutes.
- **Multivalue answer**: TTL = how long a dead IP stays in client
  rotation. 30-60s is typical; longer TTLs defeat multivalue's
  built-in retry.

The wrong TTL produces "feels broken" routing without any error. The
procedure below applies the policy-appropriate TTL by default.

## Expert heuristic: Application Recovery Controller safety rules

ARC routing controls are boolean on/off switches for a region's traffic
— a sub-second DR cutover primitive. The danger is symmetric: flipping
the wrong control off is a full region outage, and there is no DNS TTL
to slow it down.

**Three safety invariants before any production ARC deployment:**

1. **Safety rule (mandatory):** a logical AND/OR rule that blocks
   "all controls off" — e.g., "us-east-1-routing-control OR
   us-west-2-routing-control must be ON." Without this, an operator
   flipping both off takes the entire workload down with no DNS
   recourse. The safety rule is the single most important ARC
   configuration.
2. **Readiness check on the standby:** before flipping routing to the
   secondary, a readiness check confirms the secondary has capacity,
   scaled instances, and a healthy dependency tree. Cutover without
   readiness = overload the secondary, secondary fails, total outage.
3. **Acknowledged alarm on every control:** every flip should emit a
   CloudWatch alarm and an SNS notification. ARC flips are rare and
   high-impact; an alarm is cheap insurance against silent flips.

## Recent AWS features

- **IP-based routing (CIDR routing):** route based on the client's
  EDNS-client-subnet CIDR block. Overlapping CIDRs evaluate in
  document order — first match wins. Use for fine-grained traffic
  engineering (e.g., direct known office ranges to a specific origin).
- **CidrRoutingConfig in alias records:** IP-based routing is now
  compatible with alias targets, expanding the routing matrix.
- **Route 53 Application Recovery Controller improvements:** safety
  rules support AND/OR; readiness checks now support Lambda and
  DynamoDB resource types; routing-control state changes are now
  auditable via CloudTrail with the `route53-recovery-cluster`
  service prefix.
- **Traffic policy versioning:** max versions per policy raised to
  1000; `update-traffic-policy-instance` is the only way to move an
  instance to a new version (the instance does not auto-track).
- **Health check Lambda-based:** Route 53 can now use a CloudWatch
  alarm backed by a Lambda as a health check, enabling checks of
  private-VPC endpoints that Route 53's public checkers cannot reach.
- **Geolocation subdivision granularity:** added support for more
  ISO 3166-2 subdivisions; verify coverage in the AWS Region Table
  before relying on a specific subdivision code.
