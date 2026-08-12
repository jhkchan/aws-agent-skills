---
description: Diagnoses Amazon Route 53 DNS resolution failures through a twelve-category diagnostic tree (NS delegation, DNSSEC, alias vs CNAME, routing policies, private hosted zone VPC association, split-horizon, Resolver endpoints, health checks, DNS cache, domain transfer, wildcard cert) — emits ROOT_CAUSE_IDENTIFIED with the specific failure layer or INSUFFICIENT_DATA.
nl_triggers:
  - "Route 53 DNS resolution failed"
  - "DNS does not resolve"
  - "DNS NXDOMAIN"
  - "DNS SERVFAIL"
  - "Route 53 NS delegation"
  - "Route 53 glue records"
  - "Route 53 NS mismatch"
  - "Route 53 DNSSEC"
  - "Route 53 KSK"
  - "Route 53 ZSK"
  - "Route 53 DS record"
  - "Route 53 alias CNAME conflict"
  - "Route 53 routing policy"
  - "Route 53 geolocation"
  - "Route 53 latency routing"
  - "Route 53 weighted routing"
  - "Route 53 failover routing"
  - "Route 53 private hosted zone"
  - "Route 53 VPC association"
  - "Route 53 split-horizon DNS"
  - "Route 53 Resolver endpoint"
  - "Route 53 health check failing"
  - "Route 53 DNS query logging"
  - "Route 53 domain transfer"
  - "Route 53 wildcard certificate"
  - "_acme-challenge CNAME"
  - "troubleshoot Route 53 DNS"
  - "DNS wrong IP"
routes_to: route53-dns-troubleshooter
---

# /aws:troubleshoot-route53-dns

Activate the `route53-dns-troubleshooter` skill and diagnose an Amazon
Route 53 DNS resolution failure through the twelve-category diagnostic
tree.

## What it does

Reads a symptom description (error message, dig output, observed
behaviour) plus the hosted zone configuration, then walks the
symptom-driven diagnostic tree to a root cause with positive evidence:

1. **Pre-flight** — hosted zone list (`list-hosted-zones`), zone details
   (`get-hosted-zone`), record sets (`list-resource-record-sets`),
   DNSSEC status (`get-dnssec`), health check status
   (`get-health-check-status`), Resolver endpoints
   (`list-resolver-endpoints`), AWS Health (regional incidents).
   Short-circuits on broken NS delegation, missing VPC associations,
   DNSSEC chain gaps, or AWS-side Route 53 service events.
2. **Symptom entry** — map the error to one of: NXDOMAIN (NS
   delegation), SERVFAIL (DNSSEC), wrong IP (DNS cache / TTL),
   ConflictingDomainExists (alias vs CNAME), routing policy evaluation
   (geolocation / latency / weighted / failover), private zone VPC
   association, split-horizon, Resolver inbound/outbound, health check
   failure, domain transfer disruption, wildcard cert validation
   conflict.
3. **Layer-specific probes** —
   - NS delegation: `dig +trace NS`, compare registrar NS vs hosted
     zone NS, glue record check.
   - DNSSEC: `get-dnssec` (KSK/ZSK status), `dig +dnssec DS` at parent,
     DS-to-KSK key tag comparison.
   - DNS cache: `dig @authoritative` vs `dig @8.8.8.8`, TTL analysis.
   - Alias vs CNAME: `list-resource-record-sets` for conflicting types.
   - Routing policy: geolocation (default record exists?), latency
     (region coverage), weighted (weight values, health checks),
     failover (PRIMARY health check status).
   - Private zone: `get-hosted-zone` VPCs list, DHCP Options Set,
     cross-account authorization.
   - Resolver: inbound endpoint SG (allow UDP/TCP 53), outbound
     endpoint rules and associations.
   - Health check: `get-health-check` config (endpoint, path, port),
     `get-health-check-status`, circular dependency detection.
   - Wildcard cert: `dig CNAME _acme-challenge`, wildcard CNAME
     interception.
   - Domain transfer: NS and DS at new registrar.
4. **Verdict** — ROOT_CAUSE_IDENTIFIED (with failing probe that matches
   the symptom) or INSUFFICIENT_DATA (a probe requires operator input,
   propagation wait, or AWS-side incident is suspected).

Emits a deterministic diagnostic block per target:

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
```

## When to invoke

Paste a symptom description and ask any of:

- "DNS returns NXDOMAIN for my domain"
- "DNS SERVFAIL on Cloudflare but works on Google DNS"
- "Route 53 failover always returns SECONDARY"
- "Private hosted zone not resolving from VPC"
- "ALIAS record creation fails with ConflictingDomainExists"
- "DNS still returns old IP after record change"
- "Geolocation routing returns wrong region"
- "On-premises cannot resolve Route 53 private zones"

A bare domain name + any DNS error verb ("domain not resolving",
"wrong IP", "SERVFAIL") also routes here via the orchestrator.

## Inputs

- Symptom description: error string (NXDOMAIN, SERVFAIL), observed
  behaviour (wrong IP, intermittent, only some resolvers), when it
  started.
- Zone configuration: HostedZoneId, domain name, private vs public,
  NS records, record sets, DNSSEC status, health checks.
- For live diagnosis: dig output (from multiple resolvers), VPC ID,
  DHCP Options Set, Resolver endpoint IDs. The skill uses
  `list-hosted-zones`, `get-hosted-zone`, `list-resource-record-sets`,
  `get-dnssec`, `get-health-check`, `get-health-check-status`,
  `list-resolver-endpoints`, `list-resolver-rules`,
  `list-resolver-rule-associations`, `describe-vpcs`,
  `describe-dhcp-options`, `dig`, `nslookup`.

## Outputs

- One diagnostic block per target domain / zone / health check.
- Layer-specific LAYER value from the enumerated set.
- Evidence section with the failing probe AND passing probes (layers
  ruled out) — never a verdict without positive evidence.
- Specific remediation: update registrar NS, update DS record, fix
  health check endpoint, associate VPC with private zone, delete
  conflicting CNAME, update routing policy, or AWS Support escalation.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 2 Troubleshoot specialist for Route 53 DNS resolution
  failures).
- `/aws:troubleshoot-vpc-connectivity` for deeper diagnosis when the
  DNS Resolver endpoint cannot reach on-premises DNS due to routing,
  NACL, or peering issues.
- `/aws:audit-acm-certificate` for certificate validation CNAME
  conflicts that cause ACM certificate renewal failures.
