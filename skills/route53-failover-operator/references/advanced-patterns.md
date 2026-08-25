# Advanced Patterns — Route 53 Failover Operator

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Cost/time baselines (2026)

**Cost/time baselines (2026):**

- Endpoint health check: $0.50/endpoint/month for the first 100, then
  $0.25 each above 100. CloudWatch-alarm-based and calculated health
  checks are free (the underlying alarm costs apply).
- HTTP/HTTPS health check interval: 10s (Fast) or 30s (Standard). 10s
  roughly doubles cost.
- DNS propagation after a record change: bounded by the record TTL.
  Lower TTL = faster failover but more DNS query traffic to Route 53
  authoritative servers.
- Calculated health checks (AND/OR of up to 256 child checks): free, but
  each child check is billed at its own type's rate.

## Mindset — three Route 53 realities

- **Failover speed is TTL-bound, not health-check-bound.** The health
  check may flip to unhealthy in 10-30 seconds, but every client that
  cached the old IP at TTL=N will keep sending traffic to the primary
  until that cache entry expires. The single highest-leverage failover
  lever is the record TTL — set it to 60s for failover records. A
  300s TTL means up to 5 minutes of stale traffic even after a perfect
  health-check transition.

- **"Healthy" does not mean "working."** A health check that probes
  `/health` returning 200 will report healthy even when the application
  is broken on every other route. The failover trigger is only as good
  as the probe. Pair the endpoint health check with a CloudWatch alarm
  on a real business metric (request success rate, error rate) so a
  false-healthy health check does not mask a real outage.

- **Cross-account Route 53 requires the zone-owning account to grant
  the operator account.** The operator account's IAM role identity-based
  policy is NOT sufficient by itself. The zone-owning account must
  attach a resource-based policy (or delegate via RAM / Organizations
  `AWS::Route53Resolver::*`, or use a cross-account role assumption) that
  allows the operator's role ARN to call
  `route53:ChangeResourceRecordSets` on the hosted zone ARN.

## Step 0: Expert knowledge — non-obvious Route 53 behaviors

These behaviors are easy to misjudge without operational failover
experience. Each changes a plan if ignored:

- **Route 53 health checks run from 3+ global regions, not one.** Each
  checker region issues the probe independently; a health check is
  unhealthy only when the failure threshold (default 3) is hit
  consecutively across the merged observation. This means a single-
  region network blip rarely triggers failover, but a true outage does
  in ~10-30 seconds (interval x threshold).

- **The record TTL is the failover contract, not the health check
  interval.** Even after Route 53 marks the primary unhealthy and stops
  returning its IP, every recursive resolver and every client OS that
  cached the old IP at the previous TTL will keep using it. Lowering TTL
  to 60s ahead of a planned failover is the single highest-leverage
  action; for an emergency failover with a 300s TTL, the operator must
  either accept up to 5 minutes of stale traffic or proactively purge
  caches.

- **Failover routing policy requires paired records.** One record has
  `Failover: PRIMARY` with a `HealthCheckId`; the other has `Failover:
  SECONDARY` (no health check, or its own health check). Route 53
  returns the PRIMARY IP when its health check is healthy, otherwise
  the SECONDARY. There is no weighted gradient.

- **Weighted routing is the right tool for canary/blue-green, not
  failover routing.** A weighted policy with weights 100/0 is a valid
  "failover" shape, and shifting 100->0/0->100 is a planned failover
  that can be paused (50/50) or rolled back. Failover routing is
  automatic but binary; weighted is manual but graduated. Choose
  weighted for planned failovers that may need to pause.

- **Multivalue answer is NOT load balancing.** It returns up to 8
  healthy IPs per query (shuffled), but clients pick one. It is a
  "round-robin with health checks" — useful for spreading load across
  many endpoints, not for primary/secondary failover. Combine with
  per-endpoint health checks for opportunistic redundancy.

- **Latency routing does not fail over; it falls back.** If the lowest-
  latency region's endpoint is unhealthy, Route 53 serves the next-
  lowest-latency healthy region. This is automatic and works without a
  failover record. Use latency routing for multi-region active-active.

- **Geolocation routing can pair with failover for regional DR.** A
  geolocation record (e.g., "users in Europe") can be paired with a
  geolocation + failover SECONDARY record so that if the primary EU
  endpoint is unhealthy, EU users fall back to a secondary EU endpoint.
  This requires both records to share the same geolocation continent
  code.

- **Calculated health checks (AND/OR) compose other health checks.** A
  calculated check lets you say "failover only when BOTH the endpoint
  check AND the database-alarm-based check are unhealthy." This is the
  antidote to the false-healthy trap. Up to 256 child checks; the
  calculated check itself is free.

- **Insulated health checks prevent child-check influence on other
  calculated checks.** Insulating a child health check prevents it from
  affecting the status of OTHER calculated health checks that reference
  it. Use when a child check is shared between multiple calculated
  checks with different semantics.

- **`test-dns-answer` shows what Route 53 authoritatively answers from
  a specific resolver IP.** It does NOT show what a real client at that
  IP sees — recursive resolvers cache. To verify end-to-end, run
  `dig @1.1.1.1 <fqdn>` and `dig @8.8.8.8 <fqdn>` from multiple
  networks. `test-dns-answer` is authoritative truth; `dig` is observed
  truth.

- **CloudWatch-alarm-based health checks are free but slower.** A
  CloudWatch alarm in ALARM state flips the health check unhealthy.
  This avoids the per-endpoint fee but adds alarm-evaluation latency
  (typically 1 minute for a 1-minute period). Use for composite health
  signals; use endpoint checks for fast failover.

- **Cross-account hosted zone IAM requires a resource-based grant.**
  Route 53 does NOT support resource-based policies on hosted zones the
  way S3/KMS do — the zone-owning account must either (a) attach an
  inline policy to a role the operator assumes via STS, or (b) use AWS
  RAM to share the hosted zone with the operator account via
  Organizations or a direct invitation. Identity-based policies in the
  operator account alone cannot grant cross-account Route 53 access.

- **`UPSERT` is the safer change action than `CREATE` or `DELETE`.**
  `UPSERT` creates the record if it does not exist, or updates it if it
  does. `CREATE` fails if the record exists; `DELETE` fails if it does
  not. For failover operations, prefer `UPSERT` so the same change
  batch works whether the record is in its pre-state or post-state.

- **`ChangeResourceRecordSets` is eventually consistent.** The API
  returns a `ChangeInfo` with `Status: PENDING` immediately; the actual
  DNS change propagates within 60 seconds typically. Poll
  `get-change --id <change-id>` until `Status: INSYNC` before declaring
  the failover applied.

- **Both records unhealthy means Route 53 returns all records.** If
  PRIMARY and SECONDARY are both unhealthy (both have failing health
  checks), Route 53 returns BOTH IPs — it prefers serving a possibly-
  bad answer over no answer. This is why a BLOCKED pre-check on "both
  unhealthy" matters: failing over when the secondary is also down does
  not help.

## Step 2 — READY plan contents

- The exact `change-resource-record-sets` JSON batch with all fields
  populated from the current record set + the operation parameters.
- The expected DNS propagation time (TTL seconds for cached resolvers;
  near-instant for uncached).
- The expected side-effects (which IPs Route 53 will answer with after
  INSYNC; which health check transitions to expect).
- The CONFIRM gate prompt.
- The verification step (`test-dns-answer` + `dig` from multiple
  resolvers + application metric check).

## Recent AWS features (2024-2026)

- **Health check `EnableSNI` GA (2024):** Server Name Indication
  support on HTTPS health checks. Required when the endpoint uses
  virtual-hosted TLS (multiple certs on one IP). Without SNI, Route 53
  receives the default certificate which may not match the probe
  hostname.

- **CloudWatch-alarm-based health check refinements (2024-2025):**
  Health checks can now be driven directly by a CloudWatch alarm in
  ALARM state, with no per-endpoint probe. Useful when the health
  signal is a composite metric (e.g., error rate > threshold) rather
  than an HTTP response.

- **Calculated health check `InsufficientDataHealthStatus` (2024):**
  Explicit control over the parent's status when child checks have
  insufficient data. Default is `LastKnownGoodStatus`; set to
  `Unhealthy` for fail-fast workloads.

- **Insulated child health checks (2024-2025):** A child health check
  can be marked insulated so that its status does not affect OTHER
  calculated checks that reference it. Use when sharing a child check
  between calculated checks with different semantics.

- **Cross-account hosted zone sharing via RAM (2024):** AWS RAM
  supports sharing Route 53 hosted zones with member accounts in an
  Organization. The zone-owning account creates a RAM resource share;
  member accounts can then manage records via their own IAM roles.
  Replaces the older inline-policy-only pattern.

- **`test-dns-answer` mulcdtiple resolver IPs (2024):** The
  `test-dns-answer` API now accepts any public resolver IP, allowing
  operators to verify Route 53's answer from the perspective of
  specific resolver networks. Previously limited to a small set.

- **Route 53 Resolver DNS Firewall integration (2024-2025):** For
  VPC-resolver-based failover verification, the Resolver DNS Firewall
  can block or allow specific domains. Verify the firewall is not
  blocking the failover target domain during VPC-internal tests.

- **CidrRoutingConfig (2025):** A new routing policy that returns
  different answers based on the client's CIDR block. Useful for
  deterministic failover by client geography (e.g., send corporate
  ranges to a known-good endpoint during DR).
