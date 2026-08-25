# Advanced Patterns — Route 53 DNS Troubleshooter

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Quick start — symptom to layer map

- **Symptom -> layer map (first plausible match drives the first probe):**
  `NXDOMAIN` (domain does not exist) -> NS_DELEGATION / GLUE_RECORD;
  `SERVFAIL` / DNSSEC validation failure -> DNSSEC_KSK / DNSSEC_ZSK /
  DNSSEC_DS; wrong IP returned -> DNS_CACHE_TTL / ROUTING_POLICY /
  ALIAS_CNAME_CONFLICT; failover not switching -> HEALTH_CHECK /
  ROUTING_FAILOVER; private zone not resolving in VPC ->
  PHZ_VPC_ASSOCIATION; same domain resolves differently inside vs
  outside VPC -> SPLIT_HORIZON / RESOLVER_INBOUND; wildcard cert
  validation CNAME conflict -> WILDCARD_CERT.

## Quick start — senior DNS gotchas

- **The NS delegation chain is the #1 misdiagnosis area.** The full
  chain is: root TLD servers -> registrar NS records -> hosted zone
  NS records. If the registrar's NS records do not match the hosted
  zone's NS records, the domain resolves to stale or no records.
  Always verify the NS delegation chain with `dig NS` from a public
  resolver before debugging record-level issues.
- **DNSSEC DS record at the parent must match the hosted zone KSK.**
  If DNSSEC is enabled on the hosted zone but the DS record at the
  parent (registrar) zone does not match the KSK, validating resolvers
  return SERVFAIL. The DS record is the cryptographic link between
  parent and child zones.
- **Private hosted zones need VPC association via DHCP Options Set or
  explicit association.** A private hosted zone that is not associated
  with the VPC where queries originate will NOT resolve. The VPC's
  DHCP Options Set `domain-name-servers` must point at
  `AmazonProvidedDNS` (169.254.169.253) for Route 53 Resolver to
  answer queries from that VPC.
- **INSUFFICIENT_DATA for propagation-delay or AWS-side incidents.**
  DNS changes propagate based on TTL. A change that was made 2 minutes
  ago may not have propagated yet; wait at least 2x the old TTL before
  declaring a failure. A regional Route 53 outage is not
  customer-fixable — escalate to AWS Support and surface the AWS Health
  event ARN.

## Mindset

A failing DNS resolution is usually a delegation, association, or
cache configuration issue wearing a "DNS is broken" costume. The
record itself is correct in the majority of cases; the broken thing is
NS delegation at the registrar, DNSSEC signing key status, VPC
association for private zones, health check status for failover
routing, or TTL-based caching. Treat the record configuration as
innocent until the delegation chain, DNSSEC chain, zone associations,
and health checks are proven correct. Senior network engineers do not
start by editing records; they start with `dig +trace` from a public
resolver and `list-resource-record-sets` for the hosted zone, and only
change records once the delegation and association layers are confirmed
correct.

## Philosophy — four senior DNS behaviours

Four behaviours separate a senior DNS engineer from a generalist:

- **The NS delegation chain is a four-link chain, and any broken link
  causes resolution failure.** The chain is: (1) root servers
  (`a.root-servers.net`), (2) TLD servers (`.com`, `.io`, etc.),
  (3) registrar NS records (set at the domain registrar, e.g., GoDaddy,
  Namecheap, or Route 53 Registrar), and (4) hosted zone NS records
  (the four NS servers assigned by Route 53). If links (3) and (4) do
  not match — i.e., the registrar points at different NS servers than
  the hosted zone — resolution fails or returns stale records.
  Operators who "added the record to the zone" but did not update the
  registrar NS see no effect from their change.

- **DNSSEC is a chain of trust from the root, and each parent-to-child
  link is established by a DS record.** When DNSSEC signing is enabled
  on a hosted zone, Route 53 generates a KSK (key-signing key) and a
  ZSK (zone-signing key). The KSK's public key must be published as a
  DS record at the parent zone (via the registrar). If the DS record
  does not match the KSK — wrong algorithm, wrong digest, or stale key
  — validating resolvers (which use AD bit / DO bit) return SERVFAIL
  for every query to the zone. Non-validating resolvers still resolve
  correctly, creating the confusing symptom "works on some networks,
  fails on others."

- **Private hosted zones and public hosted zones are independent.** A
  private hosted zone resolves only from VPCs it is associated with,
  via the Route 53 Resolver (AmazonProvidedDNS at 169.254.169.253).
  A public hosted zone resolves from the global DNS. If the same domain
  name exists in both a private and a public zone (split-horizon DNS),
  the private zone takes precedence for queries from the associated
  VPC. Operators who "can resolve from the office but not from the VPC"
  (or vice versa) have a private-zone association or split-horizon
  issue.

- **Health-check-based failover requires the health check to be in the
  SAME evaluation as the record's routing policy.** A failover record
  with `Failover: PRIMARY` and `HealthCheckId: abc123` only serves
  traffic when health check `abc123` is healthy. If the health check
  itself is misconfigured (wrong endpoint, wrong protocol, wrong path),
  the record is always unhealthy and the SECONDARY (or no answer) is
  returned. Operators who "see the PRIMARY record in the zone but DNS
  returns nothing" have a failing health check causing the record to
  be suppressed.

## Zone-state short-circuit table

| Configuration field | Effect on diagnosis |
|---|---|
| `Config.PrivateZone: true` but no VPC associations | Private zone has no VPC to serve queries from. Resolution fails from all locations. |
| `Config.PrivateZone: false` but registrar NS not updated | Public zone exists but the TLD does not delegate to it. Resolution fails globally. |
| DNSSEC enabled but `KeySigningKeys[].KeyTag` does not match parent DS | Validating resolvers return SERVFAIL. |
| Health check `Status: Unhealthy` on a PRIMARY failover record | DNS suppresses the PRIMARY record; returns SECONDARY or nothing. |
| Multiple zones for the same domain name (public + private) | Split-horizon DNS; private zone wins inside the VPC. |

## Delegation / record-set pre-flight table

| Field | Effect |
|---|---|
| Hosted zone NS records differ from registrar NS records | Delegation chain is broken. Resolution may work intermittently or fail entirely. |
| SOA serial does not increment after a change | Indicates the change was not committed (rare in Route 53) or the secondary zones (if any) are not transferring. |
| Alias record and CNAME for the same name | Cannot coexist. Route 53 rejects the change with `ConflictingDomainExists`. |
| `TTL: 86400` on the old record | Changes take up to 24 hours to propagate from caches. Wait 2x TTL before declaring failure. |

## Step 0: Non-obvious behaviours that change diagnosis

These are the operational gotchas a senior DNS engineer knows from
incident experience. Each one routes a diagnosis away from the obvious
layer to a less obvious one:

- **DNS TTL is the maximum cache duration, not the average.** A TTL of
  3600 seconds means any resolver that cached the old record will serve
  it for up to 3600 seconds from the time it was cached. After a record
  change, the worst-case wait is 2x the OLD TTL (once for the resolver
  that cached it just before the change, and once for the resolver that
  queries the authoritative server and gets the new TTL). Operators who
  "changed the record 30 minutes ago" with a 1-hour TTL have not waited
  long enough.

- **`dig` uses the system resolver by default; `dig @8.8.8.8` bypasses
  it.** When debugging DNS, always query multiple resolvers (Google
  `8.8.8.8`, Cloudflare `1.1.1.1`, the VPC resolver `169.254.169.253`)
  to distinguish local cache issues from global resolution issues. A
  record that "works on `dig @8.8.8.8` but fails on `dig` (local)" is
  a local resolver cache issue, not a Route 53 issue.

- **Route 53 ALIAS records are resolved server-side by Route 53.** When
  a resolver queries Route 53 for an ALIAS record, Route 53 looks up
  the target (e.g., an ALB DNS name) and returns the final IP address.
  The ALIAS is invisible to the client — the client sees an A/AAAA
  record. This is different from a CNAME, which returns the CNAME and
  requires the client to do a second query. ALIAS records and CNAME
  records CANNOT coexist for the same name.

- **DNSSEC validation failures are network-dependent.** A validating
  resolver (one that sets the DO bit and validates signatures) returns
  SERVFAIL if the DNSSEC chain is broken. A non-validating resolver
  ignores DNSSEC and resolves normally. This creates the confusing
  symptom "the domain works on my home Wi-Fi but not on my corporate
  network" — the corporate network uses a validating resolver. Always
  check with `dig +dnssec` to see the AD (Authenticated Data) bit.

- **The DS record at the parent zone is the cryptographic link.**
  Without it, DNSSEC is "enabled" on the hosted zone but the chain of
  trust is broken. The DS record is typically set via the registrar
  (which controls the parent zone). If the registrar does not support
  DS record management, DNSSEC cannot be fully enabled. Route 53
  Registrar supports DS records natively.

- **Private hosted zones resolve ONLY from associated VPCs.** A private
  zone for `internal.example.com` that is not associated with VPC
  `vpc-abc123` will NOT resolve from instances in that VPC. The VPC
  must either be explicitly associated via
  `associate-vpc-with-hosted-zone` or authorized via
  `create-vpc-association-authorization` (for cross-account
  associations). The VPC's DHCP Options Set must use
  `AmazonProvidedDNS`.

- **Route 53 Resolver inbound endpoints allow on-premises to query
  Route 53.** An inbound endpoint provides ENIs in specified subnets
  that on-premises DNS resolvers can forward queries to. If the inbound
  endpoint's Security Group does not allow UDP/TCP 53 from the
  on-premises CIDR, queries from on-premises fail silently (timeout).

- **Route 53 Resolver outbound endpoints allow VPC to forward to
  on-premises.** An outbound endpoint provides ENIs that forward
  queries matching resolver rules to on-premises DNS servers. If the
  resolver rule is not associated with the VPC, queries are not
  forwarded.

- **Split-horizon DNS means the same domain resolves differently
  inside vs outside the VPC.** If `api.example.com` exists in both a
  public hosted zone and a private hosted zone associated with the VPC,
  queries from the VPC resolve the private zone (internal IP) while
  queries from the internet resolve the public zone (public IP). This
  is intentional but confuses operators who see different IPs from
  different locations.

- **Health checks evaluate independently of DNS.** A health check
  monitors an endpoint (IP, domain, or another health check) at a
  configurable interval (10s or 30s). The health check status drives
  failover, weighted, and multi-value-answer routing. If the health
  check endpoint is wrong (e.g., monitors the wrong path or port), the
  record is suppressed even though the actual service is healthy.
  Always check `get-health-check-status` before declaring a failover
  routing issue.

- **Geolocation routing defaults to a `Default` geo location if no
  match.** If a query originates from a continent/country not covered
  by any geolocation record, Route 53 returns the record with
  `GeoLocation.CountryCode: "*"`. If no default record exists, Route 53
  returns NXDOMAIN for that query. Operators who "see NXDOMAIN from
  some regions" may be missing a default geolocation record.

- **Latency routing is based on AWS region-to-region latency, not
  network distance.** Route 53 maintains a latency table between AWS
  regions. A user in London querying a latency-routed record gets the
  record in the region with the lowest latency to London (typically
  `eu-west-1` or `eu-west-2`). If only one region has a latency record,
  ALL queries go to that region regardless of the user's location.

- **Weighted routing with a weight of 0 suppresses the record.** A
  record with `Weight: 0` receives no traffic. This is useful for
  draining (set weight to 0 to remove from rotation) but surprises
  operators who accidentally set weight to 0 during testing.

- **Domain transfers change the registrar NS records.** During a
  domain transfer between registrars, the NS records at the TLD change.
  If DNSSEC was enabled at the old registrar, the DS record must be
  re-established at the new registrar. A gap in DS coverage causes
  SERVFAIL on validating resolvers during the transition.

- **Wildcard certificate validation CNAMEs (`_acme-challenge`) can
  conflict with existing records.** ACM creates a CNAME record like
  `_abc123.example.com` for certificate validation. If a wildcard
  `*.example.com` CNAME already exists, Route 53 returns the wildcard
  instead of the validation CNAME, causing certificate validation to
  fail or renew incorrectly.

## Step 1 — symptom-to-branch table

Map the symptom to a branch and jump to that branch's section. If the
symptom matches none of the categories, route to Step 13
(INSUFFICIENT_DATA).

| Symptom | Branch |
|---|---|
| `NXDOMAIN` (domain does not exist) | Step 2 — NS delegation |
| `SERVFAIL` or intermittent resolution on validating resolvers | Step 3 — DNSSEC |
| Wrong IP returned (stale or unexpected) | Step 4 — DNS cache / TTL |
| Alias record change rejected (`ConflictingDomainExists`) | Step 5 — Alias vs CNAME |
| Routing policy not resolving as expected | Step 6 — Routing policy |
| Failover record always returns SECONDARY | Step 7 — Health check |
| Private zone not resolving from VPC | Step 8 — Private hosted zone |
| Same domain resolves differently inside vs outside VPC | Step 9 — Split-horizon |
| On-premises cannot resolve Route 53 private zones | Step 10 — Resolver inbound |
| VPC cannot resolve on-premises DNS names | Step 11 — Resolver outbound |
| Wildcard cert validation fails or renews incorrectly | Step 12 — Wildcard cert |
| SERVFAIL after domain transfer | Step 12b — Domain transfer |
| None of the above | Step 13 — INSUFFICIENT_DATA |

## Step 2 — delegation chain diagram

The delegation chain:

```
Root servers (a.root-servers.net)
  -> TLD servers (.com, .io, etc.)
    -> Registrar NS records (set at the domain registrar)
      -> Hosted zone NS records (Route 53 assigned NS)
```

## Step 6a — geolocation checks

```bash
aws route53 list-resource-record-sets \
  --hosted-zone-id <zone-id> --output json | \
  jq '.ResourceRecordSets[] | select(.GeoLocation != null)'
```

| Check | Expected |
|---|---|
| Every geolocation record has a `GeoLocation` (ContinentCode, CountryCode, or SubdivisionCode) | At least one record per target region |
| A default record exists (`GeoLocation.CountryCode: "*"`) | Catches all queries not matching a specific geo |
| `RoutingPolicy: geolocation` on all records for the name | All records for the same name use the same routing policy |

Common error: no default record -> queries from uncovered regions
return NXDOMAIN.

## Step 6b — latency checks

| Check | Expected |
|---|---|
| Each latency record has a `Region` (AWS region code) | At least two records in different regions |
| `RoutingPolicy: latency` on all records for the name | All records for the same name use latency routing |

Common error: only one region has a record -> all queries go to that
region regardless of user location.

## Step 6c — weighted checks

| Check | Expected |
|---|---|
| Each weighted record has a `Weight` (integer >= 0) | Weights are relative; a record with weight 0 gets no traffic |
| `RoutingPolicy: weighted` on all records for the name | All records for the same name use weighted routing |
| Health check on each weighted record | Unhealthy records are suppressed (weight effectively 0) |

Common error: one record has `Weight: 0` (intentional drain or
accidental).

## Step 6d — failover checks

| Check | Expected |
|---|---|
| PRIMARY record has `Failover: PRIMARY` and `HealthCheckId` | PRIMARY is the active record when healthy |
| SECONDARY record has `Failover: SECONDARY` | SECONDARY takes over when PRIMARY is unhealthy |
| Health check endpoint is correct | See Step 7 |

Common error: health check is failing, so PRIMARY is always suppressed
(see Step 7).

## Step 7 — common failure patterns

Common failure patterns:

| Pattern | Cause |
|---|---|
| Health check monitors the Route 53 record itself instead of the endpoint | Circular dependency. Fix: monitor the endpoint IP or ALB DNS directly. |
| `ResourcePath: /health` but the endpoint does not serve `/health` | 404 or connection refused. Fix: correct the path. |
| Health check monitors `HTTP` but endpoint redirects to `HTTPS` | Health check sees 301/302 as unhealthy (expects 2xx/3xx). Fix: use HTTPS type, or enable `EnableSNI`. |
| `Type: CALCULATED` with all child checks unhealthy | Calculated health check returns unhealthy. Fix: fix child health checks. |
| Health check in a different region than the endpoint | Latency-based false negatives. Consider CloudWatch alarm-based health checks for cross-region. |
| `InsufficientDataHealthStatus: Healthy` on CloudWatch alarm health check | CloudWatch alarm has insufficient data; health check defaults to healthy. |

## Step 8 — PHZ VPC association checks and failure patterns

| Check | Expected |
|---|---|
| `VPCs` in `get-hosted-zone` includes the target VPC | If absent, the zone is not associated with the VPC |
| DHCP Options Set `domain-name-servers` includes `AmazonProvidedDNS` | Required for Route 53 Resolver to answer queries |
| `PrivateZone: true` in hosted zone config | Zone must be private to resolve from VPC |

Common failure patterns:

| Pattern | Cause |
|---|---|
| Private zone not associated with VPC | Fix: `associate-vpc-with-hosted-zone`. |
| Cross-account VPC association not authorized | Fix: `create-vpc-association-authorization` in the zone account, then `associate-vpc-with-hosted-zone` in the VPC account. |
| DHCP Options Set uses custom DNS (not AmazonProvidedDNS) | Route 53 Resolver is bypassed. Fix: use `AmazonProvidedDNS` (169.254.169.253) as the first nameserver. |
| Private zone name overlaps with a public zone name | Split-horizon; private zone wins in the VPC. Intentional, but may hide public records. |

## Recent AWS features (2024-2026)

- **DNSSEC signing in Route 53 (2024 GA):** Route 53 can now sign
  hosted zones with DNSSEC automatically. The KSK and ZSK are managed
  by Route 53 (KMS-backed). The DS record must still be established at
  the parent registrar. Diagnostically, `get-dnssec` shows the key
  state and DS values.
- **CIDR routing (2024-2025):** IP-based routing policy routes queries
  based on the client's source IP CIDR block. Useful for split-routing
  specific office networks or ISP ranges. Diagnostically, check
  `CidrRoutingConfig` on the record set.
- **Resolver query logging GA (2024):** Resolver query logs capture all
  DNS queries originating from a VPC. CloudWatch Logs log group
  receives the queries. Diagnostically, `filter-log-events` on the log
  group shows what queries were made and what Route 53 returned.
- **Health check enhanced metrics (2025):** Health checks now emit
  per-probe metrics (HTTP status, response time) to CloudWatch.
  Diagnostically, check `HealthCheckPercentageHealthy` and
  `ConnectionTime` metrics.
- **Private hosted zone cross-account sharing (2025):** Simplified
  cross-account VPC association via RAM share. Diagnostically, the
  association still requires `create-vpc-association-authorization`
  and `associate-vpc-with-hosted-zone`, but RAM reduces the operational
  overhead.
