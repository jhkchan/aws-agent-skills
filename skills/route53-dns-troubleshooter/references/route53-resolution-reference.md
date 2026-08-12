# Route 53 DNS Resolution Reference Guide

Supplementary reference for the Route 53 DNS Troubleshooter skill.
Loaded on-demand when a diagnostic needs delegation chain semantics,
DNSSEC key hierarchy, routing policy evaluation rules, or private
zone association matrices.

## NS delegation chain

The full delegation chain for a public domain:

```
Root servers (a-m.root-servers.net)
  -> TLD servers (.com: a-m.gtld-servers.net, .io, .org, etc.)
    -> Registrar NS records (set at the domain registrar)
      -> Hosted zone NS records (Route 53 assigned NS)
```

### Verifying each link

| Link | Command | Expected |
|---|---|---|
| Root -> TLD | `dig +trace NS <domain> @8.8.8.8` | TLD servers listed |
| TLD -> Registrar NS | `dig NS <domain> @a.gtld-servers.net +short` | Registrar NS listed |
| Registrar NS == Hosted zone NS | Compare `dig NS` output with `list-resource-record-sets` NS | Must match exactly |

### Glue records

Glue records are needed when the NS hostnames are under the SAME domain
being delegated. For example, if `example.com` delegates to
`ns1.example.com`, the parent (`.com` TLD) needs a glue record (A/AAAA)
for `ns1.example.com` to resolve the circular dependency.

Route 53's default NS hostnames (`ns-X.awsdns-*.com`) are NOT under the
delegated domain, so no glue records are needed. Glue records are only
needed for custom NS names.

## DNSSEC key hierarchy and chain of trust

```
Root zone (trust anchor, baked into resolver software)
  |
  +-> DS record at TLD (.com, .io, etc.)
      |
      +-> DS record at registrar zone (parent of your domain)
          |
          +-> KSK (Key Signing Key)
              |  signs the DNSKEY RRset
              +-> ZSK (Zone Signing Key)
                  |  signs all other RRsets
                  +-> RRSIG on each record (A, AAAA, MX, etc.)
```

### DNSSEC key states in Route 53

| State | Meaning | Action needed |
|---|---|---|
| `KEY_NOT_PUBLISHED` | Key generated but not yet in the zone | Wait for propagation |
| `KEY_PUBLISHED` | Key is in the zone but not used for signing | Wait for key activation |
| `INACTIVE` | Key is published but not signing (transition) | Wait for DNSSEC rotation to complete |
| `ACTIVE` | Key is actively signing the zone | None |

### DS record verification

The DS (Delegation Signer) record at the parent zone links the parent
to the child zone's KSK. The DS record contains:

| Field | Description |
|---|---|
| Key tag | Numeric identifier of the KSK (computed from the DNSKEY) |
| Algorithm | Cryptographic algorithm (13 = ECDSAP256SHA256, 8 = RSASHA256) |
| Digest type | Hash algorithm (2 = SHA-256, 1 = SHA-1) |
| Digest | Hash of the KSK's DNSKEY RRset |

To verify: `dig +dnssec DS <domain> @8.8.8.8 +short` should return a DS
record whose key tag matches the KSK's key tag from
`aws route53 get-dnssec`.

## Record type coexistence rules

| Existing record type | Can add CNAME? | Can add ALIAS (A)? | Can add ALIAS (AAAA)? |
|---|---|---|---|
| A | No | No (same type) | Yes (different type) |
| AAAA | No | Yes (different type) | No (same type) |
| CNAME | No | No | No |
| ALIAS (A) | No | No (same type) | Yes (different type) |
| ALIAS (AAAA) | No | Yes (different type) | No (same type) |
| MX, TXT, NS, SRV, PTR | Yes | Yes (A alias) | Yes (AAAA alias) |

A CNAME cannot coexist with ANY other record type for the same name
(except for SIG, NXT, and NSEC records in DNSSEC).

## Routing policy evaluation

### Simple routing
- One record set with one or more values
- Route 53 returns all values in random order
- No health check support

### Weighted routing
- Traffic split proportional to weight values
- `Weight: 0` suppresses the record (no traffic)
- Unhealthy records are suppressed (effective weight 0)
- Weights are relative: weights 1, 1, 2 means 25%, 25%, 50%

### Latency routing
- Based on AWS inter-region latency data
- Route 53 evaluates the user's EDNS Client Subnet (if provided) or
  the resolver's IP to estimate the user's nearest AWS region
- Each record has a `Region` (AWS region code like `us-east-1`)
- The record with the lowest latency to the user is returned

### Geolocation routing
- Based on the user's geographic location (continent, country, subdivision)
- A `Default` record (`GeoLocation.CountryCode: "*"`) catches unmatched
  queries
- Without a default record, queries from uncovered locations return
  NXDOMAIN
- Geolocation is determined from EDNS Client Subnet or resolver IP

### Failover routing
- `PRIMARY` record is served when its health check is healthy
- `SECONDARY` record is served when the PRIMARY health check fails
- PRIMARY must have a `HealthCheckId`
- If no SECONDARY exists and PRIMARY is unhealthy, NXDOMAIN is returned

### Multi-value answer routing
- Returns up to 8 healthy records randomly
- Each record can have its own health check
- Provides simple load balancing (not as sophisticated as ALB)

### Geoproximity routing (traffic flow)
- Routes based on geographic proximity with adjustable bias
- Requires a traffic policy (not available via simple record sets)

### IP-based routing
- Routes based on the client's source IP CIDR block
- `CidrRoutingConfig` contains a list of CIDR blocks and corresponding
  record values
- A default location catches unmatched IPs

## TTL reference by record type

| Record type | Recommended TTL | Notes |
|---|---|---|
| NS | 172800 (48h) | TLD-level caching; changes are very slow |
| SOA | 900 (15m) | serial, refresh, retry, expiry, minimum |
| A / AAAA (stable) | 3600 (1h) | Balance caching vs change speed |
| A / AAAA (dynamic) | 60 (1m) | Fast failover; higher query cost |
| A / AAAA (failover) | 60 (1m) | Health check drives failover, not TTL |
| MX | 3600 (1h) | Email routing changes need moderate propagation |
| TXT (SPF, DKIM) | 3600 (1h) | Email security records |
| CNAME | 300 (5m) | Moderate; often used for validation |
| ALIAS | N/A | Route 53 resolves server-side; uses target's TTL |

## Private hosted zone resolution matrix

| Source | Resolves public zone? | Resolves private zone? |
|---|---|---|
| Internet (any DNS client) | Yes | No |
| EC2 in associated VPC | Yes (if no private zone for same name) | Yes |
| EC2 in non-associated VPC | Yes | No |
| EC2 in VPC with custom DNS | Depends on forwarder | Depends on forwarder |
| On-premises via inbound endpoint | Depends on forwarder config | Yes (if forwarded to inbound ENI) |

### Private zone VPC association methods

| Method | Command | Use case |
|---|---|---|
| Direct association | `associate-vpc-with-hosted-zone` | Same account |
| Cross-account authorization | `create-vpc-association-authorization` + `associate-vpc-with-hosted-zone` | Cross-account |
| RAM share (2025+) | RAM resource share + association | Simplified cross-account |

## Resolver endpoint reference

### Inbound endpoint

| Property | Value |
|---|---|
| Purpose | On-premises / external -> Route 53 (private zones) |
| ENIs | One per subnet (minimum 2 subnets in different AZs) |
| IP addresses | Auto-assigned or specified from subnet CIDR |
| SG requirement | Allow inbound UDP/TCP 53 from source CIDR |
| On-premises config | Conditional forwarder for private zone domain -> inbound ENI IPs |

### Outbound endpoint

| Property | Value |
|---|---|
| Purpose | VPC -> on-premises DNS |
| ENIs | One per subnet (minimum 2 subnets in different AZs) |
| SG requirement | Allow outbound UDP/TCP 53 to target DNS IPs |
| Resolver rules | `DomainName` matches the on-prem domain; `TargetIps` are on-prem DNS |
| Rule association | Rule must be associated with the VPC |

### Resolver rule evaluation order

1. System rules (built-in, e.g., `.in-addr.arpa` reverse lookup)
2. Forwarding rules (outbound endpoint rules) — evaluated in priority order
3. Private hosted zones (associated with the VPC)
4. Public hosted zones
5. Internet root servers

If a forwarding rule matches a domain, it takes precedence over a
private hosted zone for the same domain.
