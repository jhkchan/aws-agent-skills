---
name: vpc-peering-deployer
description: 'Provisions Amazon VPC peering connections with production defaults: requester/accepter model (create-vpc-peering-connection, accept-vpc-peering-connection), same-account vs cross-account peering, same-region vs inter-region peering, DNS resolution (allowDnsResolutionFromPeeredVpc), route table updates on BOTH sides (required for traffic to flow), security group cross-VPC references (same account+region only), limitations (no transitive routing, no edge-to-edge routing), and IPv6 support. Emits a READY_TO_DEPLOY checklist with verification commands. Use when creating a VPC peering connection, connecting two VPCs, setting up cross-account VPC peering, enabling inter-region VPC peering, or configuring DNS resolution across peered VPCs. Triggers: create vpc peering connection, cross-account vpc peering, inter-region vpc peering, vpc peering route table, vpc peering DNS resolution, vpc peering security group reference, accept vpc peering, vpc peering IPv6.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with ec2 access (and cross-account STS assume-role if cross-account peering). Works with Terraform aws_vpc_peering_connection / aws_vpc_peering_connection_accepter / aws_route resources and CloudFormation AWS::EC2::VPCPeeringConnection templates.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Networking
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, vpc, vpc-peering, cloudops, deploy, networking, provisioning, cross-account, inter-region, route-table, dns-resolution, security-group, ipv6
  dependencies: aws-orchestrator
  keywords: aws, vpc, vpc peering, peering connection, cloudops, deploy, provisioning, cross-account, inter-region, requester, accepter, route table, dns resolution, security group reference, ipv6, transitive routing, edge-to-edge
  when_to_use: Invoke when the user wants to create a VPC peering connection between two VPCs (same-account or cross-account, same-region or inter-region), configure DNS resolution across peered VPCs, update route tables on both sides for traffic flow, reference security groups across peered VPCs, or understand VPC peering limitations (no transitive routing). Do NOT invoke for AWS Transit Gateway (use transit-gateway skills), VPC endpoints (PrivateLink), or VPN/Direct Connect connectivity.
---

# VPC Peering Deployer

An AWS CloudOps agent skill that provisions Amazon VPC peering
connections with correct defaults. The skill walks the operator through
the requester/accepter model, same-account vs cross-account decisions,
same-region vs inter-region constraints, route table updates, DNS
resolution, security group cross-references, and peering limitations,
captures topology and routing decisions, explains why each default
matters, and emits a READY_TO_DEPLOY checklist with copy-pasteable
verification commands.

## Activation keywords

create VPC peering connection, cross-account VPC peering, inter-region
VPC peering, VPC peering route table, VPC peering DNS resolution, VPC
peering security group reference, accept VPC peering, VPC peering IPv6.

## STRICT output contract

When this skill is invoked with a VPC-peering-provisioning request
(create a peering connection, connect two VPCs, cross-account or inter-
region peering, DNS resolution, route tables, security group cross-
references, or a partial configuration), the agent MUST respond with the
READY_TO_DEPLOY checklist defined in the "Output format" section using
the literal all-caps labels `VPC_PEERING:`, `VERDICT:`, `CHECKLIST:`,
and `VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels breaks
automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Requester/accepter model | Core peering model |
| Step 2 — Same-account vs cross-account | Account topology |
| Step 3 — Same-region vs inter-region | Region topology |
| Step 4 — Create and accept the peering connection | Provisioning step |
| Step 5 — Route table updates (BOTH sides required) | Traffic flow |
| Step 6 — DNS resolution (allowDnsResolutionFromPeeredVpc) | DNS across VPCs |
| Step 7 — Security group cross-VPC references | SG cross-referencing |
| Step 8 — Limitations (no transitive routing) | Topology constraints |
| Step 9 — IPv6 support | IPv6 peering |
| Step 10 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/routing-and-dns.md | Route table + DNS detail |
| references/cross-account-and-security.md | Cross-account + SG detail |
| references/worked-examples.md | Create/accept CLI walkthroughs |
| references/error-handling.md | Failure triage |
| references/advanced-patterns.md | Recent features |

## Mindset

**One-line takeaway:** A VPC peering connection is a one-to-one network
link between two VPCs. The requester creates it; the accepter accepts
it. Traffic flows ONLY if route tables on BOTH sides are updated to
include the peered VPC's CIDR. Peering is NOT transitive — A peered to
B and B peered to C does NOT let A talk to C.

Three misconceptions dominate VPC peering misdesign at provisioning
time:

- **"Creating the peering connection is enough."** It is not. Creating
  and accepting the peering connection establishes the link, but NO
  traffic flows until route tables on BOTH the requester and accepter
  sides are updated to route traffic to the peered VPC's CIDR via the
  peering connection. This is the #1 cause of "my peering doesn't work"
  tickets.

- **"VPC peering supports transitive routing."** It does NOT. If VPC-A
  is peered to VPC-B, and VPC-B is peered to VPC-C, VPC-A CANNOT reach
  VPC-C through VPC-B. Each pair needs its own direct peering
  connection. For hub-and-spoke or transitive topologies, use AWS
  Transit Gateway.

- **"Security groups can reference peered VPC security groups across
  accounts."** Only partially true. Security group cross-VPC references
  (referencing a SG by its ID from a peered VPC) work ONLY when the
  peering is within the same account AND same region. Cross-account or
  inter-region peering cannot use SG cross-references — use CIDR-based
  rules instead.

## Configuration dependency graph (novel heuristic)

VPC peering configurations are NOT independent. The peering connection
must be accepted before route tables can reference it. DNS resolution
must be explicitly enabled. Security group cross-references have
account/region constraints. Use this graph to sequence provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Peering connection (requester) | requester VPC exists; accepter VPC ID known | connection is pending until accepted; accepter must be in the same region (same-region) or a different region (inter-region) | the peering link |
| Peering acceptance | requester created the connection; accepter account has permission | acceptance CANNOT be automated across accounts without IAM role assumption (accepter must call accept-vpc-peering-connection) | active peering connection |
| Route table (requester side) | peering connection ACTIVE; requester route table exists | route to peered CIDR via pcx-xxx MUST be added manually; without it NO traffic flows | requester → accepter traffic |
| Route table (accepter side) | peering connection ACTIVE; accepter route table exists | route to requester CIDR via pcx-xxx MUST be added manually; the accepter side is the #1 forgotten step | accepter → requester traffic |
| DNS resolution | peering connection ACTIVE | `AllowDnsResolutionFromPeeredVpc` must be set to true on BOTH VPCs (requester and accepter) for bidirectional DNS | DNS hostname resolution across VPCs |
| Security group cross-reference | peering connection ACTIVE; SAME account + SAME region only | cross-account or inter-region peering CANNOT use SG cross-references | SG rules referencing peered VPC's SG by ID |
| IPv6 routing | VPCs have IPv6 CIDR blocks assigned | IPv6 routes must be added separately (in addition to IPv4 routes) | IPv6 traffic across peering |

**The route-table-both-sides row is the one a baseline model misses.**
Creating and accepting the peering is necessary but NOT sufficient.
Both sides need explicit route table entries. The DNS resolution flag is
another commonly forgotten configuration. The procedure below forces an
explicit decision on each.

**Cross-dependency gotchas:**
- Route tables on BOTH sides must be updated. Adding a route on the
  requester side only enables one-directional traffic (requester →
  accepter). The return path (accepter → requester) needs its own route
  entry.
- DNS resolution requires the flag enabled on both VPCs. Enabling it on
  one side only does NOT work for bidirectional resolution.
- Security group cross-VPC references work ONLY within the same account
  and same region. For cross-account or inter-region peering, use CIDR-
  based security group rules.
- IPv4 and IPv6 routing are independent. If both are needed, add routes
  for both CIDR families.

## Expert heuristic: the two-sided route table requirement

A baseline model says "create and accept the peering." The correct
heuristic recognizes that the peering connection is a bidirectional
link, but route tables are per-VPC and per-direction.

```text
VPC-A (10.0.0.0/16)  ←── peering (pcx-xxx) ──→  VPC-B (10.1.0.0/16)

For VPC-A → VPC-B traffic:
  VPC-A route table needs: Destination 10.1.0.0/16 → Target pcx-xxx

For VPC-B → VPC-A traffic:
  VPC-B route table needs: Destination 10.0.0.0/16 → Target pcx-xxx

Missing either route = traffic flows in ONE direction only (or not at all).
Both routes are needed for bidirectional communication.
```

**Key implication:** the #1 cause of "my peering doesn't work" is a
missing route table entry on the accepter side. Always verify BOTH
sides have routes pointing to the peering connection.

## Expert heuristic: when to use peering vs Transit Gateway

VPC peering is one-to-one. Transit Gateway is hub-and-spoke (many-to-
many). The decision depends on topology.

```text
Number of VPCs to connect:
  ├── 2 VPCs → VPC peering (simplest, no additional cost beyond data transfer)
  ├── 3-4 VPCs, full mesh → VPC peering (n*(n-1)/2 connections; manageable)
  │     3 VPCs = 3 peering connections
  │     4 VPCs = 6 peering connections
  ├── 5+ VPCs, or hub-and-spoke → Transit Gateway (avoids peering explosion)
  │     5 VPCs full mesh = 10 peering connections; TGW = 1 attachment per VPC
  ├── Need transitive routing (A→B→C) → Transit Gateway (peering is NOT transitive)
  ├── Need VPN/Direct Connect integration → Transit Gateway
  └── Cost-sensitive, 2 VPCs → VPC peering (no hourly TGW charge)
```

**Key implication:** peering is free (no per-hour charge; you pay only
for data transfer). Transit Gateway charges per-hour per-attachment plus
data processing. For 2 VPCs, peering is almost always the right choice.
For 5+ VPCs or transitive routing, Transit Gateway is better.

## Expert heuristic: cross-account acceptance automation

In cross-account peering, the accepter account must call
`accept-vpc-peering-connection`. This requires either manual action in
the accepter account's console/CLI, or automated role assumption.

```text
Cross-account peering flow:
  1. Requester account creates the peering connection (create-vpc-peering-connection)
     → Connection status: pending-acceptance
  2. Accepter account accepts (accept-vpc-peering-connection)
     → Requires IAM permission in the accepter account
     → Options:
       ├── Manual: operator logs into accepter account, runs accept
       ├── Automated: requester assumes a role in accepter account via STS
       │   aws sts assume-role --role-arn arn:aws:iam::<accepter>:role/...
       │   → then call accept-vpc-peering-connection with accepter credentials
       └── Lambda/EventBridge: accepter account auto-accepts via EventBridge rule
  3. Connection status: active
  4. Both sides update route tables
```

**Key implication:** cross-account peering adds an acceptance step that
same-account peering does not. Plan for the IAM role or manual step.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Requester VPC exists | Peering requires an existing VPC | `aws ec2 describe-vpcs --vpc-ids <vpc-id>` |
| Accepter VPC ID known | Must specify the peer VPC at creation | Confirm VPC ID in the accepter account |
| CIDR blocks do NOT overlap | Overlapping CIDRs break routing; peering may create but traffic fails | Compare VPC CIDRs |
| AWS account IDs (if cross-account) | Cross-account peering needs both account IDs | `aws sts get-caller-identity` |
| Regions identified (if inter-region) | Inter-region peering specifies peer region | Confirm both regions |
| IAM permission in accepter account | Accepter must accept the connection | Verify `ec2:AcceptVpcPeeringConnection` |
| Route table IDs identified | Routes must be added to specific route tables | `aws ec2 describe-route-tables` |
| DNS resolution decision | Must be explicitly enabled on both sides | Assess DNS requirements |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Requester/accepter model

VPC peering uses a requester/accepter model. The requester creates the
peering connection; the accepter accepts it.

| Role | Action | API call |
|---|---|---|
| Requester | Creates the peering connection | `create-vpc-peering-connection` |
| Accepter | Accepts the peering connection | `accept-vpc-peering-connection` |
| Both | Update route tables | `create-route` (each side) |

**Same-account peering:** the requester can auto-accept if it has
permission. The accepter role is the same account.

**Cross-account peering:** the accepter is a DIFFERENT account. The
accepter must explicitly accept (manually or via role assumption).

## Step 2 — Same-account vs cross-account

| Feature | Same-account | Cross-account |
|---|---|---|
| Acceptance | Can be auto-accepted (if IAM permits) | Must be explicitly accepted by accepter account |
| Security group cross-references | Supported (same account) | NOT supported (use CIDR rules) |
| IAM complexity | Single account | Need role assumption or manual acceptance |
| Peering limit | 125 active peering connections per VPC (soft limit) | Same |

**Cross-account requires:** the accepter account's VPC ID AND account
ID at creation time. The requester specifies `--peer-owner-id`.

## Step 3 — Same-region vs inter-region

| Feature | Same-region | Inter-region |
|---|---|---|
| Latency | Minimal (within-region) | Slightly higher (cross-region backbone) |
| Data transfer cost | Standard intra-region | Cross-region data transfer charges apply |
| Security group cross-references | Supported (same region) | NOT supported (use CIDR rules) |
| DNS resolution | Supported | Supported (with flag on both sides) |
| `--peer-region` | Not needed (same region) | REQUIRED (must specify peer region) |
| Max inter-region peerings | N/A | 125 per VPC (soft limit) |

**Inter-region data transfer cost** is the primary trade-off. Inter-
region traffic incurs cross-region data transfer charges (~$0.01-$0.02
per GB depending on regions). Same-region peering has standard intra-
region data transfer rates.

## Step 4 — Create and accept the peering connection

Step 4 — create/accept CLI walkthroughs (same-account, cross-account, inter-region) — moved verbatim.
Full detail: [Worked examples](references/worked-examples.md).

**Common mistake:** trying to update route tables before the connection
is ACTIVE. Route creation fails if the peering is still
`pending-acceptance`.

## Step 5 — Route table updates (BOTH sides required)

Route tables on BOTH the requester and accepter sides must be updated
to route traffic to the peered VPC's CIDR via the peering connection.
This is the most commonly forgotten step.

Step 5 — route table update commands (both sides required) — moved verbatim.
Full detail: [Routing and DNS](references/routing-and-dns.md).

**Critical:** BOTH routes are needed for bidirectional traffic. Missing
the accepter-side route is the #1 cause of "peering doesn't work."

For multiple route tables per VPC (e.g., public and private subnets),
update EACH route table that needs to route to the peered VPC.

## Step 6 — DNS resolution (allowDnsResolutionFromPeeredVpc)

By default, DNS hostnames from one VPC are NOT resolvable from the
peered VPC. To enable cross-VPC DNS resolution, set
`AllowDnsResolutionFromPeeredVpc` to true on the peering connection.

Step 6 — DNS resolution enablement commands (both sides) — moved verbatim.
Full detail: [Routing and DNS](references/routing-and-dns.md).

**Critical:** BOTH sides must enable the flag for bidirectional DNS
resolution. Enabling it on one side only does NOT work.

**Prerequisites for DNS resolution:**
- Both VPCs must have `enableDnsHostnames` and `enableDnsSupport` set
  to true.
- The peering connection must be ACTIVE.

## Step 7 — Security group cross-VPC references

Security group cross-VPC references allow a SG rule to reference a
security group in the peered VPC by its ID (e.g., `sg-xxx` from the
peer VPC). This is more precise than CIDR-based rules.

**Constraint: only works within the SAME account AND SAME region.**
Cross-account or inter-region peering CANNOT use SG cross-references.
Use CIDR-based rules instead.

Step 7 — SG cross-reference vs CIDR-based rule commands — moved verbatim.
Full detail: [Cross-account and security](references/cross-account-and-security.md).

## Step 8 — Limitations (no transitive routing)

VPC peering has hard limitations. A baseline model may not surface
these; they are critical for topology design.

| Limitation | Description | Workaround |
|---|---|---|
| No transitive routing | A→B and B→C does NOT allow A→C | Create direct A→C peering, or use Transit Gateway |
| No edge-to-edge routing | Traffic cannot traverse a peering to reach a VPN/Direct Connect/IGW on the peer side | Use Transit Gateway for VPN/DX integration |
| Overlapping CIDRs | Peering with overlapping CIDRs breaks routing (may create but traffic fails) | Re-design CIDR allocation; use non-overlapping ranges |
| Max peering connections | 125 active peerings per VPC (soft limit) | Request limit increase, or use Transit Gateway |
| SG cross-references | Same account + same region only | Use CIDR-based rules for cross-account/inter-region |

**The no-transitive-routing limitation is the most impactful.** Many
operators assume that peering VPC-A to VPC-B and VPC-B to VPC-C allows
VPC-A to reach VPC-C. It does NOT. Each pair needs a direct peering
connection. For transitive topologies, use AWS Transit Gateway.

## Step 9 — IPv6 support

VPC peering supports IPv6 traffic if both VPCs have IPv6 CIDR blocks
assigned. IPv6 routes must be added separately (in addition to IPv4
routes).

Step 9 — IPv6 route commands (both sides) — moved verbatim.
Full detail: [Routing and DNS](references/routing-and-dns.md).

IPv4 and IPv6 routing are independent. Both must be configured if both
protocols are needed.

## Step 10 — Recent features

Step 10 — recent AWS features (2023-2026) — moved verbatim.
Full detail: [Advanced Patterns](references/advanced-patterns.md).

## NEVER do these things

1. **NEVER assume creating and accepting the peering is enough.** Route
   tables on BOTH sides must be updated. Without routes, NO traffic
   flows. The accepter-side route is the #1 forgotten step.

2. **NEVER assume VPC peering supports transitive routing.** A→B and
   B→C does NOT allow A→C. Each pair needs a direct peering connection.
   For transitive topologies, use Transit Gateway.

3. **NEVER peer VPCs with overlapping CIDR blocks.** The peering may
   create, but routing fails because the destination CIDR is ambiguous.
   Always verify non-overlapping CIDRs before creating the peering.

4. **NEVER use security group cross-VPC references for cross-account or
   inter-region peering.** SG cross-references work ONLY within the same
   account AND same region. For cross-account or inter-region, use
   CIDR-based SG rules.

5. **NEVER enable DNS resolution on only one side.**
   `AllowDnsResolutionFromPeeredVpc` must be true on BOTH the requester
   AND accepter for bidirectional DNS resolution. One-sided enablement
   does not work.

6. **NEVER forget IPv6 routes if using IPv6.** IPv4 and IPv6 routing
   are independent. Add IPv6 routes separately (using
   `--destination-ipv6-cidr-block`) if IPv6 traffic is needed.

7. **NEVER assume route table updates propagate automatically.** Each
   route table in each VPC must be explicitly updated. If a VPC has
   multiple route tables (e.g., public/private subnets), update EACH
   one that needs to route to the peered VPC.

8. **NEVER use VPC peering for edge-to-edge routing.** Traffic cannot
   traverse a peering to reach a VPN, Direct Connect, or Internet
   Gateway on the peer side. Use Transit Gateway for these patterns.

9. **NEVER create peering connections without a CIDR overlap check.**
   Always compare VPC CIDR blocks before creating the peering.
   Overlapping CIDRs are a silent failure (peering creates, traffic
   fails).

10. **NEVER assume cross-account acceptance is automatic.** The
    accepter account must explicitly accept the peering connection
    (manually or via IAM role assumption). Plan for the acceptance
    step.

## Output format

```text
VPC_PEERING: <requester-vpc-id> ↔ <accepter-vpc-id> (<pcx-id>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Requester VPC: <vpc-id> (<cidr>)
  [✓|✗] Accepter VPC: <vpc-id> (<cidr>)
  [✓|✗] CIDR overlap check: PASS (non-overlapping) | FAIL (overlapping)
  [✓|✗] Account topology: Same-account | Cross-account (requester <acct>, accepter <acct>)
  [✓|✗] Region topology: Same-region (<region>) | Inter-region (requester <region>, accepter <region>)
  [✓|✗] Peering connection: <pcx-id> — ACTIVE
  [✓|✗] Route table (requester): <rtb-id> → <peer-cidr> via <pcx-id>
  [✓|✗] Route table (accepter): <rtb-id> → <peer-cidr> via <pcx-id>
  [✓|✗] DNS resolution: AllowDnsResolutionFromPeeredVpc=true (both sides) | Disabled
  [✓|✗] Security group: cross-VPC reference (same acct+region) | CIDR-based (cross-account/inter-region)
  [✓|✗] IPv6 routing: enabled (IPv6 routes added both sides) | IPv4 only
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws ec2 describe-vpc-peering-connections --vpc-peering-connection-ids <pcx-id> --region <region>
  aws ec2 describe-route-tables --route-table-ids <requester-rtb> --region <region>
  aws ec2 describe-route-tables --route-table-ids <accepter-rtb> --region <region>
```

### Worked example — same-account, same-region peering with DNS resolution

```text
VPC_PEERING: vpc-aaa11122 ↔ vpc-bbb22233 (pcx-111222333)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Requester VPC: vpc-aaa11122 (10.0.0.0/16)
  [✓] Accepter VPC: vpc-bbb22233 (10.1.0.0/16)
  [✓] CIDR overlap check: PASS (10.0.0.0/16 and 10.1.0.0/16 do not overlap)
  [✓] Account topology: Same-account (123456789012)
  [✓] Region topology: Same-region (us-east-1)
  [✓] Peering connection: pcx-111222333 — ACTIVE
  [✓] Route table (requester): rtb-app111 → 10.1.0.0/16 via pcx-111222333
  [✓] Route table (accepter): rtb-data222 → 10.0.0.0/16 via pcx-111222333
  [✓] DNS resolution: AllowDnsResolutionFromPeeredVpc=true (both sides)
  [✓] Security group: cross-VPC reference (sg-app → sg-data via peering)
  [✓] IPv6 routing: IPv4 only
  [✓] Tags: Environment=production, Topology=app-to-data
VERIFICATION_COMMANDS:
  aws ec2 describe-vpc-peering-connections --vpc-peering-connection-ids pcx-111222333 --region us-east-1
  aws ec2 describe-route-tables --route-table-ids rtb-app111 --region us-east-1
  aws ec2 describe-route-tables --route-table-ids rtb-data222 --region us-east-1
```

## Error handling

Error handling deep dives — moved verbatim.
Full detail: [Error handling](references/error-handling.md).

## References (load on demand)

- [Routing and DNS](references/routing-and-dns.md) — route table update commands (both sides), DNS resolution commands, IPv6 routes
- [Cross-account and security](references/cross-account-and-security.md) — acceptance automation, SG cross-reference vs CIDR-based rule commands
- [Worked examples](references/worked-examples.md) — create/accept CLI walkthroughs (same-account, cross-account, inter-region)
- [Error handling](references/error-handling.md) — pending-acceptance, no-traffic, DNS, SG-reference, CIDR-overlap fixes
- [Advanced patterns](references/advanced-patterns.md) — recent features 2023-2026

## Domain

AWS CloudOps / Amazon VPC Peering Connection Provisioning & Network
Connectivity.

## AWS documentation

- **VPC Peering Guide** — https://docs.aws.amazon.com/vpc/latest/peering/what-is-vpc-peering.html
- **Create peering connection** — https://docs.aws.amazon.com/vpc/latest/peering/create-vpc-peering-connection.html
- **Accept peering connection** — https://docs.aws.amazon.com/vpc/latest/peering/accept-vpc-peering-connection.html
- **Route tables for peering** — https://docs.aws.amazon.com/vpc/latest/peering/vpc-peering-routing.html
- **DNS resolution** — https://docs.aws.amazon.com/vpc/latest/peering/modify-peering-connection-options.html
- **Security group references** — https://docs.aws.amazon.com/vpc/latest/peering/security-group-references.html
- **Inter-region peering** — https://docs.aws.amazon.com/vpc/latest/peering/inter-region-peering.html
- **VPC peering limits** — https://docs.aws.amazon.com/vpc/latest/peering/vpc-peering-limitations.html
- **IPv6 in VPCs** — https://docs.aws.amazon.com/vpc/latest/userguide/vpc-ip-addressing.html#vpc-ipv6
