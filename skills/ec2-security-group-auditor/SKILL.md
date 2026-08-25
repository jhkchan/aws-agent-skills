---
name: ec2-security-group-auditor
description: 'Classifies each EC2 security group''s inbound exposure as OPEN, PUBLIC_NONCRITICAL, or RESTRICTED (worst-case per-rule aggregation) and emits remediation mapped to CIS AWS Foundations / PCI-DSS / NIST SP 800-53. Invoke when: (a) pre-production SG review, (b) periodic CIS/PCI-DSS compliance audit, (c) incident response involving suspected network exposure, or (d) VPC/account security-baseline validation. Recognizes port ranges, non-TCP protocols, managed prefix lists, IPv6 sources, split-horizon CIDR pairs, and overlapping rules. Keywords: security group, SG, ec2, inbound rule, port exposure, 0.0.0.0/0, CIDR audit, attack surface, compliance check, VPC security.'
license: Apache-2.0
compatibility: Requires an LLM-based agent runtime (Claude Code, Cursor, Windsurf) or direct invocation. No AWS CLI calls needed for classification — the skill operates on provided SG rule data. For live AWS audits, requires aws-cli >= 2.0 with ec2:DescribeSecurityGroups and ec2:GetManagedPrefixListEntries permissions.
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  family: Security
  verdict_shape: OPEN | PUBLIC_NONCRITICAL | RESTRICTED
  version: 0.4.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, ec2, security-group, network-security, compliance, audit
  dependencies: aws-orchestrator
  keywords: security group, SG, ec2, inbound rule, port exposure, 0.0.0.0/0, CIDR audit, attack surface, compliance check, VPC security, CIS benchmark, PCI-DSS, NIST SP 800-53, network exposure, prefix list
  when_to_use: Use when reviewing EC2 security group inbound rules for public exposure, compliance auditing against CIS AWS Foundations Benchmark / PCI-DSS / NIST SP 800-53, incident response involving suspected network exposure, or onboarding a new VPC or account for security baseline validation.
---

# EC2 Security-Group Auditor

An AWS CloudOps agent skill that analyzes EC2 security group inbound rules
to identify publicly exposed ports, classify each security group's exposure
level with a CVSS-style risk score, and provide specific remediation guidance
mapped to compliance controls.

## Quick verdict logic (at-a-glance)

For EACH inbound rule: classify **SOURCE** (PUBLIC / RESTRICTED /
CONDITIONAL), then **PORT** (CRITICAL / NON_CRITICAL). Combine:
PUBLIC + CRITICAL → **OPEN**; PUBLIC + NON_CRITICAL →
**PUBLIC_NONCRITICAL**; RESTRICTED source → **RESTRICTED**. SG verdict =
WORST per-rule verdict (`OPEN > PUBLIC_NONCRITICAL > RESTRICTED`).
Sources arrive in FOUR distinct API arrays — `IpRanges`, `Ipv6Ranges`,
`UserIdGroupPairs`, `PrefixListIds` — iterate all four or you will miss
IPv6 exposure, SG-ref cycles, and prefix-list drift. Full procedure,
port-range intersection rules, and edge cases in §"Classification logic";
deep AWS dataplane behavior in §"AWS dataplane expert details".

## Activation keywords

security group, SG, ec2, inbound rule, port exposure, open SSH, open RDP,
open database, 0.0.0.0/0, public port, network exposure, CIDR audit,
firewall rule, attack surface, compliance check, VPC security, prefix list,
CIS benchmark, PCI-DSS.

## Reasoning framework (Mindset — why the procedure is ordered this way)

Security groups are **stateful** — return traffic for an allowed inbound
flow is automatically permitted, so there is no need for "return port"
rules. That confusion is common: engineers add `32768-65535` inbound from
`0.0.0.0/0` thinking it is needed for responses — it is not; that rule is
a side channel for inbound traffic and should be removed. Because SGs are
stateful and evaluated per-rule by the AWS dataplane, the verdict for a
security group is the **worst (most permissive) verdict of any individual
inbound rule** — a single open rule creates an attack surface even if
every other rule is locked down. The procedure below evaluates each rule
independently first, then aggregates to the worst case. This is the
inverse of firewall "default deny" reasoning: a restrictive rule does NOT
narrow an already-open rule on the same SG.

## AWS dataplane expert details (Mindset — non-obvious AWS behavior)

These AWS-specific behaviors are NOT in the port registry but routinely
trip up audits. Internalize them before emitting any verdict.

### Rule evaluation is UNION, not first-match

AWS security groups do NOT use first-match priority. Every inbound allow
rule is independently evaluated against the packet; the **union** of all
allow rules is the effective permission. There is no "deny" rule in SGs
— denies live in Network ACLs, which ARE stateless and ordered. Practical
consequence: adding a tighter rule on the same port+source does NOT
override an existing `0.0.0.0/0` rule — you must REMOVE the broader
rule. This is precisely why the procedure aggregates to the WORST
per-rule verdict, not the "best" or "most specific."

### Stateful conntrack has a per-ENI ceiling

Return traffic for an allowed outbound flow is auto-permitted via
connection tracking. Each ENI's conntrack table is sized by instance
type (see EC2 network performance specs — r5n.16xlarge ~600k entries,
t3.micro far less). Under sustained high packets-per-second the table
can exhaust, at which point AWS falls back to strict-flow pinning and
some established flows may drop. This is NOT a reason to add inbound
ephemeral rules — the SG is still stateful. It IS a reason to monitor
`conntrack_allowance_exceeded` in CloudWatch `etwpm`.

### Source field has four distinct shapes in the API

`DescribeSecurityGroups` returns sources in four separate arrays:
`IpRanges` (IPv4), `Ipv6Ranges` (IPv6), `UserIdGroupPairs` (SG refs),
`PrefixListIds` (managed prefix lists). A naive auditor that only
checks `IpRanges` will miss IPv6 exposure, SG-ref cycles, and
prefix-list drift. Iterate ALL FOUR arrays every time. The
classification table treats them uniformly; the API does not.

### Quotas that change the audit posture

- `sg-rules-per-sg` quota: default 60 inbound + 60 outbound rules per
  SG (raisable). An SG near the limit is itself a smell — rule sprawl
  obscures the real posture and slows dataplane propagation.
- `SGs-per-ENI` quota: default 5. Effective permission across 5 SGs
  is the union of up to 300 inbound rules per interface.
- The VPC default SG **cannot be deleted** — only its rules can. CIS
  5.4 specifically targets leaving it open. Always include the default
  SG in scope even when "unused"; AWS re-attaches it to new ENIs in
  some launch paths.

### VPC peering, RAM sharing, and cross-VPC SG references

- SG IDs are **region-scoped** and CANNOT be referenced from another
  VPC, even over a peering connection. Cross-VPC rules must use CIDRs
  — which means there is no SG-ref guardrail on the peer side.
- Over peering, the peer VPC's effective posture depends on rules YOU
  cannot see. Flag any peered-CIDR source as "external-trust" and
  require periodic re-validation.
- In AWS RAM shared subnets, participant accounts can create SGs in
  the shared VPC. The owner account's audit MUST enumerate SGs across
  all participants (`--owner self` filter excludes them — drop it).

### Prefix-list versioning and drift

Every modification to a managed prefix list bumps `Version`. Use
`--version <current>` for optimistic locking. For periodic re-audit,
store the version observed at last review and compare; if `Version`
advanced without a corresponding change ticket, the list has drifted.
AWS-managed lists (e.g., CloudFront `pl-xxxxxxxx` for global edge IPs)
rotate entries as POPs are added — treat their classification as
"valid as of timestamp T", not timeless.

### AWS Config + Security Hub control IDs

Map findings to the downstream tooling auditors actually run — they
will find the finding in Security Hub before they read your report:

| Finding | AWS Config managed rule | Security Hub control |
| --- | --- | --- |
| SSH (22) from `0.0.0.0/0` | `restricted-common-ports` | **EC2.2** |
| RDP (3389) from `0.0.0.0/0` | `restricted-common-ports` | **EC2.18** |
| SG not attached to any ENI | `ec2-security-group-attached-to-eni` | EC2.4 |
| Default SG allows any traffic | — | **EC2.19** (CIS 5.4) |
| Any other port from `0.0.0.0/0` | `vpc-sg-open-only-to-authorized-ports` | — |
| Public launch + open SG combined | — | **EC2.15** |

Cite BOTH the CIS control AND the Security Hub control ID in the
REMEDIATION field — the remediation owner usually triages via
Security Hub.

### Reachability Analyzer confirms the actual path

For borderline cases ("is the SG reachable through a TGW or peering
route?"), use VPC Reachability Analyzer — it evaluates SG + route
table + peering together, while the SG rule alone does not guarantee
a reachable path:

```
aws ec2 create-network-insights-path \
  --source <source-eni> --destination <ip> \
  --protocol tcp --destination-port <port>
aws ec2 start-network-insights-analysis \
  --network-insights-path-id <path-id>
```

Use it to CONFIRM OPEN verdicts that depend on a specific ingress
path, and to REFUTE RESTRICTED claims when a transit gateway makes
the SG effectively reachable from an unexpected CIDR.

### Effective enumeration queries

The single most useful query for scoping an audit — find every SG in
the region that allows a given CIDR (the `ip-permission.cidr` filter
matches on substring, so use the exact value):

```
aws ec2 describe-security-groups \
  --filters Name=ip-permission.cidr,Values=0.0.0.0/0 \
            Name=ip-permission.from-port,Values=22 \
  --query 'SecurityGroups[*].[GroupId,GroupName,VpcId]' --output table
```

For IPv6 exposure, repeat with `Name=ip-permission.ipv6-ranges.cidr,Values=::/0`.

## Classification logic (Process — per-rule evaluation, worst-case aggregation)

Evaluate EACH inbound rule independently, assign a per-rule verdict, then
take the **worst** verdict across all rules as the SG's verdict.
`OPEN > PUBLIC_NONCRITICAL > RESTRICTED`.

### Decision procedure (pseudocode)

```
function classify_sg(sg):
    per_rule_verdicts = []
    for rule in sg.inbound_rules:
        src = classify_source(rule.source)          # PUBLIC | RESTRICTED | CONDITIONAL
        port = classify_port(rule.port, rule.protocol)  # CRITICAL | NON_CRITICAL | N_A

        if src == PUBLIC:
            if port == CRITICAL:
                per_rule_verdicts.append(OPEN)
            elif port == NON_CRITICAL:
                per_rule_verdicts.append(PUBLIC_NONCRITICAL)
            else:
                per_rule_verdicts.append(PUBLIC_NONCRITICAL)  # ICMP-only
        elif src == CONDITIONAL:                     # managed prefix list
            entries = inspect_prefix_list(rule.source)
            if any_entry_public(entries):
                if port == CRITICAL: per_rule_verdicts.append(OPEN)
                else: per_rule_verdicts.append(PUBLIC_NONCRITICAL)
            else:
                per_rule_verdicts.append(RESTRICTED)
        else:                                        # RESTRICTED source
            per_rule_verdicts.append(RESTRICTED)

    if no inbound rules: return RESTRICTED
    return worst(per_rule_verdicts)  # OPEN > PUBLIC_NONCRITICAL > RESTRICTED

function classify_port(port, protocol):
    if protocol == -1: return CRITICAL               # ALL protocols
    if port == "0-65535": return CRITICAL             # all TCP/UDP ports
    if intersects(port, HIGH_RISK_PORTS): return CRITICAL
    if port in [80, 443, 8080]: return NON_CRITICAL
    if protocol == ICMP: return N_A                   # handled separately
    return NON_CRITICAL                               # unknown port, non-critical default
```

### Port range intersection (the most common model error)

A rule with a port **range** must be checked for **intersection** with the
high-risk registry (§"High-risk port registry"). Examples:
- `20-25` contains 22 (SSH) and 25 (SMTP) → CRITICAL → OPEN if PUBLIC
- `3300-3400` contains 3306 (MySQL) → CRITICAL → OPEN if PUBLIC
- `440-450` contains 443 only → does NOT intersect high-risk → PUBLIC_NONCRITICAL if PUBLIC
- `0-65535` intersects all high-risk ports → always CRITICAL

### Multi-port and mixed-protocol entries

- AWS SG rules accept a **single port** or a **port range** — NOT a
  comma-separated list. Each port or range is a separate rule entry. If
  the input shows comma-separated ports in one rule, split into per-rule
  evaluations and aggregate.
- For **ICMP**, `Port` maps to `Type:Code`: `8` = Echo Request, `0` =
  Echo Reply, `13` = Timestamp, `-1:-1` = ALL. An ICMP-only rule from a
  PUBLIC source is PUBLIC_NONCRITICAL (reconnaissance, not data-plane
  access).
- A rule with the same port on **both TCP and UDP** (e.g., RDP 3389 over
  TCP+UDP): evaluate each protocol independently, take the worse verdict.

### Worked examples

- **Mixed rules (web-tier pattern):** SG has `443 TCP 0.0.0.0/0` AND
  `22 TCP 10.0.0.0/8`. Rule 1 = PUBLIC_NONCRITICAL (public source,
  non-critical port); Rule 2 = RESTRICTED (private source, even though
  port 22 is critical). Aggregate = **PUBLIC_NONCRITICAL**. Do NOT
  classify as OPEN just because SSH appears — check the SOURCE first.

- **All-ports range:** SG has `0-65535 TCP 0.0.0.0/0`. Range intersects
  the entire high-risk registry → **OPEN**. Do NOT treat `0-65535` as a
  single non-critical port.

- **Database on private CIDR:** SG has `3306 TCP 10.0.0.0/8`. Source is
  RESTRICTED → **RESTRICTED**. Port 3306 is critical ONLY when combined
  with a PUBLIC source.

- **Prefix-list source:** SG has `443 TCP pl-58a543d6` (CloudFront).
  Entries are public AWS edge IPs, but CloudFront is a trusted CDN →
  **PUBLIC_NONCRITICAL** (not OPEN).

- **IPv6 dual-stack (the most-missed exposure):** SG has `22 TCP ::/0`
  with NO IPv4 rule. The model output may look "closed" if the auditor
  only inspects `IpRanges`. `::/0` is PUBLIC, AWS IPv6 addresses are
  globally routable by default, and 22 is CRITICAL → **OPEN**. Always
  iterate BOTH `IpRanges` and `Ipv6Ranges` arrays. A "locked-down on
  IPv4" SG that is wide-open on IPv6 is a common Shadowserver finding.

- **Overlapping CIDR sources (union semantics):** SG has `22 TCP
  0.0.0.0/0` AND `22 TCP 10.0.0.0/8` on the same port. AWS evaluates
  each rule independently — there is no first-match and no deny in
  SGs. The broader `0.0.0.0/0` rule is the effective exposure.
  Per-rule verdicts: OPEN + RESTRICTED → aggregate **OPEN**. Add a
  cleanup note: the `10.0.0.0/8` rule is redundant and obscures
  posture — REMOVE it, do not "narrow" it.

- **Split-horizon evasion:** SG has `443 TCP 0.0.0.0/1` AND
  `443 TCP 128.0.0.0/1`. Neither rule literally equals `0.0.0.0/0`,
  but their union covers the entire IPv4 space. Both are PUBLIC, port
  443 is NON_CRITICAL → **PUBLIC_NONCRITICAL**. This pattern evades
  naive `grep "0.0.0.0/0"` audits; always union complementary halves
  (`/1` pairs, `/2` quads) before classifying.

- **Prefix-list drift between audits:** At review T0, `pl-abcd1234`
  contained only RFC 1918 CIDRs → RESTRICTED. At review T1, the list
  owner added `0.0.0.0/0` to debug a vendor issue. The SG rule itself
  did not change, but the effective verdict flipped to OPEN. Re-fetch
  prefix-list entries on EVERY review cycle; compare `Version` to the
  last-audited value. Drift without a change ticket is itself a finding.

## Risk scoring and compliance mapping

### CVSS-style severity per verdict

| Verdict + context | Severity | CVSS range | Action |
| --- | --- | --- | --- |
| OPEN — all-ports (`0-65535`) or protocol `-1` from PUBLIC | **Critical** | 9.8–10.0 | P0: remediate immediately |
| OPEN — administrative ports (22, 23, 3389, 5900, 2375) | **Critical** | 9.0–9.8 | P0: incident-grade response |
| OPEN — K8s/Docker (6443, 10250, 2379, 2375, 2376) | **Critical** | 9.0–9.8 | P0: cluster takeover risk |
| OPEN — databases (3306, 5432, 1433, 1521, 27017, 6379, 9200) | **Critical** | 8.5–9.3 | P1: data exfiltration risk |
| OPEN — amplification (UDP 53, UDP 123, UDP 11211) | **High** | 7.5–8.0 | P1: DDoS reflection vector |
| PUBLIC_NONCRITICAL — direct to instance (no ALB) | **Medium** | 4.3–5.3 | P2: add ALB or verify intent |
| PUBLIC_NONCRITICAL — behind ALB/WAF | **Low** | 0.0–3.1 | P3: informational |
| RESTRICTED | **None** | 0.0 | No action |

### Compliance framework mapping

Each finding maps to specific control IDs that auditors and compliance
teams reference:

| Finding | CIS AWS Benchmark v3.0 | PCI-DSS v4.0 | NIST SP 800-53 Rev. 5 |
| --- | --- | --- | --- |
| SSH (22) from `0.0.0.0/0` | **5.1** | 1.2.1, 1.3.1 | SC-7(5), AC-4 |
| RDP (3389) from `0.0.0.0/0` | **5.2** | 1.2.1, 1.3.1 | SC-7(5), AC-4 |
| Any other port from `0.0.0.0/0` | **5.3** | 1.2.1 | SC-7(5) |
| Default SG allows any traffic | **5.4** | 1.2.2 | SC-7, SC-7(12) |
| DB/admin port on public SG | — | **1.3.4**, 1.4.1 | SC-7(5), SC-7(11) |
| Amplification vector (UDP DNS/NTP) | — | 1.3.6 | SC-7(20), SC-5 |

**CIS 5.1/5.2** are the most commonly failed controls in AWS environments.
Any OPEN verdict on ports 22 or 3389 is a direct CIS 5.1/5.2 violation
and should be cited in the REMEDIATION field.

## NEVER (critical anti-patterns — apply before emitting a verdict)

- NEVER classify SSH (port 22) or RDP (port 3389) open to `0.0.0.0/0`
  (or `::/0`) as anything other than **OPEN**. Botnets enumerate these
  ports within minutes. This is a direct CIS 5.1/5.2 violation.

- NEVER classify `0-65535` (all TCP ports) or protocol `-1` (all
  protocols) from `0.0.0.0/0` as merely RESTRICTED or
  PUBLIC_NONCRITICAL. All-ports-to-internet is maximum exposure.

- NEVER assume a port range is safe because it is "narrow." A range
  `20-25` contains 22 (SSH); `3300-3310` contains 3306 (MySQL).
  Always intersect the range against the high-risk registry.

- NEVER classify a rule as OPEN solely because a high-risk port
  appears — check the SOURCE first. Port 22 from `10.0.0.0/8` is
  RESTRICTED. Confusing these produces false-positive OPEN verdicts.

- NEVER assume a port is safe because the service is "just a database."
  MySQL, PostgreSQL, Redis, MongoDB, Elasticsearch exposed to the
  internet are the root cause of countless data breaches.

- NEVER treat a managed prefix list (`pl-xxxxxxxx`) as automatically
  RESTRICTED. AWS-managed lists for CloudFront, S3, and DynamoDB contain
  public IPs. Inspect with
  `aws ec2 get-managed-prefix-list-entries --prefix-list-id <pl-id>`.

- NEVER treat `10.0.0.0/7` as fully private. The `/7` spans `10/8`
  (RFC 1918) AND `11/8` (public). Any CIDR broader than the RFC 1918
  boundaries is partially public → classify as PUBLIC.

- NEVER add inbound "ephemeral" rules (`1024-65535` from `0.0.0.0/0`)
  for return traffic. Security groups are stateful — responses to
  outbound flows are automatically allowed. This misconfiguration is
  common and creates a wide attack surface for zero benefit.

- NEVER assume `::/0` (IPv6 `any`) is less dangerous than `0.0.0.0/0`.
  AWS IPv6 addresses are globally routable by default. A dual-stack
  instance with `::/0` on port 22 is just as exposed as IPv4.

- NEVER dismiss UDP DNS (port 53) from `0.0.0.0/0`. An open UDP 53
  resolver is a DNS amplification reflector (~50-80× amplification).
  AWS throttles accounts hosting open resolvers. Classify as OPEN.

- NEVER permit ICMP `ALL` (type `-1`) from `0.0.0.0/0` without flagging
  it. While ICMP alone is PUBLIC_NONCRITICAL, `ALL` enables timestamp
  queries (OS fingerprinting), address-mask queries (network mapping),
  and Smurf amplification.

- NEVER expose SNMP (UDP 161) to the internet. Community strings
  (`public`, `private`) are sent in cleartext in SNMPv1/v2c; the full
  network topology and configuration are leaked. Classify as OPEN.

- NEVER assume overlapping or redundant CIDR rules are harmless. AWS
  evaluates every inbound allow rule independently (UNION semantics —
  there is NO first-match priority and NO deny in SGs; deny lives in
  NACLs). A port with BOTH `0.0.0.0/0` and `10.0.0.0/8` sources means
  the broader (`0.0.0.0/0`) rule is the effective exposure; the
  restrictive rule adds nothing and must be REMOVED, not narrowed.
  Flag every duplicate and overlap as a cleanup item — they obscure
  the real posture during manual review AND defeat naive
  `grep "0.0.0.0/0"` audits.

- NEVER miss split-horizon CIDR evasion. Two rules `0.0.0.0/1` and
  `128.0.0.0/1` on the same port cover the ENTIRE IPv4 space, yet
  neither literally equals `0.0.0.0/0`. The same applies to `/2` quad
  splits and `/3` octets. Always union complementary halves before
  classifying — a per-rule RESTRICTED verdict can hide a union that is
  effectively PUBLIC.

- NEVER trust a customer-managed prefix list as permanently RESTRICTED.
  The list owner can add public CIDRs at any time without changing the
  SG rule. Re-audit prefix-list entries on every review cycle. Flag
  any `pl-xxxxxxxx` reference in a RESTRICTED SG for periodic
  re-validation.

- NEVER recommend simply deleting a rule without providing the
  replacement. SG rule deletion is a live-affecting change — the
  replacement (bastion SG reference, SSM Session Manager, app-tier SG
  reference) must be specified so the operator can apply it without
  losing application access.

## Source classification (Reference)

Classify the `Source` field BEFORE evaluating the port — misclassifying a
source is the most common auditor error.

| Source | Class | Notes |
| --- | --- | --- |
| `0.0.0.0/0` | **PUBLIC** (IPv4 internet) | All IPv4 addresses. |
| `::/0` | **PUBLIC** (IPv6 internet) | All IPv6 addresses. Treat identically. |
| `0.0.0.0/1` + `128.0.0.0/1` | **PUBLIC** (split-horizon evasion) | Union covers all IPv4; classify each as PUBLIC. |
| CIDR broader than RFC 1918 boundaries | **PUBLIC** (partial) | e.g., `10.0.0.0/7` spans `10/8` (private) AND `11/8` (public). |
| `100.64.0.0/10` | **RESTRICTED** (CGNAT, RFC 6598) | Carrier-grade NAT; flag for review. |
| `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16` | **RESTRICTED** (RFC 1918) | Standard private ranges. |
| `sg-xxxxxxxx` | **RESTRICTED** (SG reference) | Self-references valid for inter-tier comms. |
| `pl-xxxxxxxx` | **CONDITIONAL** | See §"Prefix-list evaluation procedure". |
| Specific public IP `/32` | **RESTRICTED** (single source) | Narrow; flag for rotation review. |
| Missing / blank | **RESTRICTED** | Treat conservatively as no source. |

## Prefix-list evaluation procedure (Reference)

When a rule's source is `pl-xxxxxxxx`, classification is CONDITIONAL on the
prefix list's entries:

### Step 1 — Identify the type

```
aws ec2 describe-managed-prefix-lists --prefix-list-ids pl-xxxxxxxx
```
Check `OwnerId`: if it matches your account, it is **customer-managed**;
if `Amazon`, it is **AWS-managed** (CloudFront, S3, DynamoDB).

### Step 2 — Enumerate entries

```
aws ec2 get-managed-prefix-list-entries --prefix-list-id pl-xxxxxxxx
```

### Step 3 — Classify

- **ALL entries** RFC 1918 or `/32` known IPs → **RESTRICTED**.
- **ANY public entry** → treat as **PUBLIC** for classification.
- **AWS-managed exception** (CloudFront/S3/DynamoDB): entries are AWS
  service IPs — effectively public but trusted infrastructure. Classify
  as **PUBLIC_NONCRITICAL** for non-critical ports (443, 80); **OPEN**
  for critical ports (22, 3389, databases, all-ports). AWS edge IPs
  should not be trusted with administrative access.

## High-risk port registry (Reference)

### Administrative access
| Port(s) | Protocol | Service | Risk |
| --- | --- | --- | --- |
| 22 | TCP | SSH | Brute-force #1; CIS 5.1. |
| 23 | TCP | Telnet | Unencrypted; trivially exploitable. |
| 3389 | TCP/UDP | RDP | Brute-force; BlueKeep. CIS 5.2. |
| 5900-5910 | TCP | VNC | Often no auth; trivial takeover. |
| 2375, 2376 | TCP | Docker daemon | Container RCE; full host compromise. |

### Databases
| Port(s) | Protocol | Service | Risk |
| --- | --- | --- | --- |
| 3306 | TCP | MySQL / Aurora MySQL | Data exfiltration, ransomware. |
| 5432 | TCP | PostgreSQL / Aurora PG | Data exfiltration, ransomware. |
| 1433 | TCP | MSSQL | Data exfil; SA brute-force. |
| 1521 | TCP | Oracle TNS | Data exfil; TNS poisoning. |
| 27017-27019 | TCP | MongoDB | NoSQL ransomware. |
| 6379 | TCP | Redis | Cryptomining, data exfil, ransomware. |
| 9042 | TCP | Cassandra | NoSQL data exfiltration. |
| 5984 | TCP | CouchDB | Default "admin party" on old versions. |
| 11211 | TCP/UDP | Memcached | UDP amplification DDoS (~51,000×). |
| 9200, 9300 | TCP | Elasticsearch | Data exfil + ransomware. |

### Message queues / streaming / container orchestration
| Port(s) | Protocol | Service | Risk |
| --- | --- | --- | --- |
| 5671, 5672 | TCP | AMQP / RabbitMQ | Queue manipulation. |
| 9092 | TCP | Kafka | Topic read/write; data tampering. |
| 6443 | TCP | Kubernetes API | Full cluster takeover. |
| 10250 | TCP | Kubelet | Per-node RCE. |
| 2379, 2380 | TCP | etcd | K8s control-plane root. |

### Windows / RPC / directory
| Port(s) | Protocol | Service | Risk |
| --- | --- | --- | --- |
| 135, 139, 445 | TCP | MS-RPC / NetBIOS / SMB | WannaCry; EternalBlue. |
| 389, 636 | TCP | LDAP / LDAPS | Credential theft. |
| 25 | TCP | SMTP | Open-relay spam. |

### Amplification vectors (non-TCP)
| Port(s) | Protocol | Service | Amplification factor |
| --- | --- | --- | --- |
| 53 | UDP | DNS | ~50-80× |
| 123 | UDP | NTP (MONLIST) | ~556× |
| 161 | UDP | SNMP | ~3-15× |
| 1900 | UDP | SSDP / UPnP | ~30× |
| 5353 | UDP | mDNS | Local enumeration |

### Maximum exposure
| Port(s) | Protocol | Risk |
| --- | --- | --- |
| 0-65535 | TCP | Every TCP service attackable. |
| All (`-1`) | ALL | TCP + UDP + ICMP + SCTP; worst case. |

### Non-critical (PUBLIC_NONCRITICAL when PUBLIC)
| Port(s) | Protocol | Notes |
| --- | --- | --- |
| 80 | TCP | Acceptable behind ALB; verify redirect to 443. |
| 443 | TCP | Acceptable for web-facing tiers behind ALB/WAF. |
| 8080 | TCP | Acceptable behind ALB; verify not admin panel. |

## Output format (Process — per security group)

```text
SECURITY_GROUP: <name>
VERDICT: OPEN | PUBLIC_NONCRITICAL | RESTRICTED
SEVERITY: Critical | High | Medium | Low | None
CIS_CONTROLS: <e.g., "5.1" or "5.2, 5.3" or "N/A">
REASON: <1-2 sentences citing the specific rules and per-rule verdicts>
REMEDIATION: <specific action, or "None required" if RESTRICTED>
```

## Pre-flight safety checks (Process — run before any remediation CLI)

- Capture current SG rule set: `aws ec2 describe-security-groups
  --group-ids <sg-id> --output json > /tmp/<sg-id>-backup-$(date +%s).json`.
- Verify rollback: after backup, confirm the file is non-empty and parses
  as valid JSON (`python3 -c "import json; json.load(open('<file>'))"`).
  A truncated/empty backup is useless for rollback.
- Prefer **additive** changes (add restrictive rule, verify, then remove
  open rule) over **destructive** changes (delete first).
- For OPEN verdicts on administrative ports (22, 3389, 2375, 6443,
  10250), confirm the operator has an alternative access path (SSM
  Session Manager, console, or another SG rule) BEFORE removing the
  open rule.
- Verify dependency impact:
  `aws ec2 describe-network-interfaces --filters Name=group-id,Values=<sg-id>`
  — removing a rule that a load balancer, peered VPC, or Lambda function
  depends on will cause an outage.
- For prefix-list sources, snapshot entries:
  `aws ec2 get-managed-prefix-list-entries --prefix-list-id <pl-id>
  --output json > /tmp/<pl-id>-backup-$(date +%s).json`.

## Remediation guidance (Process — per verdict)

For **OPEN** security groups:

- **SSH (22):** prefer AWS Systems Manager Session Manager — no open
  ports, IAM-authenticated, fully audited. Fallback: bastion SG ref.
- **RDP (3389):** restrict to a bastion or jump-SG ref.
- **Databases (3306, 5432, 1433, 1521, 27017, 6379, 9042, 5984, 11211,
  9200):** restrict to the application-tier SG ID ONLY. Database subnets
  should have no IGW route (private subnet with NAT, not public).
- **Elasticsearch (9200, 9300):** restrict to ingestion SG + dashboard
  SG; transport port (9300) never leaves the peer set.
- **Docker daemon (2375, 2376):** never expose to internet. Bind to
  localhost or private VPN; enable TLS client cert auth on 2376.
- **Kubernetes API (6443) / Kubelet (10250) / etcd (2379-2380):**
  restrict to control-plane and operator CIDRs. P0 remediation.
- **SMB (445) / NetBIOS (139):** remove entirely; restrict to
  directory-member SG references.
- **DNS (UDP 53):** if not a designated resolver, remove. If it IS a
  resolver, restrict to known client CIDRs and enable RRL.
- **SNMP (UDP 161):** restrict to monitoring SG; upgrade to SNMPv3
  authPriv.
- **Memcached UDP:** disable UDP entirely; amplification is severe.
- **All-ports (0-65535) / protocol -1:** delete and recreate with ONLY
  the specific ports the workload requires.

For **PUBLIC_NONCRITICAL** security groups:

- **Public HTTPS (443):** verify the SG is attached to an ALB/NLB, not
  directly to backend instances. The backend SG should reference the ALB
  SG ID, not `0.0.0.0/0`.
- **Public HTTP (80):** acceptable only for redirect-to-HTTPS.
- **ICMP:** restrict to a known monitoring CIDR; never allow ICMP ALL.

For **RESTRICTED** security groups:

- No remediation required for RFC 1918 / SG-ref / `/32` rules.
- If rules use `100.64.0.0/10` (CGNAT) or broad `/7`–`/9` CIDRs,
  flag for review.
- For customer-managed prefix-list references, schedule periodic
  re-audit of list entries — the list owner can add public CIDRs without
  changing the SG rule.
- Recommend enabling VPC Flow Logs for ongoing auditing.

## Recent AWS features (2024-2026)

- **Security group VPC associations (2024):** Security groups can now be associated with specific VPCs, and VPC-scoped security groups can be shared across accounts via RAM. Auditors should verify that cross-account shared security groups do not inadvertently grant inbound exposure to unexpected principals.
- **VPC Lattice security policy integration (2024-2025):** VPC Lattice uses its own authorization model but interacts with security groups. Auditors should note that Lattice-managed traffic may not appear in standard security group rule evaluation — verify that Lattice target groups have appropriate authorization policies.
- **Prefix list improvements (2024):** Managed prefix lists now support more entries and customer-managed prefix lists can be shared across accounts. Auditors should verify that shared prefix lists are governed — a compromised prefix list can silently widen security group ingress.

## Section taxonomy (CloudOps auditor pattern)

**Pattern:** CloudOps Auditor — `Mindset → Process → Reference → Tool`.
Each major section is tagged inline with its pattern role so the
structure is machine-recognizable and aids comprehension:

1. **Frontmatter** — name, description, version.
2. **Activation keywords** — discoverability terms.
3. **Quick verdict logic** — at-a-glance summary (progressive disclosure entry point).
4. **Reasoning framework** `[Mindset]` — the *why*.
5. **AWS dataplane expert details** `[Mindset]` — non-obvious AWS behavior.
6. **Classification logic** `[Process]` — per-rule evaluation then
   worst-case aggregation, as formal pseudocode.
7. **Risk scoring and compliance mapping** `[Process]` — CVSS severity +
   CIS/PCI-DSS/NIST control IDs.
8. **NEVER** `[Process]` — anti-patterns applied before verdict.
9. **Source classification** `[Reference]` — CIDR / SG-ref / prefix-list
   decision table.
10. **Prefix-list evaluation procedure** `[Reference]` — programmatic
    inspection.
11. **High-risk port registry** `[Reference]` — categorized port tables.
12. **Output format** `[Tool]` — per-SG report shape.
13. **Pre-flight safety checks** `[Process]` — non-destructive guards.
14. **Remediation guidance** `[Tool]` — per-verdict action plan.

## Domain

AWS CloudOps / EC2 Network Security & Compliance.

## AWS documentation

- **Amazon EC2 User Guide (Security Groups)** — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-security-groups.html
- **EC2 Security** — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-security.html
- **EC2 API Reference** — https://docs.aws.amazon.com/AWSEC2/latest/APIReference/
- **AWS CLI — ec2 command reference** — https://docs.aws.amazon.com/cli/latest/reference/ec2/
- **VPC security groups** — https://docs.aws.amazon.com/vpc/latest/userguide/vpc-security-groups.html
