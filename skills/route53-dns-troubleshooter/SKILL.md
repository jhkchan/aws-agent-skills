---
name: route53-dns-troubleshooter
description: 'Diagnoses Amazon Route 53 DNS resolution failures through a twelve-category diagnostic tree: NS delegation errors (glue records, NS mismatch between registrar and hosted zone), SOA serial mismatch, DNSSEC signing errors (KSK/ZSK key status, DS record at parent zone), alias record vs CNAME conflict, routing policy evaluation errors (geolocation, latency, weighted, failover), private hosted zone VPC association missing, split-horizon DNS conflicts, Route 53 Resolver inbound/outbound endpoint misconfiguration, health check associated with record but failing, DNS query logging analysis, domain transfer DNS disruption, and wildcard certificate validation CNAME (_acme-challenge) conflicts. Walks symptoms to a verified root cause with evidence-backed probes; emits ROOT_CAUSE_IDENTIFIED or INSUFFICIENT_DATA.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline symptom classification works from pasted error messages and hosted zone configuration. Live-account diagnosis uses aws route53 list-hosted-zones / get-hosted-zone / list-resource-record-sets / get-health-check / get-dnssec, aws route53resolver list-resolver-endpoints / list-resolver-rule-associations, aws ec2 describe-vpcs / describe-dhcp-options, aws logs filter-log-events (CloudWatch Logs for Route 53...
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Networking
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
  when_to_use: Diagnosing a Route 53 DNS resolution failure (NS delegation broken, DNSSEC signing error, alias vs CNAME conflict, routing policy not resolving as expected, private hosted zone not resolving in VPC, health check failing causing failover, Resolver endpoint misconfiguration, split-horizon DNS conflict, domain transfer disruption, wildcard certificate validation CNAME conflict), walking a symptom to the failed layer with verify and fix commands, validating why a domain does not resolve, or triaging a "DNS is broken" page where the root cause may be delegation, DNSSEC, record config, VPC association, health check, or Resolver — not necessarily the application or the web server.
  when_not_to_use: Application-level HTTP errors once DNS resolves correctly (use the application logs and alb-unhealthy-target-troubleshooter), CDN/CloudFront cache behaviour (use the CloudFront distribution logs), TLS handshake errors after DNS resolves (use acm-certificate-expiry-auditor), or VPC subnet routing / NACL posture audits (use ec2-security-group-auditor). This skill diagnoses DNS resolution-time failures; it does not audit steady-state network posture or tune application delivery.
  activation_triggers: Route 53 DNS resolution failed, DNS does not resolve, Route 53 NS delegation, Route 53 glue records, Route 53 NS mismatch, Route 53 DNSSEC, Route 53 KSK, Route 53 ZSK, Route 53 DS record, Route 53 alias record CNAME conflict, Route 53 routing policy, Route 53 geolocation routing, Route 53 latency routing, Route 53 weighted routing, Route 53 failover routing, Route 53 private hosted zone, Route 53 VPC association, Route 53 split-horizon DNS, Route 53 Resolver endpoint, Route 53 health check failing, Route 53 DNS query logging, Route 53 domain transfer, Route 53 wildcard certificate, _acme-challenge CNAME, troubleshoot Route 53 DNS, DNS NXDOMAIN, DNS SERVFAIL
  invocation_schema: 'Input: either (a) a symptom description (error message, observed behaviour, "domain does not resolve", "DNS returns wrong IP"), optionally paired with the hosted zone configuration and dig output, OR (b) a HostedZoneId / domain name plus resolver context (VPC, resolver endpoint, client region) for live-account diagnosis. Output: a deterministic TARGET/VERDICT/REASON/LAYER/EVIDENCE/REMEDIATION block where VERDICT ∈ {ROOT_CAUSE_IDENTIFIED, INSUFFICIENT_DATA} and LAYER ∈ {NS_DELEGATION, GLUE_RECORD, SOA_SERIAL, DNSSEC_KSK, DNSSEC_ZSK, DNSSEC_DS, ALIAS_CNAME_CONFLICT, ROUTING_POLICY, ROUTING_GEOLOCATION, ROUTING_LATENCY, ROUTING_WEIGHTED, ROUTING_FAILOVER, PHZ_VPC_ASSOCIATION, SPLIT_HORIZON, RESOLVER_INBOUND, RESOLVER_OUTBOUND, HEALTH_CHECK, DNS_CACHE_TTL, DOMAIN_TRANSFER, WILDCARD_CERT, UNKNOWN}.'
  invocation_example: '# Minimal valid input (offline symptom classification):

    Symptom: "The domain api.example.com resolves to the old

    IP 203.0.113.10 instead of the new ALB DNS name. The new ALIAS

    record was added to the hosted zone but dig still returns the

    old IP after 2 hours."

    HostedZoneId: Z2 ABCDEFGHIJ

    Domain: api.example.com

    Record type: A (ALIAS to ALB)

    TTL: 300

    Expected: resolves to dualstack.alb-xxx.us-east-1.elb.amazonaws.com

    Actual: resolves to 203.0.113.10 (stale)'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Route 53, DNS, hosted zone, NS delegation, glue records, SOA serial, DNSSEC, KSK, ZSK, DS record, alias record, CNAME, routing policy, geolocation, latency, weighted, failover, private hosted zone, VPC association, split-horizon DNS, Route 53 Resolver, inbound endpoint, outbound endpoint, health check, DNS query logging, domain transfer, wildcard certificate, _acme-challenge, TTL, DNS cache, troubleshooting
  tags: route53, networking, troubleshooting, dns, dnssec, hosted-zone, health-check, resolver, private-hosted-zone
---

# Route 53 DNS Troubleshooter

## Quick start

Symptom -> layer map in full (NXDOMAIN, SERVFAIL, wrong IP, failover, PHZ, split-horizon, wildcard cert): [references/advanced-patterns.md](references/advanced-patterns.md).
The Quick reference symptom triage table below is the authoritative router.
- **Always verify with a probe, never guess.** Each layer has a single
  command (dig, nslookup, or AWS CLI) that proves or disproves it. A
  ROOT_CAUSE_IDENTIFIED verdict requires positive evidence — a failing
  probe that matches the symptom — not a process of elimination that
  "must be the TTL."
The four senior gotchas (NS delegation chain, DNSSEC DS/KSK match, private-zone VPC association + DHCP Options, propagation wait 2x TTL / AWS Health escalation): [references/advanced-patterns.md](references/advanced-patterns.md).

## Mindset

Full diagnostic mindset (the record is usually innocent; delegation, DNSSEC, association, and cache layers are the usual culprits): [references/advanced-patterns.md](references/advanced-patterns.md).

## Philosophy

The four senior-engineer behaviours (four-link NS delegation chain, DNSSEC DS chain of trust, private vs public zone independence, health-check/routing-policy evaluation coupling): [references/advanced-patterns.md](references/advanced-patterns.md).

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

Account-wide pre-flight commands (list-hosted-zones, get-hosted-zone, list-resource-record-sets, get-dnssec, get-health-check-status, list-resolver-endpoints, aws health, dig +trace/+dnssec): [references/diagnostic-commands.md](references/diagnostic-commands.md).

### Zone-state short-circuit

Zone-state short-circuit table (PrivateZone without VPCs, public zone without registrar NS, DNSSEC KeyTag/DS mismatch, unhealthy PRIMARY, overlapping public+private zones): [references/advanced-patterns.md](references/advanced-patterns.md).

### Delegation / record-set pre-flight

Delegation / record-set pre-flight table (registrar NS vs zone NS, SOA serial, alias/CNAME coexistence, TTL 86400 propagation): [references/advanced-patterns.md](references/advanced-patterns.md).

If the input is malformed (missing domain name or zone ID, absent
symptom description, no dig output for offline diagnosis), emit:

INSUFFICIENT_DATA re-prompt template for malformed input (missing domain/zone ID or symptom): [references/worked-examples.md](references/worked-examples.md).

## Process — Diagnostic decision tree (apply in symptom order)

The diagnostic tree is symptom-driven. Pick the entry point based on the
observed symptom, then walk the layer-specific probes in order. Each layer
ends with either a positive root-cause confirmation (failing probe that
matches the symptom) or a pass that moves to the next layer. **Never emit
ROOT_CAUSE_IDENTIFIED without a failing probe that matches the symptom.**

### Step 0: Non-obvious behaviours that change diagnosis

The 15 non-obvious behaviours (TTL max not average, dig @resolver bypass, ALIAS server-side resolution, DNSSEC validation network dependence, DS cryptographic link, PHZ VPC-only resolution, resolver inbound/outbound semantics, split-horizon, health checks vs DNS, geolocation default record, latency table, weight 0, domain-transfer NS/DS, wildcard _acme-challenge conflicts): [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand — each behaviour reroutes a diagnosis.

### Step 1: Symptom entry — pick the diagnostic branch

Symptom-to-branch table mapping each symptom to its Step 2-13 branch: [references/advanced-patterns.md](references/advanced-patterns.md).
The Quick reference symptom triage table above carries the same routing with first probes.

### Step 2: NS delegation — the four-link chain

Symptom: `NXDOMAIN` for a domain that has records in the hosted zone.
The domain does not resolve because the TLD servers do not delegate to
the Route 53 hosted zone's NS servers.

Probes (zone NS via list-resource-record-sets, dig +trace at 8.8.8.8, registrar NS): [references/diagnostic-commands.md](references/diagnostic-commands.md).

Four-link delegation chain diagram (root -> TLD -> registrar NS -> hosted zone NS): [references/advanced-patterns.md](references/advanced-patterns.md).

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

Probes (get-dnssec, dig +dnssec DS at 8.8.8.8, dig +dnssec DNSKEY): [references/diagnostic-commands.md](references/diagnostic-commands.md).

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

Probes (dig against authoritative server, public resolver, local resolver) and authoritative-vs-resolver interpretation: [references/diagnostic-commands.md](references/diagnostic-commands.md).

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

Probes (list-resource-record-sets filtered by name): [references/diagnostic-commands.md](references/diagnostic-commands.md).

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

6a geolocation probe (jq select(.GeoLocation)), the GeoLocation/default-record/same-policy check table, and the missing-default-record error: [references/advanced-patterns.md](references/advanced-patterns.md).

#### 6b: Latency

6b latency check table (Region per record, latency policy on all records) and single-region error: [references/advanced-patterns.md](references/advanced-patterns.md).

#### 6c: Weighted

6c weighted check table (Weight >= 0, weighted policy, per-record health checks) and weight-0 error: [references/advanced-patterns.md](references/advanced-patterns.md).

#### 6d: Failover

6d failover check table (PRIMARY+HealthCheckId, SECONDARY record, health check endpoint) and always-suppressed error: [references/advanced-patterns.md](references/advanced-patterns.md).

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: ROUTING_GEOLOCATION` /
`ROUTING_LATENCY` / `ROUTING_WEIGHTED` / `ROUTING_FAILOVER`.

### Step 7: Health check failing

Symptom: failover record always returns SECONDARY; weighted record
receives no traffic; multi-value answer excludes the record.

Probes (get-health-check-status, get-health-check config): [references/diagnostic-commands.md](references/diagnostic-commands.md).

| Check | Expected |
|---|---|
| `HealthCheckConfig.Type` | `HTTPS`, `HTTP`, `TCP`, `HTTPS_STR_MATCH`, `CALCULATED` |
| `HealthCheckConfig.FullyQualifiedDomainName` or `IPAddress` | The endpoint being monitored |
| `HealthCheckConfig.Port` | 443 for HTTPS, 80 for HTTP, or custom |
| `HealthCheckConfig.ResourcePath` | The path being checked (e.g., `/health`) |
| `Status` | `Healthy` or `Unhealthy` |
| `StatusReport.CheckedTime` | Recent timestamp (health check is actively running) |

Common failure patterns (circular dependency on the record itself, wrong path, HTTP->HTTPS redirect, calculated all-unhealthy, cross-region false negatives, InsufficientDataHealthStatus): [references/advanced-patterns.md](references/advanced-patterns.md).

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: HEALTH_CHECK`.

### Step 8: Private hosted zone VPC association

Symptom: private hosted zone does not resolve from instances in a VPC.

Probes (get-hosted-zone VPCs, list-vpc-association-authorizations, describe-dhcp-options): [references/diagnostic-commands.md](references/diagnostic-commands.md).

Association check table (VPCs list, AmazonProvidedDNS, PrivateZone flag) and common failure patterns (associate, cross-account authorization, custom DHCP DNS, split-horizon overlap): [references/advanced-patterns.md](references/advanced-patterns.md).

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: PHZ_VPC_ASSOCIATION`.

### Step 9: Split-horizon DNS

Symptom: same domain resolves differently inside vs outside the VPC.

Probe (list-hosted-zones filtered by name) and the inside-vs-outside resolution interpretation: [references/diagnostic-commands.md](references/diagnostic-commands.md).

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: SPLIT_HORIZON`.

### Step 10: Resolver inbound endpoint

Symptom: on-premises DNS resolvers cannot resolve Route 53 private
hosted zones. Queries from on-premises time out.

Probes (list-resolver-endpoints INBOUND, get-resolver-endpoint, describe-security-groups on endpoint ENIs): [references/diagnostic-commands.md](references/diagnostic-commands.md).

| Check | Expected |
|---|---|
| Inbound endpoint `Status: OPERATIONAL` | If `CREATING` or `ACTION_NEEDED`, wait or fix the issue |
| Inbound endpoint has ENIs in the subnets reachable from on-premises | ENI IPs must be routable from on-premises |
| Security Group allows inbound UDP/TCP 53 from on-premises CIDR | DNS traffic allowed |
| On-premises forwarder points at the inbound endpoint IPs | Conditional forwarder or secondary zone configured |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: RESOLVER_INBOUND`.

### Step 11: Resolver outbound endpoint

Symptom: VPC instances cannot resolve on-premises DNS names.

Probes (list-resolver-endpoints OUTBOUND, list-resolver-rules, list-resolver-rule-associations): [references/diagnostic-commands.md](references/diagnostic-commands.md).

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

Probes (CNAME record-set scan, dig CNAME _<hash>) and the wildcard-intercepts-ACM-validation interpretation: [references/diagnostic-commands.md](references/diagnostic-commands.md).

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: WILDCARD_CERT`.

### Step 12b: Domain transfer DNS disruption

Symptom: SERVFAIL or NXDOMAIN after a domain transfer between registrars.

Probes (dig NS and dig +dnssec DS at the TLD) and the NS-change/DS-gap transition interpretation: [references/diagnostic-commands.md](references/diagnostic-commands.md).

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

Full worked example (DNSSEC DS record mismatch -> DNSSEC_DS): [references/worked-examples.md](references/worked-examples.md).

### Worked example — Private hosted zone VPC association

Full worked example (PHZ not associated with the VPC -> PHZ_VPC_ASSOCIATION): [references/worked-examples.md](references/worked-examples.md).

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

Pre-flight safety checks (CONFIRMATION GATE, read-only-first, UPSERT discipline, split-horizon confirmation, DNSSEC multi-step, NS change windows, batch limit of 5 zones) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand before executing any state-changing CLI.

## Remediation guidance

Per-layer remediation playbooks with exact CLI (NS_DELEGATION, DNSSEC_DS, DNSSEC_KSK/ZSK, DNS_CACHE_TTL, ALIAS_CNAME_CONFLICT, PHZ_VPC_ASSOCIATION incl. cross-account, HEALTH_CHECK, RESOLVER_INBOUND, RESOLVER_OUTBOUND, WILDCARD_CERT): [references/error-handling.md](references/error-handling.md).

## Deep reference: Route 53 DNS resolution layer model

Resolution layer model deep reference (symptom->layer decision matrix, NS delegation chain, DNSSEC key hierarchy and key states, routing-policy reference, TTL reference, resolver endpoint reference): [references/route53-resolution-reference.md](references/route53-resolution-reference.md).

## Recent AWS features (2024-2026)

Recent AWS features (DNSSEC signing GA, CIDR routing, Resolver query logging, health check enhanced metrics, PHZ cross-account RAM sharing): [references/advanced-patterns.md](references/advanced-patterns.md).

## References (load on demand)

- [Advanced patterns](references/advanced-patterns.md) — mindset, philosophy, quick-start gotchas, Step 0 non-obvious behaviours, per-step check tables, recent AWS features
- [Diagnostic commands](references/diagnostic-commands.md) — account-wide pre-flight gather-info gate, per-step probes (Steps 2-12b), pre-flight safety checks
- [Error handling](references/error-handling.md) — per-layer remediation playbooks with exact CLI
- [Worked examples](references/worked-examples.md) — DNSSEC DS mismatch, PHZ VPC association, INSUFFICIENT_DATA re-prompt
- [Resolution reference](references/route53-resolution-reference.md) — resolution layer model, delegation chain, DNSSEC hierarchy, routing-policy/TTL/resolver tables
- [Troubleshooting commands](references/route53-troubleshooting-commands.md) — remediation command catalog

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
