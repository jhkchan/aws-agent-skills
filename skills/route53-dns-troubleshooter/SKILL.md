---
name: route53-dns-troubleshooter
description: >-
  Diagnoses Amazon Route 53 DNS resolution failures through a twelve-category
  diagnostic tree: NS delegation errors (glue records, NS mismatch between
  registrar and hosted zone), SOA serial mismatch, DNSSEC signing errors
  (KSK/ZSK key status, DS record at parent zone), alias record vs CNAME
  conflict, routing policy evaluation errors (geolocation, latency,
  weighted, failover), private hosted zone VPC association missing,
  split-horizon DNS conflicts, Route 53 Resolver inbound/outbound endpoint
  misconfiguration, health check associated with record but failing,
  DNS query logging analysis, domain transfer DNS disruption, and wildcard
  certificate validation CNAME (_acme-challenge) conflicts. Walks symptoms
  to a verified root cause with evidence-backed probes; emits
  ROOT_CAUSE_IDENTIFIED or INSUFFICIENT_DATA.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline symptom classification works from pasted error messages and hosted zone configuration. Live-account diagnosis uses aws route53 list-hosted-zones / get-hosted-zone / list-resource-record-sets / get-health-check / get-dnssec, aws route53resolver list-resolver-endpoints / list-resolver-rule-associations, aws ec2 describe-vpcs / describe-dhcp-options, aws logs filter-log-events (CloudWatch Logs for Route 53 query logging), dig / nslookup / delv for live DNS resolution, and aws cloudtrail lookup-events (AWS CLI v2, SSO or key-based credentials).
keywords:
- Route 53
- DNS
- hosted zone
- NS delegation
- glue records
- SOA serial
- DNSSEC
- KSK
- ZSK
- DS record
- alias record
- CNAME
- routing policy
- geolocation
- latency
- weighted
- failover
- private hosted zone
- VPC association
- split-horizon DNS
- Route 53 Resolver
- inbound endpoint
- outbound endpoint
- health check
- DNS query logging
- domain transfer
- wildcard certificate
- _acme-challenge
- TTL
- DNS cache
- troubleshooting
tags:
- route53
- networking
- troubleshooting
- dns
- dnssec
- hosted-zone
- health-check
- resolver
- private-hosted-zone
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Networking
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
  when_to_use: Diagnosing a Route 53 DNS resolution failure (NS delegation broken, DNSSEC signing error, alias vs CNAME conflict, routing policy not resolving as expected, private hosted zone not resolving in VPC, health check failing causing failover, Resolver endpoint misconfiguration, split-horizon DNS conflict, domain transfer disruption, wildcard certificate validation CNAME conflict), walking a symptom to the failed layer with verify and fix commands, validating why a domain does not resolve, or triaging a "DNS is broken" page where the root cause may be delegation, DNSSEC, record config, VPC association, health check, or Resolver — not necessarily the application or the web server.
  when_not_to_use: Application-level HTTP errors once DNS resolves correctly (use the application logs and alb-unhealthy-target-troubleshooter), CDN/CloudFront cache behaviour (use the CloudFront distribution logs), TLS handshake errors after DNS resolves (use acm-certificate-expiry-auditor), or VPC subnet routing / NACL posture audits (use ec2-security-group-auditor). This skill diagnoses DNS resolution-time failures; it does not audit steady-state network posture or tune application delivery.
  activation_triggers:
  - Route 53 DNS resolution failed
  - DNS does not resolve
  - Route 53 NS delegation
  - Route 53 glue records
  - Route 53 NS mismatch
  - Route 53 DNSSEC
  - Route 53 KSK
  - Route 53 ZSK
  - Route 53 DS record
  - Route 53 alias record CNAME conflict
  - Route 53 routing policy
  - Route 53 geolocation routing
  - Route 53 latency routing
  - Route 53 weighted routing
  - Route 53 failover routing
  - Route 53 private hosted zone
  - Route 53 VPC association
  - Route 53 split-horizon DNS
  - Route 53 Resolver endpoint
  - Route 53 health check failing
  - Route 53 DNS query logging
  - Route 53 domain transfer
  - Route 53 wildcard certificate
  - _acme-challenge CNAME
  - troubleshoot Route 53 DNS
  - DNS NXDOMAIN
  - DNS SERVFAIL
  invocation_schema: 'Input: either (a) a symptom description (error message, observed behaviour, "domain does not resolve", "DNS returns wrong IP"), optionally paired with the hosted zone configuration and dig output, OR (b) a HostedZoneId / domain name plus resolver context (VPC, resolver endpoint, client region) for live-account diagnosis. Output: a deterministic TARGET/VERDICT/REASON/LAYER/EVIDENCE/REMEDIATION block where VERDICT ∈ {ROOT_CAUSE_IDENTIFIED, INSUFFICIENT_DATA} and LAYER ∈ {NS_DELEGATION, GLUE_RECORD, SOA_SERIAL, DNSSEC_KSK, DNSSEC_ZSK, DNSSEC_DS, ALIAS_CNAME_CONFLICT, ROUTING_POLICY, ROUTING_GEOLOCATION, ROUTING_LATENCY, ROUTING_WEIGHTED, ROUTING_FAILOVER, PHZ_VPC_ASSOCIATION, SPLIT_HORIZON, RESOLVER_INBOUND, RESOLVER_OUTBOUND, HEALTH_CHECK, DNS_CACHE_TTL, DOMAIN_TRANSFER, WILDCARD_CERT, UNKNOWN}.'
  invocation_example: "# Minimal valid input (offline symptom classification):\nSymptom: \"The domain api.example.com resolves to the old\nIP 203.0.113.10 instead of the new ALB DNS name. The new ALIAS\nrecord was added to the hosted zone but dig still returns the\nold IP after 2 hours.\"\nHostedZoneId: Z2 ABCDEFGHIJ\nDomain: api.example.com\nRecord type: A (ALIAS to ALB)\nTTL: 300\nExpected: resolves to dualstack.alb-xxx.us-east-1.elb.amazonaws.com\nActual: resolves to 203.0.113.10 (stale)"
---

# Route 53 DNS Troubleshooter

## Quick start

- **Symptom -> layer map (first plausible match drives the first probe):**
  `NXDOMAIN` (domain does not exist) -> NS_DELEGATION / GLUE_RECORD;
  `SERVFAIL` / DNSSEC validation failure -> DNSSEC_KSK / DNSSEC_ZSK /
  DNSSEC_DS; wrong IP returned -> DNS_CACHE_TTL / ROUTING_POLICY /
  ALIAS_CNAME_CONFLICT; failover not switching -> HEALTH_CHECK /
  ROUTING_FAILOVER; private zone not resolving in VPC ->
  PHZ_VPC_ASSOCIATION; same domain resolves differently inside vs
  outside VPC -> SPLIT_HORIZON / RESOLVER_INBOUND; wildcard cert
  validation CNAME conflict -> WILDCARD_CERT.
- **Always verify with a probe, never guess.** Each layer has a single
  command (dig, nslookup, or AWS CLI) that proves or disproves it. A
  ROOT_CAUSE_IDENTIFIED verdict requires positive evidence — a failing
  probe that matches the symptom — not a process of elimination that
  "must be the TTL."
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

## Philosophy

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

## Quick reference — symptom triage table

| Symptom phrase / error | Most likely layer | First probe |
|---|---|---|
| `NXDOMAIN` for a domain that has records | NS_DELEGATION | `dig +trace NS <domain>` from a public resolver |
| `SERVFAIL`, intermittent resolution on some networks | DNSSEC_DS / DNSSEC_KSK | `dig +dnssec <domain>`, check DS at parent |
| Wrong IP returned (stale) | DNS_CACHE_TTL | `dig <domain> @8.8.8.8` (bypass local cache); check old TTL |
| Alias record conflicts with existing CNAME | ALIAS_CNAME_CONFLICT | `list-resource-record-sets` for the zone |
| Geolocation routing returns wrong region's record | ROUTING_GEOLOCATION | `dig <domain>` from different regions; check geolocation config |
| Weighted routing sends all traffic to one record | ROUTING_WEIGHTED | Check weight values and health check on other records |
| Failover record always returns SECONDARY | HEALTH_CHECK / ROUTING_FAILOVER | `get-health-check-status` |
| Private zone not resolving from VPC | PHZ_VPC_ASSOCIATION | `list-vpc-association-authorizations`, `get-hosted-zone` |
| Same domain resolves differently inside vs outside VPC | SPLIT_HORIZON | Check for overlapping private + public zones |
| Resolver rules not forwarding as expected | RESOLVER_OUTBOUND | `list-resolver-rules`, `list-resolver-rule-associations` |
| DNS queries from on-premises not reaching Route 53 | RESOLVER_INBOUND | `list-resolver-endpoints`, check inbound endpoint SG and route |
| Wildcard cert validation CNAME conflict | WILDCARD_CERT | `dig CNAME _acme-challenge.<domain>` |
| `SERVFAIL` after domain transfer | DOMAIN_TRANSFER | Check registrar NS, DNSSEC chain at new registrar |

## Pre-flight: zone state and gather-info gate

Before running symptom-specific probes, gather the canonical hosted
zone configuration and short-circuit on zone states that mimic DNS
failures. Misclassifying these produces hours of debugging for a
problem that is not a DNS resolution problem.

### Account-wide pre-flight commands

```bash
# 1. List all hosted zones (public and private)
aws route53 list-hosted-zones --output json | \
  jq '.HostedZones[] | {Id, Name, PrivateZone, RecordSetCount}'

# 2. Get hosted zone details (including NS and SOA records)
aws route53 get-hosted-zone --id <zone-id> --output json

# 3. List all resource record sets in the zone
aws route53 list-resource-record-sets \
  --hosted-zone-id <zone-id> --output json

# 4. Get DNSSEC status for the zone
aws route53 get-dnssec --hosted-zone-id <zone-id> --output json

# 5. Check health check status
aws route53 get-health-check-status \
  --health-check-id <hc-id> --output json

# 6. Resolver endpoints (for hybrid DNS)
aws route53resolver list-resolver-endpoints --output json

# 7. AWS Health (regional events)
aws health describe-events --filter eventStatusCodes=OPEN,UPCOMING \
  --region us-east-1 --output json

# 8. Live DNS resolution (from a public resolver)
dig +trace +additional NS <domain> @8.8.8.8
dig +dnssec +multi <domain> @8.8.8.8
```

### Zone-state short-circuit

| Configuration field | Effect on diagnosis |
|---|---|
| `Config.PrivateZone: true` but no VPC associations | Private zone has no VPC to serve queries from. Resolution fails from all locations. |
| `Config.PrivateZone: false` but registrar NS not updated | Public zone exists but the TLD does not delegate to it. Resolution fails globally. |
| DNSSEC enabled but `KeySigningKeys[].KeyTag` does not match parent DS | Validating resolvers return SERVFAIL. |
| Health check `Status: Unhealthy` on a PRIMARY failover record | DNS suppresses the PRIMARY record; returns SECONDARY or nothing. |
| Multiple zones for the same domain name (public + private) | Split-horizon DNS; private zone wins inside the VPC. |

### Delegation / record-set pre-flight

| Field | Effect |
|---|---|
| Hosted zone NS records differ from registrar NS records | Delegation chain is broken. Resolution may work intermittently or fail entirely. |
| SOA serial does not increment after a change | Indicates the change was not committed (rare in Route 53) or the secondary zones (if any) are not transferring. |
| Alias record and CNAME for the same name | Cannot coexist. Route 53 rejects the change with `ConflictingDomainExists`. |
| `TTL: 86400` on the old record | Changes take up to 24 hours to propagate from caches. Wait 2x TTL before declaring failure. |

If the input is malformed (missing domain name or zone ID, absent
symptom description, no dig output for offline diagnosis), emit:

```text
TARGET: <domain-name or unknown>
VERDICT: INSUFFICIENT_DATA
REASON: Input is missing required context — at minimum a domain name
  and a symptom description (NXDOMAIN, wrong IP, SERVFAIL, etc.).
LAYER: UNKNOWN
EVIDENCE:
  - Missing: <list specific missing fields>
REMEDIATION: Re-prompt the operator for: (1) the domain name being
  queried, (2) the observed symptom (NXDOMAIN, wrong IP, SERVFAIL,
  intermittent), (3) the expected resolution result, and (4) for
  live diagnosis, the HostedZoneId and whether the zone is public or
  private.
```

## Process — Diagnostic decision tree (apply in symptom order)

The diagnostic tree is symptom-driven. Pick the entry point based on the
observed symptom, then walk the layer-specific probes in order. Each layer
ends with either a positive root-cause confirmation (failing probe that
matches the symptom) or a pass that moves to the next layer. **Never emit
ROOT_CAUSE_IDENTIFIED without a failing probe that matches the symptom.**

### Step 0: Non-obvious behaviours that change diagnosis

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

### Step 1: Symptom entry — pick the diagnostic branch

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

### Step 2: NS delegation — the four-link chain

Symptom: `NXDOMAIN` for a domain that has records in the hosted zone.
The domain does not resolve because the TLD servers do not delegate to
the Route 53 hosted zone's NS servers.

```bash
# Get the hosted zone's assigned NS servers
aws route53 list-resource-record-sets \
  --hosted-zone-id <zone-id> --output json | \
  jq '.ResourceRecordSets[] | select(.Type == "NS") | .ResourceRecords[].Value'

# Check what the TLD servers see (via a public resolver)
dig +trace +additional NS <domain> @8.8.8.8

# Check the registrar's NS records
dig NS <domain> @8.8.8.8 +short
```

The delegation chain:

```
Root servers (a.root-servers.net)
  -> TLD servers (.com, .io, etc.)
    -> Registrar NS records (set at the domain registrar)
      -> Hosted zone NS records (Route 53 assigned NS)
```

| Mismatch | Effect |
|---|---|
| Registrar NS != hosted zone NS | TLD delegates to wrong NS; queries hit stale or no zone. |
| Registrar NS is empty | TLD has no delegation; NXDOMAIN everywhere. |
| Registrar NS points at old DNS provider | Domain resolves old records (from the previous provider). |
| Glue records missing (for custom NS names under the same domain) | TLD cannot resolve the NS hostnames; delegation fails. |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: NS_DELEGATION` (NS mismatch)
or `GLUE_RECORD` (glue records missing for custom NS hostnames).

Fix: update the registrar's NS records to match the Route 53 hosted
zone's NS servers.

### Step 3: DNSSEC — KSK, ZSK, and DS record

Symptom: `SERVFAIL` from validating resolvers; intermittent resolution
("works on some networks, fails on others").

```bash
# Get DNSSEC status for the zone
aws route53 get-dnssec --hosted-zone-id <zone-id> --output json

# Check the DS record at the parent (via a public resolver)
dig +dnssec DS <domain> @8.8.8.8 +short

# Check the DNSKEY records (KSK and ZSK)
dig +dnssec DNSKEY <domain> @8.8.8.8 +short
```

| Condition | Diagnosis |
|---|---|
| DNSSEC enabled, KSK `KeyState: KEY_NOT_PUBLISHED` | KSK not yet active. Wait for key propagation (minutes to hours). |
| KSK active but DS record missing at parent | Chain of trust broken. Validating resolvers return SERVFAIL. Fix: establish DS record at the registrar. |
| DS record at parent does not match KSK (wrong algorithm, digest, or key tag) | Stale DS record after KSK rotation. Fix: update DS at registrar with the current KSK's DS values. |
| ZSK `KeyState: KEY_NOT_PUBLISHED` | Zone is not being signed. Records have no RRSIG. Fix: wait for ZSK to propagate. |
| DNSSEC was disabled but DS record remains at parent | "Leftover DS" causes validating resolvers to attempt validation on an unsigned zone. SERVFAIL. Fix: remove DS at registrar. |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: DNSSEC_KSK` (KSK issue),
`DNSSEC_ZSK` (ZSK issue), or `DNSSEC_DS` (DS record at parent issue).

### Step 4: DNS cache / TTL

Symptom: wrong (stale) IP returned after a record change. The change is
in the hosted zone but resolvers are still serving the old cached value.

```bash
# Query the authoritative server directly (bypass all caches)
dig <domain> @<route53-ns-server> +short

# Query a public resolver
dig <domain> @8.8.8.8 +short

# Query the local system resolver
dig <domain> +short
```

If the authoritative server returns the new value but public resolvers
return the old value, the issue is TTL-based caching. Wait 2x the old
TTL. If the authoritative server returns the old value, the change was
not committed (verify with `list-resource-record-sets`).

| Scenario | Diagnosis |
|---|---|
| Authoritative returns new, public resolver returns old | TTL caching. Wait 2x old TTL. |
| Authoritative returns old | Change not committed. Verify `list-resource-record-sets`. |
| Some public resolvers return new, others return old | Different resolvers cached at different times. Wait for TTL expiry. |
| Local resolver returns old but public resolver returns new | Local DNS cache (OS or browser). Flush local cache. |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: DNS_CACHE_TTL`.

### Step 5: Alias vs CNAME conflict

Symptom: attempting to create an ALIAS record fails with
`ConflictingDomainExists` or `InvalidChangeBatch`.

```bash
# List existing records for the name
aws route53 list-resource-record-sets \
  --hosted-zone-id <zone-id> --output json | \
  jq '.ResourceRecordSets[] | select(.Name == "<name>")'
```

A name can have only ONE record type (with exceptions for specific
combinations). The conflict matrix:

| Existing record | New record | Conflict? |
|---|---|---|
| CNAME | ALIAS (to any target) | YES — cannot coexist |
| ALIAS | CNAME | YES — cannot coexist |
| A | ALIAS (to A-target) | YES — cannot coexist |
| ALIAS (A) | ALIAS (AAAA) | NO — can coexist (one A alias, one AAAA alias) |
| MX, TXT, NS | ALIAS or CNAME | NO — these types can coexist with each other but not with CNAME/ALIAS |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: ALIAS_CNAME_CONFLICT`. Fix:
delete the conflicting record before creating the new one.

### Step 6: Routing policy evaluation

Symptom: routing policy (geolocation, latency, weighted, failover) does
not resolve as expected.

#### 6a: Geolocation

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

#### 6b: Latency

| Check | Expected |
|---|---|
| Each latency record has a `Region` (AWS region code) | At least two records in different regions |
| `RoutingPolicy: latency` on all records for the name | All records for the same name use latency routing |

Common error: only one region has a record -> all queries go to that
region regardless of user location.

#### 6c: Weighted

| Check | Expected |
|---|---|
| Each weighted record has a `Weight` (integer >= 0) | Weights are relative; a record with weight 0 gets no traffic |
| `RoutingPolicy: weighted` on all records for the name | All records for the same name use weighted routing |
| Health check on each weighted record | Unhealthy records are suppressed (weight effectively 0) |

Common error: one record has `Weight: 0` (intentional drain or
accidental).

#### 6d: Failover

| Check | Expected |
|---|---|
| PRIMARY record has `Failover: PRIMARY` and `HealthCheckId` | PRIMARY is the active record when healthy |
| SECONDARY record has `Failover: SECONDARY` | SECONDARY takes over when PRIMARY is unhealthy |
| Health check endpoint is correct | See Step 7 |

Common error: health check is failing, so PRIMARY is always suppressed
(see Step 7).

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: ROUTING_GEOLOCATION` /
`ROUTING_LATENCY` / `ROUTING_WEIGHTED` / `ROUTING_FAILOVER`.

### Step 7: Health check failing

Symptom: failover record always returns SECONDARY; weighted record
receives no traffic; multi-value answer excludes the record.

```bash
aws route53 get-health-check-status \
  --health-check-id <hc-id> --output json

aws route53 get-health-check \
  --health-check-id <hc-id> --output json | \
  jq '.HealthCheckConfig'
```

| Check | Expected |
|---|---|
| `HealthCheckConfig.Type` | `HTTPS`, `HTTP`, `TCP`, `HTTPS_STR_MATCH`, `CALCULATED` |
| `HealthCheckConfig.FullyQualifiedDomainName` or `IPAddress` | The endpoint being monitored |
| `HealthCheckConfig.Port` | 443 for HTTPS, 80 for HTTP, or custom |
| `HealthCheckConfig.ResourcePath` | The path being checked (e.g., `/health`) |
| `Status` | `Healthy` or `Unhealthy` |
| `StatusReport.CheckedTime` | Recent timestamp (health check is actively running) |

Common failure patterns:

| Pattern | Cause |
|---|---|
| Health check monitors the Route 53 record itself instead of the endpoint | Circular dependency. Fix: monitor the endpoint IP or ALB DNS directly. |
| `ResourcePath: /health` but the endpoint does not serve `/health` | 404 or connection refused. Fix: correct the path. |
| Health check monitors `HTTP` but endpoint redirects to `HTTPS` | Health check sees 301/302 as unhealthy (expects 2xx/3xx). Fix: use HTTPS type, or enable `EnableSNI`. |
| `Type: CALCULATED` with all child checks unhealthy | Calculated health check returns unhealthy. Fix: fix child health checks. |
| Health check in a different region than the endpoint | Latency-based false negatives. Consider CloudWatch alarm-based health checks for cross-region. |
| `InsufficientDataHealthStatus: Healthy` on CloudWatch alarm health check | CloudWatch alarm has insufficient data; health check defaults to healthy. |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: HEALTH_CHECK`.

### Step 8: Private hosted zone VPC association

Symptom: private hosted zone does not resolve from instances in a VPC.

```bash
aws route53 get-hosted-zone --id <zone-id> --output json | \
  jq '.VPCs'

aws route53 list-vpc-association-authorizations \
  --hosted-zone-id <zone-id> --output json

aws ec2 describe-dhcp-options \
  --dhcp-options-ids <dhcp-options-id> --output json | \
  jq '.DhcpOptions.DhcpConfigurations'
```

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

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: PHZ_VPC_ASSOCIATION`.

### Step 9: Split-horizon DNS

Symptom: same domain resolves differently inside vs outside the VPC.

```bash
# Check for both public and private zones with the same name
aws route53 list-hosted-zones --output json | \
  jq '.HostedZones[] | select(.Name == "<domain>.") | {Id, Name, PrivateZone}'
```

If both a public and a private zone exist for the same domain:
- Queries from the VPC (associated with the private zone) resolve the
  private zone's records.
- Queries from the internet resolve the public zone's records.

This is intentional for split-horizon DNS. If it is NOT intended, either
delete the private zone or rename the private zone (e.g.,
`internal.example.com`).

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: SPLIT_HORIZON`.

### Step 10: Resolver inbound endpoint

Symptom: on-premises DNS resolvers cannot resolve Route 53 private
hosted zones. Queries from on-premises time out.

```bash
aws route53resolver list-resolver-endpoints \
  --filters Name=Direction,Values=INBOUND --output json

aws route53resolver get-resolver-endpoint \
  --resolver-endpoint-id <endpoint-id> --output json

# Check Security Groups on the inbound endpoint ENIs
aws ec2 describe-security-groups \
  --group-ids <sg-ids> --output json | \
  jq '.SecurityGroups[].IpPermissions'
```

| Check | Expected |
|---|---|
| Inbound endpoint `Status: OPERATIONAL` | If `CREATING` or `ACTION_NEEDED`, wait or fix the issue |
| Inbound endpoint has ENIs in the subnets reachable from on-premises | ENI IPs must be routable from on-premises |
| Security Group allows inbound UDP/TCP 53 from on-premises CIDR | DNS traffic allowed |
| On-premises forwarder points at the inbound endpoint IPs | Conditional forwarder or secondary zone configured |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: RESOLVER_INBOUND`.

### Step 11: Resolver outbound endpoint

Symptom: VPC instances cannot resolve on-premises DNS names.

```bash
aws route53resolver list-resolver-endpoints \
  --filters Name=Direction,Values=OUTBOUND --output json

aws route53resolver list-resolver-rules --output json

aws route53resolver list-resolver-rule-associations --output json
```

| Check | Expected |
|---|---|
| Outbound endpoint `Status: OPERATIONAL` | If not operational, fix endpoint |
| Resolver rule matches the on-premises domain | `DomainName` in the rule must match the domain being queried |
| Resolver rule is `ASSOCIATED` with the VPC | If `NOT_ASSOCIATED`, associate it |
| Outbound endpoint SG allows outbound UDP/TCP 53 to on-premises DNS | Egress allowed |
| Rule `TargetIps` point at the correct on-premises DNS servers | IPs and port correct |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: RESOLVER_OUTBOUND`.

### Step 12: Wildcard certificate validation CNAME conflict

Symptom: ACM certificate validation fails or a certificate stops renewing.
The `_acme-challenge` or `_<hash>` CNAME record conflicts with an
existing wildcard CNAME.

```bash
aws route53 list-resource-record-sets \
  --hosted-zone-id <zone-id> --output json | \
  jq '.ResourceRecordSets[] | select(.Type == "CNAME") | select(.Name | test("_acme-challenge|^[*_]"))'

dig CNAME _<hash>.<domain> @8.8.8.8 +short
```

If a wildcard CNAME `*.example.com` exists and ACM creates a validation
CNAME `_abc123.example.com`, Route 53 returns the wildcard CNAME
instead of the validation CNAME. This prevents ACM from validating or
renewing the certificate.

Fix: delete the wildcard CNAME, or use a more specific CNAME that does
not conflict with the ACM validation record.

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: WILDCARD_CERT`.

### Step 12b: Domain transfer DNS disruption

Symptom: SERVFAIL or NXDOMAIN after a domain transfer between registrars.

```bash
# Check NS records at the TLD
dig NS <domain> @8.8.8.8 +short

# Check DS record (DNSSEC) at the TLD
dig +dnssec DS <domain> @8.8.8.8 +short
```

During a domain transfer:
1. The NS records change from the old registrar's delegation to the new
   registrar's delegation.
2. If DNSSEC was enabled, the DS record must be re-established at the
   new registrar.
3. A gap between NS change and DS establishment causes SERVFAIL on
   validating resolvers.

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: DOMAIN_TRANSFER`.

### Step 13: INSUFFICIENT_DATA

If none of the above produced a positive root-cause match, OR the symptom
clearly indicates an AWS-side incident (regional Route 53 outage),
emit INSUFFICIENT_DATA with a list of missing information and the next
probes to run.

## Output format

```text
TARGET: <domain-name / zone-id / health-check-id>
VERDICT: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
REASON: <1-2 sentences naming the failed layer and the failing probe>
LAYER: <NS_DELEGATION | GLUE_RECORD | SOA_SERIAL |
        DNSSEC_KSK | DNSSEC_ZSK | DNSSEC_DS |
        ALIAS_CNAME_CONFLICT |
        ROUTING_POLICY | ROUTING_GEOLOCATION |
        ROUTING_LATENCY | ROUTING_WEIGHTED |
        ROUTING_FAILOVER |
        PHZ_VPC_ASSOCIATION | SPLIT_HORIZON |
        RESOLVER_INBOUND | RESOLVER_OUTBOUND |
        HEALTH_CHECK | DNS_CACHE_TTL |
        DOMAIN_TRANSFER | WILDCERT_CERT |
        UNKNOWN>
EVIDENCE:
  - <observed symptom — error string or behaviour>
  - <failing probe — command and its output that confirms the cause>
  - <passing probes — layers ruled out>
REMEDIATION:
  1. <specific action with CLI command>
  2. <verification command after the fix>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <zone / domain> in <region>.
  Proceed? (yes/no)"
```

### Worked example — NS delegation mismatch

```text
TARGET: api.example.com (zone Z2ABCDEFGHIJ)
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: The hosted zone NS servers are
  ns-1.awsdns.com, ns-2.awsdns.net, ns-3.awsdns.org, ns-4.awsdns.co.uk
  but the registrar (GoDaddy) has NS records pointing at
  ns-old.provider.net, ns-old2.provider.net. The delegation chain is
  broken — TLD servers delegate to the old provider, not Route 53
  (Step 2).
LAYER: NS_DELEGATION
EVIDENCE:
  - Symptom: api.example.com returns NXDOMAIN from all public
    resolvers, but list-resource-record-sets shows a valid A record
    (ALIAS to ALB) in the hosted zone.
  - Probe: dig +trace NS example.com @8.8.8.8 shows TLD delegation
    to ns-old.provider.net, not Route 53 NS servers.
  - Probe: aws route53 list-resource-record-sets returns NS records:
    ns-1.awsdns.com, ns-2.awsdns.net, ns-3.awsdns.org, ns-4.awsdns.co.uk.
  - Passing: the A record exists in the zone (confirmed via dig against
    ns-1.awsdns.com directly); DNSSEC is not enabled (no SERVFAIL
    risk); no private zone for the same domain.
REMEDIATION:
  1. Update the registrar (GoDaddy) NS records to match the Route 53
     hosted zone NS servers:
     ns-1.awsdns.com, ns-2.awsdns.net, ns-3.awsdns.org,
     ns-4.awsdns.co.uk
  2. Verify after 24-48 hours (TLD TTL is typically 48 hours):
     dig NS example.com @8.8.8.8 +short
     dig api.example.com @8.8.8.8 +short
CONFIRM: Before updating NS at the registrar, emit and await:
  "CONFIRM: About to update NS delegation for example.com at GoDaddy.
   Proceed? (yes/no)"
```

### Worked example — DNSSEC DS record mismatch

```text
TARGET: app.example.com (zone Z3DEFGHIJKL)
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: DNSSEC is enabled on the hosted zone with KSK key tag 12345,
  but the DS record at the parent zone has key tag 67890 (from a
  previous KSK rotation). Validating resolvers return SERVFAIL because
  the chain of trust is broken (Step 3).
LAYER: DNSSEC_DS
EVIDENCE:
  - Symptom: app.example.com returns SERVFAIL from Cloudflare DNS
    (1.1.1.1, validating) but resolves correctly from a non-validating
    resolver.
  - Probe: dig +dnssec DS example.com @8.8.8.8 +short returns key tag
    67890.
  - Probe: aws route53 get-dnssec returns KeySigningKeys[0].KeyTag:
    12345.
  - Passing: ZSK is active (KeyState: INACTIVE -> NSEC signing);
    NS delegation is correct (dig +trace resolves to Route 53 NS).
REMEDIATION:
  1. Update the DS record at the registrar (Route 53 Registrar) to
     match the current KSK:
     aws route53 update-domain-nameservers is NOT the right call;
     use the registrar's DNSSEC management interface or API:
     aws route53 associate-dnssec --domain-name example.com (if
     Route 53 Registrar) with the current KSK DS values.
  2. Verify after DS propagation (TLD DS TTL, typically 24 hours):
     dig +dnssec DS example.com @8.8.8.8 +short
     dig +dnssec app.example.com @1.1.1.1 (should resolve without
     SERVFAIL; check AD bit is set)
```

### Worked example — Private hosted zone VPC association

```text
TARGET: internal.example.com (zone Z4EFGHIJKLM, private)
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: The private hosted zone internal.example.com is not associated
  with VPC vpc-abc123. Queries from EC2 instances in vpc-abc123
  resolve the public internet instead of the private zone, returning
  NXDOMAIN for internal service names (Step 8).
LAYER: PHZ_VPC_ASSOCIATION
EVIDENCE:
  - Symptom: EC2 instances in vpc-abc123 cannot resolve
    db.internal.example.com; dig returns NXDOMAIN.
  - Probe: aws route53 get-hosted-zone --id Z4EFGHIJKLM returns
    VPCs: [] (empty — no VPC associations).
  - Probe: dig db.internal.example.com @169.254.169.253 returns
    NXDOMAIN (AmazonProvidedDNS has no private zone to answer from).
  - Passing: the record exists in the zone (confirmed via
    list-resource-record-sets); NS delegation is N/A (private zone);
    DHCP Options Set for vpc-abc123 uses AmazonProvidedDNS.
REMEDIATION:
  1. Associate the VPC with the private hosted zone:
     aws route53 associate-vpc-with-hosted-zone \
       --hosted-zone-id Z4EFGHIJKLM \
       --vpc VPCRegion=us-east-1,VPCId=vpc-abc123 \
       --profile <p>
  2. Verify from an EC2 instance in vpc-abc123:
     dig db.internal.example.com @169.254.169.253 +short
CONFIRM: Before associating the VPC, emit and await:
  "CONFIRM: About to associate vpc-abc123 with private zone
   Z4EFGHIJKLM (internal.example.com). Proceed? (yes/no)"
```

## Anti-Patterns — NEVER

- NEVER declare ROOT_CAUSE_IDENTIFIED without a failing probe that
  matches the symptom. A "process of elimination" diagnosis erodes
  operator trust when the real cause is elsewhere.

- NEVER edit a record without verifying the NS delegation chain first.
  If the registrar NS does not match the hosted zone NS, no record
  change will take effect. Always verify delegation with
  `dig +trace NS` before touching records.

- NEVER disable DNSSEC to "fix" SERVFAIL without identifying the root
  cause. The SERVFAIL means the DS record at the parent does not match
  the KSK. Fix the DS record. Disabling DNSSEC leaves the DS record at
  the parent, causing SERVFAIL on all queries (the resolver tries to
  validate an unsigned zone against the leftover DS).

- NEVER assume a record change is not propagating because of Route 53.
  Route 53 propagates changes within 60 seconds to its global network.
  Apparent "slow propagation" is almost always TTL-based caching at
  downstream resolvers. Wait 2x the old TTL before declaring failure.

- NEVER create a CNAME and an ALIAS for the same name. Route 53 rejects
  the change with `ConflictingDomainExists`. Delete the conflicting
  record first.

- NEVER assume private hosted zones resolve from all VPCs by default.
  Each VPC must be explicitly associated. Cross-account associations
  require authorization in both accounts.

- NEVER set a health check to monitor the Route 53 record itself (the
  domain name being routed). This creates a circular dependency — the
  health check depends on the record, and the record depends on the
  health check. Always monitor the endpoint (IP, ALB DNS) directly.

- NEVER assume `dig` output is definitive without specifying the
  resolver. Local system resolvers and browsers cache aggressively.
  Always use `dig @<resolver>` to bypass local caches.

- NEVER assume weighted routing distributes evenly. The distribution
  is proportional to weight values. A record with weight 1 and another
  with weight 99 means the first gets ~1% of traffic, not 50%.

- NEVER assume latency routing is based on the user's geographic
  location. It is based on the latency between the user's nearest AWS
  region and the record's region. A user in Tokyo querying a latency
  record in `us-east-1` and `ap-northeast-1` gets `ap-northeast-1`
  because the latency from Tokyo to `ap-northeast-1` is lower.

- NEVER forget to remove the DS record at the parent after disabling
  DNSSEC. A leftover DS record causes SERVFAIL on validating resolvers
  indefinitely.

- NEVER use a wildcard CNAME (`*.example.com`) if ACM certificate
  validation CNAMEs exist in the same zone. The wildcard intercepts
  the validation query and the certificate fails to renew.

- NEVER transfer a domain between registrars without first planning
  the DNSSEC transition. Disable DNSSEC (and remove the DS record) at
  the old registrar BEFORE initiating the transfer, then re-enable at
  the new registrar after the transfer completes.

## Pre-flight safety checks (run before any state-changing CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`change-resource-record-sets`, `associate-vpc-with-hosted-zone`,
  `change-tags-for-resource`, `update-health-check`,
  `disassociate-vpc-from-hosted-zone`, DNSSEC enable/disable), emit
  and await operator approval.

- **Read-only first.** Every probe in the diagnostic tree is
  read-only (`list-hosted-zones`, `get-hosted-zone`,
  `list-resource-record-sets`, `get-dnssec`, `get-health-check`,
  `get-health-check-status`, `list-resolver-endpoints`,
  `list-resolver-rules`, `dig`, `nslookup`). Do not perform
  state-changing operations as diagnostic probes.

- **`change-resource-record-sets`** is the primary state-changing
  command. Use UPSERT (not CREATE) to avoid failures if the record
  already exists. Always confirm the record set before applying.

- **`associate-vpc-with-hosted-zone`** enables private zone resolution
  for the VPC. If the zone name overlaps with a public zone, the
  private zone takes precedence in the VPC (split-horizon). Confirm
  this is intended.

- **DNSSEC enable/disable** is a multi-step process. Enabling DNSSEC
  generates KSK and ZSK, but the DS record must be established at the
  parent registrar separately. Disabling DNSSEC removes signing but
  leaves the DS record at the parent until explicitly removed.

- **NS record changes** at the registrar can take 24-48 hours to
  propagate through the TLD. Plan the change during a maintenance
  window and have a rollback plan (old NS values documented).

- **Bulk remediation batch limit.** If the diagnosis identifies the
  same root cause across multiple zones (e.g., stale DS records after
  a KSK rotation), batch remediation into groups of at most 5 zones,
  emit a single CONFIRM per batch, and verify between batches.

## Remediation guidance

### For NS_DELEGATION

Update the registrar's NS records to match the Route 53 hosted zone NS
servers. This is done at the registrar's console or API, not via the
Route 53 API (unless using Route 53 Registrar):

```bash
# If using Route 53 Registrar:
aws route53domains update-domain-nameservers \
  --domain-name <domain> \
  --nameservers Name=ns-1.awsdns.com Name=ns-2.awsdns.net \
                Name=ns-3.awsdns.org Name=ns-4.awsdns.co.uk \
  --profile <p>
```

### For DNSSEC_DS

Establish or update the DS record at the parent registrar:

```bash
# Get the DS values from the hosted zone KSK
aws route53 get-dnssec --hosted-zone-id <zone-id> --output json | \
  jq '.KeySigningKeys[0].DS'

# If using Route 53 Registrar:
aws route53domains associate-dnssec \
  --domain-name <domain> \
  --dnssec-key <ds-values-from-above> \
  --profile <p>
```

### For DNSSEC_KSK / DNSSEC_ZSK

```bash
# Enable DNSSEC signing (generates KSK and ZSK)
aws route53 enable-dnssec --hosted-zone-id <zone-id> --profile <p>

# Disable DNSSEC signing (removes KSK and ZSK — also remove DS at parent)
aws route53 disable-dnssec --hosted-zone-id <zone-id> --profile <p>
```

### For DNS_CACHE_TTL

No CLI fix. Wait 2x the old TTL. For urgent changes, consider lowering
the TTL BEFORE making future changes (set TTL to 60 seconds, wait for
old TTL to expire, make the change).

### For ALIAS_CNAME_CONFLICT

Delete the conflicting record, then create the new one:

```bash
aws route53 change-resource-record-sets \
  --hosted-zone-id <zone-id> \
  --change-batch '{
    "Changes": [
      {"Action": "DELETE", "ResourceRecordSet": {"Name": "<name>", "Type": "CNAME", ...}},
      {"Action": "CREATE", "ResourceRecordSet": {"Name": "<name>", "Type": "A", "AliasTarget": {...}}}
    ]
  }' --profile <p>
```

### For PHZ_VPC_ASSOCIATION

```bash
aws route53 associate-vpc-with-hosted-zone \
  --hosted-zone-id <zone-id> \
  --vpc VPCRegion=<region>,VPCId=<vpc-id> \
  --profile <p>
```

For cross-account:

```bash
# In the zone account:
aws route53 create-vpc-association-authorization \
  --hosted-zone-id <zone-id> \
  --vpc VPCRegion=<region>,VPCId=<vpc-id> \
  --profile <zone-account>

# In the VPC account:
aws route53 associate-vpc-with-hosted-zone \
  --hosted-zone-id <zone-id> \
  --vpc VPCRegion=<region>,VPCId=<vpc-id> \
  --profile <vpc-account>
```

### For HEALTH_CHECK

```bash
# Update the health check endpoint
aws route53 update-health-check \
  --health-check-id <hc-id> \
  --fully-qualified-domain-name <endpoint> \
  --resource-path /health \
  --port 443 \
  --type HTTPS \
  --profile <p>
```

### For RESOLVER_INBOUND

Verify the inbound endpoint SG allows UDP/TCP 53 from on-premises CIDR.
If the SG is restrictive, add an inbound rule:

```bash
aws ec2 authorize-security-group-ingress \
  --group-id <sg-id> \
  --protocol udp --port 53 \
  --cidr <on-prem-cidr> \
  --profile <p>

aws ec2 authorize-security-group-ingress \
  --group-id <sg-id> \
  --protocol tcp --port 53 \
  --cidr <on-prem-cidr> \
  --profile <p>
```

### For RESOLVER_OUTBOUND

Associate the resolver rule with the VPC:

```bash
aws route53resolver associate-resolver-rule \
  --resolver-rule-id <rule-id> \
  --vpc-id <vpc-id> \
  --profile <p>
```

### For WILDCARD_CERT

Delete the wildcard CNAME that intercepts ACM validation:

```bash
aws route53 change-resource-record-sets \
  --hosted-zone-id <zone-id> \
  --change-batch '{
    "Changes": [
      {"Action": "DELETE", "ResourceRecordSet": {"Name": "*.example.com.", "Type": "CNAME", "TTL": 300, "ResourceRecords": [{"Value": "<old-target>"}]}}
    ]
  }' --profile <p>
```

## Deep reference: Route 53 DNS resolution layer model

### Symptom -> layer decision matrix (offline classification)

```
Error string / behaviour                            → Layer
NXDOMAIN (domain does not exist)                     → NS_DELEGATION / GLUE_RECORD
SERVFAIL (intermittent, validating resolvers only)   → DNSSEC_DS / DNSSEC_KSK / DNSSEC_ZSK
Wrong IP (stale after change)                        → DNS_CACHE_TTL
ConflictingDomainExists on record create             → ALIAS_CNAME_CONFLICT
Geolocation returns NXDOMAIN from some regions       → ROUTING_GEOLOCATION (no default record)
Weighted sends all traffic to one record             → ROUTING_WEIGHTED (weight: 0 on others)
Failover always returns SECONDARY                    → HEALTH_CHECK / ROUTING_FAILOVER
Private zone not resolving from VPC                  → PHZ_VPC_ASSOCIATION
Same domain, different IP inside vs outside VPC      → SPLIT_HORIZON
On-prem cannot resolve private zone                  → RESOLVER_INBOUND
VPC cannot resolve on-prem DNS                       → RESOLVER_OUTBOUND
ACM cert validation fails / stops renewing           → WILDCERT_CERT
SERVFAIL after domain transfer                       → DOMAIN_TRANSFER
```

### NS delegation chain reference

```
dig +trace example.com @8.8.8.8

Step 1: Root servers (a-m.root-servers.net)
  -> Refers to TLD servers

Step 2: TLD servers (.com: a-m.gtld-servers.net)
  -> Refers to registrar NS records

Step 3: Registrar NS (set at the domain registrar)
  -> Must match hosted zone NS (Route 53 assigned)

Step 4: Hosted zone NS (ns-X.awsdns-*.com/net/org/co.uk)
  -> Authoritative for the domain
  -> Serves all record sets
```

### DNSSEC key hierarchy

```
Root zone (root key / trust anchor)
  |
  +-> DS record at TLD (.com, .io, etc.)
      |
      +-> DS record at registrar zone (parent of your domain)
          |
          +-> KSK (Key Signing Key) — signs the DNSKEY RRset
              |
              +-> ZSK (Zone Signing Key) — signs all other RRsets
                  |
                  +-> RRSIG on each record (A, AAAA, MX, etc.)
```

### DNSSEC key states in Route 53

| State | Meaning |
|---|---|
| `KEY_NOT_PUBLISHED` | Key generated but not yet published in the zone |
| `KEY_PUBLISHED` | Key is in the zone but not yet used for signing |
| `INACTIVE` | Key is published but not used for signing (transition state) |
| `ACTIVE` | Key is actively signing the zone |

### Routing policy reference

| Policy | How it works | Requires per record |
|---|---|---|
| Simple | One record, one value (or multiple values returned in random order) | Nothing special |
| Weighted | Traffic split by weight (relative proportions) | `Weight` (integer >= 0) |
| Latency | Route to lowest-latency region | `Region` (AWS region code) |
| Failover | PRIMARY when healthy, SECONDARY when not | `Failover` (PRIMARY/SECONDARY), `HealthCheckId` on PRIMARY |
| Geolocation | Route by user location (continent/country/subdivision) | `GeoLocation` (ContinentCode/CountryCode/SubdivisionCode) |
| Geoproximity | Route by geographic distance (bias adjustable) | `GeoLocation` + `Bias` |
| Multi-value answer | Return up to 8 healthy records randomly | `HealthCheckId` (optional per record) |
| IP-based routing | Route by client IP CIDR blocks | `CidrRoutingConfig` |

### TTL reference

| Record type | Recommended TTL | Notes |
|---|---|---|
| NS | 172800 (48 hours) | TLD-level caching; changes are slow |
| SOA | 900 (15 minutes) | Includes serial, refresh, retry, expiry |
| A / AAAA (stable) | 3600 (1 hour) | Balance between caching and change speed |
| A / AAAA (dynamic, failover) | 60 (1 minute) | Fast failover; higher query cost |
| MX | 3600 (1 hour) | Email routing changes need moderate propagation |
| TXT (SPF, DKIM) | 3600 (1 hour) | Email security records |
| CNAME | 300 (5 minutes) | Moderate; often used for validation |

### Resolver endpoint reference

| Property | Inbound endpoint | Outbound endpoint |
|---|---|---|
| Purpose | On-prem -> Route 53 (private zones) | VPC -> on-prem DNS |
| ENIs | One per subnet (min 2 subnets) | One per subnet (min 2 subnets) |
| SG requirement | Allow inbound UDP/TCP 53 | Allow outbound UDP/TCP 53 |
| On-prem config | Forward queries to inbound ENI IPs | Resolver rules with `TargetIps` = on-prem DNS |
| Min subnets | 2 (different AZs for HA) | 2 (different AZs for HA) |

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

## Domain

AWS CloudOps / Route 53 DNS, Resolution Diagnostics, DNSSEC, Hosted
Zone Delegation, Private Zones, Resolver Endpoints, and Health Check
Failover.

## AWS documentation

- **Route 53 Developer Guide** — https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/
- **Route 53 DNSSEC signing** — https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/dns-configuring-dnssec.html
- **Routing policies** — https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/routing-policy.html
- **Private hosted zones** — https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/hosted-zones-private.html
- **Route 53 Resolver** — https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver.html
- **Health checks** — https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/dns-failover.html
- **Alias records vs CNAME** — https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resource-record-sets-choosing-alias-non-alias.html
- **Resolver query logging** — https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver-query-logs.html
- **Domain registration and transfer** — https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/domain-register.html
- **AWS Health** — https://docs.aws.amazon.com/health/latest/ug/
