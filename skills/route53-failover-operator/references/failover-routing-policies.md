# Route 53 Failover Routing Policies Reference

Load this reference when planning or executing a failover. The sections
below cover the five routing policies used for failover, the planned
vs emergency vs failback sequences, and the TTL strategy for each.

## Failover routing (PRIMARY / SECONDARY)

The simplest DR shape. Two records share the same Name + Type but have
different `SetIdentifier`, `Failover` values, and IPs.

```json
[
  {
    "Name": "api.example.com.",
    "Type": "A",
    "SetIdentifier": "primary",
    "Failover": "PRIMARY",
    "TTL": 60,
    "ResourceRecords": [{"Value": "10.0.0.10"}],
    "HealthCheckId": "h-primary"
  },
  {
    "Name": "api.example.com.",
    "Type": "A",
    "SetIdentifier": "secondary",
    "Failover": "SECONDARY",
    "TTL": 60,
    "ResourceRecords": [{"Value": "10.0.1.10"}]
  }
]
```

**Behavior:** Route 53 returns the PRIMARY IP when its health check is
`Healthy`; otherwise the SECONDARY IP. Binary — no gradient.

**Caveat:** if BOTH records are unhealthy (SECONDARY has a health
check too), Route 53 returns BOTH IPs as a last resort. This is why
the pre-check "secondary reachable" matters.

**Swap operation (planned failover):** to make the old secondary the
new primary and vice versa, UPSERT both records in the same change-
batch with the IPs and HealthCheckIds swapped.

## Weighted routing (100/0 -> 0/100)

The right tool for planned failovers that may need to pause or roll
back. Each record has a `Weight`; Route 53 returns records in
proportion to their weights.

```json
[
  {
    "Name": "api.example.com.",
    "Type": "A",
    "SetIdentifier": "blue",
    "Weight": 100,
    "TTL": 60,
    "ResourceRecords": [{"Value": "10.0.0.10"}],
    "HealthCheckId": "h-blue"
  },
  {
    "Name": "api.example.com.",
    "Type": "A",
    "SetIdentifier": "green",
    "Weight": 0,
    "TTL": 60,
    "ResourceRecords": [{"Value": "10.0.1.10"}],
    "HealthCheckId": "h-green"
  }
]
```

**Behavior:** with weights 100/0, all traffic goes to blue. Shifting
to 0/100 sends all traffic to green. Intermediate values (50/50,
10/90) allow canary deployments or gradual failover.

**Caveat:** a 0-weight record gets NO traffic but is still returned if
all other records are unhealthy (last-resort). Do NOT set both weights
to 0 — Route 53 returns nothing.

**Canary sequence:** 100/0 -> 95/5 -> 90/10 -> 50/50 -> 0/100. Pause
at each step to monitor metrics.

## Latency routing (multi-region active-active)

Route 53 maintains a latency database mapping client resolver IPs to
AWS regions. It returns the record in the lowest-latency region.

```json
[
  {
    "Name": "api.example.com.",
    "Type": "A",
    "SetIdentifier": "us-east-1",
    "Region": "us-east-1",
    "TTL": 60,
    "ResourceRecords": [{"Value": "10.0.0.10"}],
    "HealthCheckId": "h-use1"
  },
  {
    "Name": "api.example.com.",
    "Type": "A",
    "SetIdentifier": "eu-west-1",
    "Region": "eu-west-1",
    "TTL": 60,
    "ResourceRecords": [{"Value": "10.1.0.10"}],
    "HealthCheckId": "h-euw1"
  }
]
```

**Behavior:** if `us-east-1` is unhealthy, Route 53 returns `eu-west-1`
for ALL clients (not just EU clients). This is automatic — no
SECONDARY record needed. Use for active-active multi-region.

**Caveat:** "lowest latency" is based on Route 53's measurements, not
the client's actual network path. Use `test-dns-answer --resolver-ip
<client-resolver>` to inspect per-resolver answers.

## Geolocation routing (regional DR)

Route 53 returns different records based on the client's location
(continent, country, or US state).

```json
[
  {
    "Name": "api.example.com.",
    "Type": "A",
    "SetIdentifier": "eu-primary",
    "GeoLocation": {"ContinentCode": "EU"},
    "TTL": 60,
    "ResourceRecords": [{"Value": "10.1.0.10"}],
    "HealthCheckId": "h-eu-primary"
  },
  {
    "Name": "api.example.com.",
    "Type": "A",
    "SetIdentifier": "eu-secondary",
    "GeoLocation": {"ContinentCode": "EU"},
    "Failover": "SECONDARY",
    "TTL": 60,
    "ResourceRecords": [{"Value": "10.2.0.10"}]
  }
]
```

Pair `GeoLocation` with `Failover: SECONDARY` for regional DR: EU
clients go to `eu-primary` when healthy, else `eu-secondary`. Both
records share the same continent code.

**Caveat:** a default record (`GeoLocation: {"CountryCode": "*"}`) is
required to catch clients not matched by any specific geo rule.

## Multivalue answer (round-robin with health checks)

Returns up to 8 healthy IPs per query, shuffled. Each record can have
a health check.

```json
[
  {
    "Name": "pool.example.com.",
    "Type": "A",
    "SetIdentifier": "node-1",
    "MultiValueAnswer": true,
    "TTL": 30,
    "ResourceRecords": [{"Value": "10.0.0.1"}],
    "HealthCheckId": "h-node-1"
  },
  {
    "Name": "pool.example.com.",
    "Type": "A",
    "SetIdentifier": "node-2",
    "MultiValueAnswer": true,
    "TTL": 30,
    "ResourceRecords": [{"Value": "10.0.0.2"}],
    "HealthCheckId": "h-node-2"
  }
]
```

**Behavior:** clients get a shuffled subset of healthy IPs. If a node
is unhealthy, it is excluded from the subset. NOT load balancing —
clients pick one IP and stick with it.

## Planned failover sequence (weighted)

1. **Pre-flight (T-7 days):** lower TTL to 60s. Verify both blue and
   green health checks are Healthy.
2. **T-0:** apply the weighted shift (100/0 -> 0/100) in a single
   change-batch.
3. **T+60s:** verify `test-dns-answer` returns green IP.
4. **T+120s:** verify application metrics show green taking traffic.
5. **T+24h:** if stable, optionally raise TTL back to 300s for
   stability. Keep it at 60s if you expect to fail back soon.

## Emergency failover sequence (failover routing)

1. **T-0:** PRIMARY health check is Unhealthy. Verify
   `test-dns-answer` already returns SECONDARY IP (Route 53 SHOULD
   have failed over automatically).
2. **If TTL > 60:** optionally lower TTL to 60s to shrink the stale-
   traffic window. Accept that clients cached at the old TTL will
   continue to the primary until expiry.
3. **If you want to invert topology (old primary becomes secondary):**
   UPSERT both records with IPs/HealthCheckIds swapped.
4. **Post-failover:** monitor secondary health and application metrics.

## Failback sequence

1. **Pre-flight:** restore the primary endpoint. Verify its health
   check is `Healthy` for at least 2 consecutive intervals (60-120
   seconds).
2. **T-0:** if topology was inverted during the emergency, swap it
   back. If using weighted routing, shift weights back.
3. **T+60s:** verify `test-dns-answer` returns primary IP.
4. **T+120s:** verify application metrics show primary taking traffic.
5. **Debrief:** document the root cause, time-to-detect, time-to-
   failover, time-to-failback. Update the runbook.

## TTL strategy

| Scenario | Recommended TTL | Why |
|---|---|---|
| Failover record (PRIMARY/SECONDARY) | 60s | Fast failover; clients re-query within 60s of the change. |
| Weighted record (canary) | 60s | Quick rollback if the canary is bad. |
| Latency record (active-active) | 60-300s | Tolerate slightly higher TTL since failover is automatic. |
| Stable record (no failover) | 300-3600s | Reduce DNS query volume and cost. |
| Emergency failover on a 300s record | Lower to 60s FIRST | Shrink the stale window before flipping routing. |

**Cost note:** TTL does not affect Route 53 query cost directly, but
lower TTL means more recursive-resolver queries hit Route 53
authoritative servers. For high-traffic domains, the difference
between 60s and 300s TTL can be significant in query volume. Balance
failover speed against query cost.
