# Advanced Patterns — Route 53 Health Check Troubleshooter

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Philosophy — four senior Route 53 behaviours

Four behaviours separate a senior Route 53 engineer from a generalist:

- **The health check status drives the diagnostic order.** An
  `Unhealthy` status with the endpoint reachable from the VPC means
  the health checker cannot reach the endpoint — that is a network
  visibility or protocol mismatch problem, not an application problem.
  A `Healthy` status with traffic still failing over means the routing
  policy or DNS TTL is the problem.

- **Health checker IPs are external and must be allowed inbound.**
  Route 53 health checkers probe from 15+ AWS regions using publicly
  routed IPs. An endpoint behind a security group or firewall that
  does not allow the Route 53 health checker IP ranges
  (`aws route53 get-health-check` provides the caller IPs) will fail
  every probe. This is the #1 cause of "endpoint works from VPC but
  health check is unhealthy."

- **Calculated health checks apply boolean logic but operators
  frequently invert AND/OR.** A calculated health check with
  `Type: CALCULATED` and `Inverted: false` using `AND` logic reports
  healthy only when ALL child checks are healthy. `OR` logic reports
  healthy when ANY child is healthy. `NOT` inverts a single child.
  Operators who expect "healthy if any child is healthy" but configure
  `AND` see failover trigger when only one region is down — the
  opposite of what they intended.

- **DNS TTL is the dominant factor in failover speed, not the health
  check interval.** The health check interval determines how quickly
  Route 53 detects a failure. The DNS TTL determines how quickly
  clients stop using the old record. A health check with
  `RequestInterval: 10` and `FailureThreshold: 3` detects failure in
  30 seconds, but a record with TTL 300 means clients may continue
  hitting the dead endpoint for 5 more minutes.

## Step 0: Non-obvious behaviours that change diagnosis

- **Route 53 health checkers are external to your VPC.** They probe
  from 15+ AWS regions using publicly routed IPs. An endpoint on a
  private subnet (10.x.x.x) without a public IP or a Route 53
  resolver inbound endpoint is unreachable by health checkers. Use
  the health check's `IPAddress` with a public ENI, or use a domain
  name that resolves to a public IP.

- **HTTPS health checks validate the TLS certificate against the
  FQDN.** If the endpoint serves a certificate for `api.example.com`
  but the health check FQDN is `health.example.com`, the health check
  fails with a certificate name mismatch. EnableSNI must be true when
  the endpoint uses SNI-based virtual hosting.

- **`FailureThreshold` is the number of consecutive failures, not
  total failures.** With `FailureThreshold: 3` and
  `RequestInterval: 30`, the health check flips to unhealthy after 3
  CONSECUTIVE failures (90 seconds). A single success between failures
  resets the counter. Operators who "see 5 failures in the logs but
  the health check is still healthy" may be seeing non-consecutive
  failures with intermittent successes resetting the count.

- **Calculated health check `Inverted` flag flips the logic.** A
  calculated check with `Inverted: true` reports healthy when the
  underlying expression is FALSE. Accidental inversion causes the
  opposite of the expected behaviour.

- **DNS TTL caches stale records on resolvers worldwide.** Even after
  Route 53 flips the record, recursive DNS resolvers cache the old
  answer for up to the TTL. A TTL of 300 means some clients may use
  the old record for 5 minutes. The only way to force faster failover
  is to lower the TTL before a failover event.

- **`RequestInterval` has two tiers: 30s (standard) and 10s (fast).** Fast detects in ~30s (3×10s); standard in ~90s (3×30s). Fast costs more.

- **Weighted routing failover requires explicit health check
  association per record.** Without a `HealthCheckId`, Route 53 serves
  the record regardless of endpoint health.

- **Latency-based and geolocation routing policies evaluate the DNS
  resolver's location, not the client's location.** A client in London
  using a DNS resolver in New York gets the latency/geolocation record
  for New York. This causes apparent "wrong routing" when clients use
  public resolvers like 8.8.8.8.

- **CloudWatch alarm-based health checks flip on ALARM state only.**
  The alarm must be in `ALARM` state (not `INSUFFICIENT_DATA` or `OK`)
  for the health check to report unhealthy. Low traffic alarms may
  stay in `INSUFFICIENT_DATA`, never triggering failover.

- **NS delegation propagation can take up to 48 hours.** If the hosted zone NS records were recently changed, recursive resolvers worldwide may still cache the old NS records. Use `dig NS <domain>` against multiple public resolvers to check propagation status.

## Expert heuristics — detail

### Heuristic 1: Health check caller IP visibility

Route 53 health checkers run from 15+ AWS regions using publicly routed
IPs — they are NOT inside your VPC. An endpoint on a private subnet
(10.x.x.x) is unreachable unless: (a) it has a public IP, (b) a NAT
Gateway or public ALB fronts it, or (c) a Route 53 Resolver inbound
endpoint is configured. Always verify the SG/firewall allows the Route
53 health checker IP ranges. If ALL regions report unhealthy in
`get-health-check-status`, the endpoint is genuinely unreachable from
health checkers. If only SOME regions report unhealthy, it's a
geographic network issue.

### Heuristic 2: Failure threshold math (consecutive failures)

`FailureThreshold: N` means N CONSECUTIVE failures are required to flip
to unhealthy — a single success resets the counter. Total detection
time = `RequestInterval` × `FailureThreshold`. Standard (30s × 3 = 90s),
fast (10s × 3 = 30s), aggressive (10s × 1 = 10s, high flapping risk).
The total client-perceived failover time = detection time + DNS TTL:
standard HC (90s) + TTL 300s = up to 390s (6.5 min); fast HC (30s) +
TTL 60s = up to 90s (1.5 min). Always calculate and communicate the
expected failover time to the operator.

### Heuristic 3: DNS TTL vs failover speed trade-off

TTL determines how long recursive resolvers cache the old record —
Route 53 cannot force resolvers to flush their cache. Low TTL (60s) =
faster failover but higher Route 53 query cost. High TTL (3600s) =
lower cost but up to 1 hour of stale records. For failover-critical
records, 60 seconds is the practical minimum; below 60 seconds some
resolvers use their own minimum. Pre-warming: lower the TTL several
hours BEFORE a planned failover so resolvers pick up the new TTL.

## Configuration dependency graph

```
DNS Client Query
    │
    ▼
┌────────────────────────────────────────┐
│ Recursive DNS Resolver (TTL-cached)    │── Step 6: DNS_RESOLUTION
│   │                                    │
│   ▼                                    │
│ Authoritative NS (zone delegation)     │── Step 9: NS_DELEGATION
│   │                                    │
│   ▼                                    │
│ Routing Policy Evaluation              │── Step 5: DNS_FAILOVER_ROUTING
│  ┌─ FAILOVER / WEIGHTED ─┐             │
│  ├─ LATENCY / GEOLOCATION┤             │
│  └───────────────────────┘             │
│   │                                    │
│   ▼                                    │
│ Health Check Evaluation                │── Step 2: ENDPOINT_HEALTH
│  ┌─ Endpoint HTTP/HTTPS/TCP ─────────┐ │   Step 3: CERTIFICATE_MISMATCH
│  │   (cert, port, path, SG)           │ │── Step 7: HC_REGION_SELECTION
│  ├─ Calculated (AND/OR/NOT) ─────────┤ │── Step 4: CALCULATED_HC_LOGIC
│  ├─ CloudWatch Alarm ────────────────┤ │── Step 8: ALARM_BASED_HC
│  └─ Interval/Threshold ──────────────┘ │── Step 0: HC_INTERVAL_THRESHOLD
│   │                                    │
│   ▼                                    │
│ Record Served (healthy/unhealthy+TTL)  │
└────────────────────────────────────────┘
```
