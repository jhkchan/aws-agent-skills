---
name: transit-gateway-routing-troubleshooter
description: 'Diagnoses AWS Transit Gateway routing failures through a fourteen-layer diagnostic tree: TGW route table association vs propagation (separate controls), static route priority (static beats propagated), overlapping CIDR blocks across attachments, peering attachment non-transitivity (VPC-A→TGW-A←peering→TGW-B→VPC-C requires direct peering, no transitive hop), VPN/Direct Connect gateway routing, multicast domain membership, TGW flow logs gaps, VPC route table default route 0.0/0 pointing at TGW, TGW attachment placed in the wrong subnet/AZ, cross-VPC security group references (not supported through TGW), DNS resolution across TGW attachments, appliance mode forcing traffic through an inspection VPC, and blackhole route detection. Walks symptoms to a verified root cause with evidence-backed read-only probes; emits ROOT_CAUSE_IDENTIFIED or INSUFFICIENT_DATA.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline symptom classification works from pasted topology and error messages. Live-account diagnosis uses aws ec2 describe-transit-gateways, describe-transit-gateway-attachments, describe-transit-gateway-route-tables, get-transit-gateway-route-table-associations, get-transit-gateway-route-table-propagations, search-transit-gateway-routes, describe-route-tables, describe-vpn-connections...
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
  when_to_use: Diagnosing a Transit Gateway routing failure (traffic from one attached VPC never reaches another attached VPC, traffic takes the wrong path, traffic is asymmetrically dropped, peering between two TGWs does not forward, VPN/DX routing through TGW is broken, multicast traffic does not reach all members, appliance-mode inspection VPC drops cross-AZ return traffic, or a default route 0.0/0 pointing at the TGW produces a blackhole). Use when the symptom is "VPC-A cannot reach VPC-B through the transit gateway" and the cause may be route table association/propagation, static-route priority, overlapping CIDR, non-transitive peering, wrong-subnet attachment, missing appliance mode, or a missing TGW route table entry.
  when_not_to_use: Provisioning a new TGW or attachment (use transit-gateway-deployer), VPC peering (non-TGW) connectivity (use vpc-peering-deployer), VPC endpoint / PrivateLink connectivity inside a single VPC (use vpc-connectivity-troubleshooter), or TGW cost / capacity posture audits (use networkmanager-core-network-auditor). This skill diagnoses routing failures at runtime; it does not provision or audit steady-state posture.
  activation_triggers: VPC cannot reach VPC through transit gateway, TGW traffic blackhole, TGW route table missing entry, TGW static route overrides propagated, transit gateway peering non-transitive, TGW appliance mode cross-AZ return, TGW overlapping CIDR, TGW default route 0.0.0.0/0, TGW attachment wrong subnet, TGW VPN routing, TGW Direct Connect routing, TGW multicast not received, TGW DNS resolution across attachments, TGW flow logs missing, security group cross-VPC TGW, troubleshoot transit gateway routing
  invocation_schema: 'Input: either (a) a symptom description ("VPC-A cannot reach VPC-B through TGW", "traffic exits VPC-A but never arrives at VPC-B", "TGW peering between two regions does not forward"), optionally paired with the TGW topology (attachment IDs, VPC CIDRs, route table IDs), OR (b) a TGW ID plus the source/destination VPC IDs and observed packet-flow symptom for live-account diagnosis. Output: a deterministic TARGET/VERDICT/REASON/LAYER/EVIDENCE/REMEDIATION block where VERDICT ∈ {ROOT_CAUSE_IDENTIFIED, INSUFFICIENT_DATA} and LAYER ∈ {TGW_ROUTE_TABLE_ASSOCIATION, TGW_ROUTE_TABLE_PROPAGATION, TGW_STATIC_ROUTE_PRIORITY, TGW_OVERLAPPING_CIDR, TGW_PEERING_NON_TRANSITIVE, TGW_VPN_DX_ROUTING, TGW_MULTICAST_DOMAIN, TGW_FLOW_LOGS, VPC_DEFAULT_ROUTE_TGW, TGW_ATTACHMENT_WRONG_SUBNET, TGW_SG_CROSS_VPC, TGW_DNS_RESOLUTION, TGW_APPLIANCE_MODE, TGW_BLACKHOLE_ROUTE, UNKNOWN}.'
  invocation_example: '# Minimal valid input (offline symptom classification):

    Symptom: "EC2 instance i-aaa in VPC vpc-a (10.10.0.0/16, us-east-1)

    cannot reach EC2 instance i-bbb in VPC vpc-b (10.20.0.0/16, us-east-1)

    through transit gateway tgw-aaa. The ping times out. Both VPCs are

    attached to the TGW; the VPC-A route table has 10.20.0.0/16 → tgw-aaa."

    TGW: tgw-aaa

    Attachment A: tgw-attach-aaa (VPC vpc-a, subnet subnet-a-aaa, AZ us-east-1a)

    Attachment B: tgw-attach-bbb (VPC vpc-b, subnet subnet-b-aaa, AZ us-east-1a)

    VPC-A route table: 10.20.0.0/16 → tgw-aaa

    VPC-B route table: (default route 0.0.0.0/0 → igw-bbb; no entry for 10.10.0.0/16)'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Transit Gateway, TGW, route table, association, propagation, static route, propagated route, overlapping CIDR, peering attachment, non-transitive, VPN, Direct Connect, multicast domain, flow logs, default route, appliance mode, inspection VPC, blackhole, security group, cross-VPC, DNS resolution, troubleshooting
  tags: transit-gateway, networking, troubleshooting, routing, tgw, peering, vpn, direct-connect, appliance-mode, multicast
---

# Transit Gateway Routing Troubleshooter

## Quick start

- **Symptom → layer map (first plausible match drives the first probe):**
  Traffic exits source VPC but never arrives at destination VPC →
  TGW_ROUTE_TABLE_ASSOCIATION / TGW_ROUTE_TABLE_PROPAGATION /
  VPC_DEFAULT_ROUTE_TGW (return path); traffic reaches the wrong VPC
  → TGW_STATIC_ROUTE_PRIORITY / TGW_OVERLAPPING_CIDR; TGW peering
  between two TGWs forwards one way but not the other →
  TGW_PEERING_NON_TRANSITIVE; cross-AZ return traffic through an
  inspection VPC is dropped → TGW_APPLIANCE_MODE; VPN/DX advertises
  routes but VPC cannot reach on-prem → TGW_VPN_DX_ROUTING; multicast
  sender works but receivers see nothing → TGW_MULTICAST_DOMAIN;
  cross-VPC DNS hostname resolution fails → TGW_DNS_RESOLUTION;
  TGW flow logs are empty → TGW_FLOW_LOGS.
- **Always verify with a read-only probe, never guess.** Each layer
  has a single command that proves or disproves it. A
  ROOT_CAUSE_IDENTIFIED verdict requires positive evidence — a
  failing probe that matches the symptom — not a process of
  elimination.
- **Route table association and propagation are SEPARATE controls.**
  Associating an attachment with a TGW route table determines which
  route table that attachment LOOKS UP routes in. Propagating an
  attachment into a route table determines which route table LEARNS
  that attachment's CIDR. An attachment can be associated with one
  route table and propagate into many. Operators who "added the VPC
  to the TGW" but never propagated the attachment into the peer's
  route table produce a one-way blackhole.
- **Static routes ALWAYS beat propagated routes in the same TGW route
  table.** A `search-transit-gateway-routes` result showing a static
  `10.20.0.0/16 → tgw-attach-wrong` entry explains why the
  auto-propagated `10.20.0.0/16 → tgw-attach-correct` route never
  wins. This is the #1 misdiagnosis in TGW incidents.
- **TGW peering is strictly non-transitive.** If `tgw-a` peers with
  `tgw-b`, and `tgw-b` peers with `tgw-c`, traffic from an attachment
  on `tgw-a` CANNOT reach an attachment on `tgw-c` through `tgw-b` as
  a hop. Each pair of TGWs that needs to exchange traffic requires a
  direct peering attachment. There is no "transitive peering" feature.
- **Appliance mode forces cross-AZ return traffic through the
  inspection VPC.** Without appliance mode, TGW preserves the source
  AZ. A stateful inspection appliance in `us-east-1a` never sees the
  `us-east-1b` return traffic and drops the flow. Enabling appliance
  mode on the inspection VPC attachment routes the return through the
  appliance's AZ regardless of the original source AZ.

## Mindset

A TGW routing incident is almost always a route-table control-plane
problem wearing a "network is broken" costume. The TGW data plane
forwards packets along the routes it has learned; the failure is
upstream of forwarding — in association, propagation, static-route
priority, appliance mode, or overlapping CIDR. Senior network
engineers do not start by running packet captures; they start with
`search-transit-gateway-routes` and the route table associations on
both the source and destination attachments.

## Philosophy

Four behaviours separate a senior TGW engineer from a generalist:

- **Routing is bidirectional.** A successful ping from VPC-A to VPC-B
  requires VPC-A's route table to send traffic to the TGW AND the
  destination VPC-B's route table (or a default route in VPC-B) to
  send the reply back to the TGW. Operators who prove only the
  forward path chase ghosts for hours. Always probe both directions.
- **The TGW route table is per-attachment, not per-TGW.** A TGW has
  one or more route tables; each VPC attachment is associated with
  exactly one (the "association"). Routes are looked up in the
  associated route table. An attachment whose associated route table
  lacks the destination CIDR drops the packet, even if a different
  TGW route table has the route.
- **Default route 0.0.0.0/0 to TGW is a common footgun.** A VPC route
  table with `0.0.0.0/0 → tgw-aaa` sends ALL non-local traffic to
  the TGW, including internet-bound traffic that should go to the
  IGW. The TGW has no path to the internet (it is not a NAT); the
  traffic is blackholed. Always check whether the VPC route table's
  default route points at the IGW (correct for internet) or the TGW
  (correct only for a centralized egress design with a dedicated
  egress VPC).
- **TGW does NOT support cross-VPC security group references.** Unlike
  VPC peering, where `sg-aaa` in VPC-A can reference `sg-bbb` in
  VPC-B as a source rule, TGW-attached VPCs CANNOT reference each
  other's security groups. The SG rule must use a CIDR block, a
  prefix list, or another SG in the SAME VPC. Operators who "set up
  the security group peering" for a TGW topology produce a silent
  allow-list failure.

## Quick reference — symptom triage table

| Symptom phrase / observation | Most likely layer | First probe |
|---|---|---|
| Source VPC route table has `10.20.0.0/16 → tgw-aaa`, traffic leaves but never arrives | TGW_ROUTE_TABLE_ASSOCIATION / TGW_ROUTE_TABLE_PROPAGATION / VPC_DEFAULT_ROUTE_TGW (return path) | `get-transit-gateway-route-table-associations`, `search-transit-gateway-routes` for the destination CIDR |
| Traffic reaches the WRONG VPC; ping returns a host that is not the intended target | TGW_STATIC_ROUTE_PRIORITY / TGW_OVERLAPPING_CIDR | `search-transit-gateway-routes --filter type=static` |
| TGW peering between two regions: one direction works, reverse does not | TGW_PEERING_NON_TRANSITIVE (or one side missing a static/propagated route) | `describe-transit-gateway-peering-attachments` on both TGWs; route tables on both sides |
| Cross-AZ stateful firewall / inspection appliance drops flows intermittently | TGW_APPLIANCE_MODE | `describe-transit-gateway-attachments` (ApplianceMode on the inspection attachment) |
| VPN or Direct Connect advertises routes into TGW but VPC cannot reach on-prem | TGW_VPN_DX_ROUTING | `search-transit-gateway-routes` for the on-prem CIDR; VPN CGW configuration |
| Multicast sender succeeds; receivers see nothing | TGW_MULTICAST_DOMAIN | `describe-transit-gateway-multicast-domains`, `search-transit-gateway-multicast-groups` |
| Cross-VPC DNS hostname (e.g. `service.vpc-b`) does not resolve from VPC-A | TGW_DNS_RESOLUTION | VPC `enableDnsHostnames` / `enableDnsSupport`, Route 53 Resolver endpoints |
| TGW flow logs are empty even though traffic is flowing | TGW_FLOW_LOGS | `describe-flow-logs --resource-type transit-gateway`, IAM role for the flow log |
| Cross-VPC security group rule with peer-VPC SG reference does not allow traffic | TGW_SG_CROSS_VPC | `describe-security-groups` (the source reference is invalid cross-VPC) |
| None of the above, intermittent loss | UNKNOWN | Reachability Analyzer, TGW flow logs, VPC flow logs |

## Pre-flight: TGW state and gather-info gate

Before symptom-specific probes, gather the canonical TGW topology
and short-circuit on attachment states that mimic routing failures.

### Pre-flight commands

```bash
# TGW and its route tables
aws ec2 describe-transit-gateways --transit-gateway-ids <tgw-id> --output json
aws ec2 describe-transit-gateway-route-tables \
  --filters Name=transit-gateway-id,Values=<tgw-id> --output json

# All attachments (VPC, VPN, Peering, Connect, Direct Connect gateway)
aws ec2 describe-transit-gateway-attachments \
  --filters Name=transit-gateway-id,Values=<tgw-id> --output json

# Association and propagation per route table
aws ec2 get-transit-gateway-route-table-associations \
  --transit-gateway-route-table-id <rtb-id> --output json
aws ec2 get-transit-gateway-route-table-propagations \
  --transit-gateway-route-table-id <rtb-id> --output json

# Search the actual routes the TGW will use
aws ec2 search-transit-gateway-routes \
  --transit-gateway-route-table-id <rtb-id> \
  --filters Name=state,Values=active --output json

# Flow logs on the TGW
aws ec2 describe-flow-logs \
  --filter Name=resource-type,Values=transit-gateway --output json
```

### Attachment-state short-circuit

| `State` | Effect on diagnosis |
|---|---|
| `available` | Proceed with symptom-driven diagnosis. |
| `pending` / `modifying` | An attachment change is in flight. Routing may be unstable; wait for `available`. |
| `failed` | The attachment itself failed (peering rejected, VPN tunnels down). Treat as root-cause evidence. |
| `deleting` / `deleted` | The attachment is gone; traffic to its CIDR blackholes. Often an undiscussed Terraform apply. |
| `rejecting` / `rejected` (peering) | Peer TGW rejected the peering; no traffic will ever flow. |

### Malformed-input fallback

If the input is missing TGW ID, source/destination context, or a
symptom description:

```text
TARGET: <tgw-id or unknown>
VERDICT: INSUFFICIENT_DATA
REASON: Input is missing required context — at minimum a TGW ID, a
  source attachment (or source VPC + CIDR), a destination attachment
  (or destination VPC + CIDR), and a symptom description.
LAYER: UNKNOWN
EVIDENCE:
  - Missing: <list specific missing fields>
REMEDIATION: Re-prompt the operator for: (1) the TGW ID, (2) the
  source VPC ID and CIDR, (3) the destination VPC ID and CIDR, (4)
  whether peering, VPN, or Direct Connect is involved, and (5) the
  observed symptom.
```

## Process — Diagnostic decision tree (apply in symptom order)

Pick the entry point based on the symptom. Each layer ends with
either a positive root-cause confirmation (a failing probe that
matches the symptom) or a pass that moves to the next layer. **Never
emit ROOT_CAUSE_IDENTIFIED without a failing probe that matches the
symptom.**

### Step 0: Operational gotchas that change diagnosis

- **Association and propagation are independent controls.** Associating
  VPC-A's attachment with `tgw-rtb-default` makes it the lookup table
  for VPC-A's outbound traffic. Propagating VPC-B's attachment into
  `tgw-rtb-default` adds VPC-B's CIDR as a route. A working VPC-A →
  VPC-B path requires BOTH. Operators who "added both VPCs to the
  TGW" but only configured association (or only propagation) produce
  a silent blackhole.
- **Static routes ALWAYS win over propagated routes for the same
  CIDR in the same route table.** TGW priority: longest prefix wins;
  for equal prefix length, static beats propagated. A static
  `10.20.0.0/16 → tgw-attach-wrong` entry hides the propagated
  `10.20.0.0/16 → tgw-attach-correct` entry. Invisible without
  explicitly searching for static routes.
- **TGW peering attachments are strictly non-transitive.** A peering
  between `tgw-a` and `tgw-b` carries traffic between attachments on
  those two TGWs only. If `tgw-a` needs to reach `tgw-c`, establish
  a direct peering — `tgw-b` does not transit.
- **Appliance mode is per-attachment, not per-TGW.** Enable it on the
  INSPECTION VPC's attachment. With it on, TGW routes return traffic
  for any flow that transited the inspection VPC back through the
  inspection VPC's AZ, regardless of source AZ. Without it, source-AZ
  preservation causes cross-AZ stateful firewalls to drop flows.
- **TGW does not support SG references across VPCs.** Cross-VPC SG
  references work in VPC peering (same region), NOT through TGW.
  Frequent confusion when migrating from VPC peering to TGW.
- **TGW route tables do NOT learn VPC peering routes.** If VPC-A is
  peered with VPC-B (direct VPC peering) AND VPC-A is attached to a
  TGW, VPC-B's CIDR is NOT propagated into the TGW.
- **The default route `0.0.0.0/0` in a VPC route table pointing at
  the TGW is only valid in a centralized-egress design.** Otherwise
  internet-bound traffic blackholes at the TGW.
- **Multicast on TGW requires a dedicated multicast domain, and IGMP
  is not supported.** Members are statically added by ENI. A sender
  succeeds; receivers see nothing if their ENI is not in the group.
- **DNS resolution across TGW-attached VPCs requires Route 53
  Resolver.** VPC-A's `enableDnsHostnames` only resolves names within
  VPC-A. Deploy Resolver inbound/outbound endpoints for cross-VPC
  resolution.
- **TGW attachments are placed in specific subnets/AZs.** An
  attachment in `subnet-a-public us-east-1a` only has a data-plane
  ENI in `us-east-1a`. Cross-AZ traffic from `us-east-1b` to the TGW
  incurs a cross-AZ hop.
- **TGW flow logs capture only the TGW's view of the flow.** A flow
  that enters the TGW and is blackholed appears as `ACCEPT` ingress
  with no corresponding egress. Correlate VPC flow logs (source +
  destination sides) for end-to-end debugging.

### Step 1: Symptom entry

| Symptom | Branch |
|---|---|
| Source-to-destination traffic blackholes (one direction) | Step 2 |
| Return traffic blackholes (forward path works) | Step 2c |
| Traffic reaches the wrong target VPC | Step 3 |
| TGW peering (cross-TGW) does not forward | Step 4 |
| Inspection VPC drops cross-AZ flows | Step 5 |
| VPN/DX routes advertised but VPC cannot reach on-prem | Step 6 |
| Multicast sender OK, receivers silent | Step 7 |
| Cross-VPC DNS hostname does not resolve | Step 8 |
| TGW flow logs empty | Step 8b |
| Cross-VPC SG reference does not allow traffic | Step 8c |
| None of the above | Step 9 |

### Step 2: Route table association / propagation

Symptom: traffic leaves VPC-A but never arrives at VPC-B.

#### 2a: Source attachment's associated route table

```bash
aws ec2 describe-transit-gateway-attachments \
  --filters Name=transit-gateway-attachment-id,Values=<source-attach-id> \
  --output json | jq '.TransitGatewayAttachments[].Association.TransitGatewayRouteTableId'
```

If the source attachment has NO association, **ROOT_CAUSE_IDENTIFIED**
with `LAYER: TGW_ROUTE_TABLE_ASSOCIATION`. The TGW has no lookup
table for its outbound traffic.

#### 2b: Destination CIDR in the associated route table

```bash
aws ec2 search-transit-gateway-routes \
  --transit-gateway-route-table-id <source-rtb-id> \
  --filters Name=type,Values=propagated,static --output json | \
  jq '.Routes[] | select(.DestinationCidrBlock | startswith("<dest-cidr-prefix>"))'
```

If the destination CIDR is NOT present, the destination attachment
was not propagated. **ROOT_CAUSE_IDENTIFIED** with
`LAYER: TGW_ROUTE_TABLE_PROPAGATION`.

#### 2c: Return path (destination → source)

The #1 missed check. The destination VPC's route table must send the
reply back to the TGW.

```bash
aws ec2 describe-route-tables \
  --filters Name=vpc-id,Values=<dest-vpc-id> --output json | \
  jq '.RouteTables[].Routes[] | select(.DestinationCidrBlock | startswith("<source-cidr-prefix>"))'
```

If no route exists for the source CIDR (neither specific nor default
to the TGW), the reply goes to the IGW or is dropped.
**ROOT_CAUSE_IDENTIFIED** with `LAYER: VPC_DEFAULT_ROUTE_TGW`.

#### 2d: Default route 0.0.0.0/0 pointing at TGW

```bash
aws ec2 describe-route-tables \
  --filters Name=vpc-id,Values=<vpc-id> --output json | \
  jq '.RouteTables[].Routes[] | select(.DestinationCidrBlock=="0.0.0.0/0")'
```

If the default route points at a TransitGatewayId (not `igw-`),
internet-bound traffic is blackholed unless the VPC is in a
centralized-egress design.

### Step 3: Static route priority / overlapping CIDR

Symptom: traffic reaches the WRONG target VPC.

#### 3a: Static routes overriding propagated

```bash
aws ec2 search-transit-gateway-routes \
  --transit-gateway-route-table-id <rtb-id> \
  --filters Name=type,Values=static --output json | \
  jq '.Routes[] | select(.DestinationCidrBlock | startswith("<dest-cidr-prefix>"))'
```

If a static route exists for the same CIDR as a propagated route and
points at a DIFFERENT attachment, the static wins. Traffic goes to
the wrong attachment. **ROOT_CAUSE_IDENTIFIED** with
`LAYER: TGW_STATIC_ROUTE_PRIORITY`.

#### 3b: Overlapping CIDR

```bash
aws ec2 describe-vpcs --vpc-ids <vpc-a-id> <vpc-b-id> --output json | \
  jq '.Vpcs[] | {VpcId, CidrBlock, CidrBlockAssociationSet}'
```

If two attachments advertise overlapping CIDRs (e.g.,
`10.0.0.0/16` and `10.0.1.0/24`), the longest-prefix match wins; the
broader CIDR is shadowed for the overlapping portion.
**ROOT_CAUSE_IDENTIFIED** with `LAYER: TGW_OVERLAPPING_CIDR`. Fix:
re-CIDR one of the VPCs (no NAT-on-TGW workaround).

### Step 4: TGW peering non-transitivity

#### 4a: Peering attachment state

```bash
aws ec2 describe-transit-gateway-peering-attachments \
  --filters Name=transit-gateway-id,Values=<tgw-a-id> --output json | \
  jq '.TransitGatewayPeeringAttachments[] | {TransitGatewayPeeringAttachmentId, State, AccepterTgwInfo, RequesterTgwInfo}'
```

`pending-acceptance` requires peer acceptance; `rejected` is dead;
`failed` errored. Only `available` carries traffic.

#### 4b: Route tables on BOTH TGWs

```bash
aws ec2 search-transit-gateway-routes \
  --transit-gateway-route-table-id <local-rtb> \
  --filters Name=type,Values=propagated,static --output json | \
  jq '.Routes[] | select(.TransitGatewayAttachments[].TransitGatewayAttachmentId=="<peering-attach-id>")'
```

Repeat on the remote TGW. If either side lacks the route, traffic is
one-directional.

#### 4c: Transitivity check

If the operator expects `tgw-a` to reach `tgw-c` through `tgw-b` as
an intermediate hop, **ROOT_CAUSE_IDENTIFIED** with
`LAYER: TGW_PEERING_NON_TRANSITIVE`. TGW peering is strictly peer-to-
peer. Establish a direct peering between `tgw-a` and `tgw-c`; there
is no workaround.

### Step 5: Appliance mode

```bash
aws ec2 describe-transit-gateway-attachments \
  --transit-gateway-attachment-ids <inspection-vpc-attachment-id> --output json | \
  jq '.TransitGatewayAttachments[].Options.ApplianceModeSupport'
```

If `ApplianceModeSupport` is `disable`, cross-AZ stateful flows are
dropped. **ROOT_CAUSE_IDENTIFIED** with `LAYER: TGW_APPLIANCE_MODE`.
Fix: enable appliance mode on the inspection VPC's attachment.

### Step 6: VPN / Direct Connect routing

#### 6a: On-prem CIDR in the TGW route table

```bash
aws ec2 search-transit-gateway-routes \
  --transit-gateway-route-table-id <rtb-id> \
  --filters Name=type,Values=propagated,static --output json | \
  jq '.Routes[] | select(.DestinationCidrBlock | startswith("<onprem-cidr-prefix>"))'
```

If absent, the VPN/DX attachment is not propagating. For VPN: check
`CustomerGateway` BGP. For DX: check the DX gateway association.

#### 6b: VPN attachment's association

```bash
aws ec2 describe-transit-gateway-attachments \
  --filters Name=resource-type,Values=vpn \
  --filters Name=transit-gateway-id,Values=<tgw-id> --output json | \
  jq '.TransitGatewayAttachments[] | {TransitGatewayAttachmentId, Association, State}'
```

If the VPN attachment is associated with a different route table than
the VPC attachments use for outbound lookups, VPC outbound traffic
never finds the on-prem route.

#### 6c: DX gateway association

```bash
aws directconnect describe-direct-connect-gateways --output json
aws directconnect describe-direct-connect-gateway-associations --output json
```

If the TGW is not associated with the DX gateway, or the allowed
prefixes exclude the target CIDR, **ROOT_CAUSE_IDENTIFIED** with
`LAYER: TGW_VPN_DX_ROUTING`.

### Step 7: Multicast domain

```bash
aws ec2 describe-transit-gateway-multicast-domains \
  --transit-gateway-id <tgw-id> --output json

aws ec2 search-transit-gateway-multicast-groups \
  --transit-gateway-multicast-domain-id <domain-id> --output json | \
  jq '.MulticastGroups[] | {GroupIpAddress, NetworkInterfaceId, GroupMember}'
```

If a receiver's ENI is not in the group, it does not receive. If the
multicast domain itself does not exist, **ROOT_CAUSE_IDENTIFIED** with
`LAYER: TGW_MULTICAST_DOMAIN`.

### Step 8: DNS resolution across TGW attachments

```bash
aws ec2 describe-vpc-attribute --vpc-id <vpc-id> --attribute enableDnsSupport --output json
aws ec2 describe-vpc-attribute --vpc-id <vpc-id> --attribute enableDnsHostnames --output json
aws route53resolver list-resolver-endpoints --output json
aws route53resolver list-resolver-rules --output json
```

Both VPCs need `enableDnsSupport: true` and `enableDnsHostnames:
true`. For cross-VPC resolution, deploy Route 53 Resolver inbound
endpoints in the destination VPC and outbound endpoints in the
source VPC; create a forwarding rule. If absent,
**ROOT_CAUSE_IDENTIFIED** with `LAYER: TGW_DNS_RESOLUTION`.

### Step 8b: TGW flow logs

```bash
aws ec2 describe-flow-logs \
  --filter Name=resource-type,Values=transit-gateway \
  --filter Name=resource-id,Values=<tgw-id> --output json
```

If no flow log is configured, or the IAM role lacks
`logs:CreateLogStream` / `logs:PutLogEvents`, or the destination
CloudWatch Logs group does not exist, **ROOT_CAUSE_IDENTIFIED** with
`LAYER: TGW_FLOW_LOGS`.

### Step 8c: Cross-VPC security group references

```bash
aws ec2 describe-security-groups \
  --filters Name=vpc-id,Values=<vpc-a-id> --output json | \
  jq '.SecurityGroups[].IpPermissions[] | .UserIdGroupPairs[]?'
```

If a `UserIdGroupPairs` entry references a GroupId in a different VPC,
the reference is invalid for a TGW topology. Cross-VPC SG references
work in VPC peering (same region only), not through TGW.
**ROOT_CAUSE_IDENTIFIED** with `LAYER: TGW_SG_CROSS_VPC`. Fix:
replace the cross-VPC SG reference with the peer VPC's CIDR or a
managed prefix list.

### Step 9: UNKNOWN / INSUFFICIENT_DATA

- **INSUFFICIENT_DATA** — A specific probe requires operator input
  (the remote TGW's route table for a cross-account peering, the
  on-prem BGP status, the destination VPC's route table). List the
  missing pieces and the next probe to run once the info is
  available.
- **UNKNOWN** — All probes passed and the symptom persists. Escalate
  to AWS Support with the TGW ID, the source/destination attachment
  IDs, a Reachability Analysis output, and the observed symptom.

## Output format

```text
TARGET: <tgw-id, source-attachment, destination-attachment>
VERDICT: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
REASON: <1-2 sentences naming the failed layer and the failing probe>
LAYER: <TGW_ROUTE_TABLE_ASSOCIATION | TGW_ROUTE_TABLE_PROPAGATION |
        TGW_STATIC_ROUTE_PRIORITY | TGW_OVERLAPPING_CIDR |
        TGW_PEERING_NON_TRANSITIVE | TGW_VPN_DX_ROUTING |
        TGW_MULTICAST_DOMAIN | TGW_FLOW_LOGS |
        VPC_DEFAULT_ROUTE_TGW | TGW_ATTACHMENT_WRONG_SUBNET |
        TGW_SG_CROSS_VPC | TGW_DNS_RESOLUTION |
        TGW_APPLIANCE_MODE | TGW_BLACKHOLE_ROUTE | UNKNOWN>
EVIDENCE:
  - <observed symptom — error string or packet-flow behaviour>
  - <failing probe — command and its output that confirms the cause>
  - <passing probes — layers ruled out>
REMEDIATION:
  1. <specific action with CLI command>
  2. <verification command after the fix>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <tgw-id> in <region>. Proceed?
  (yes/no)"
```

### Worked example — Static route overrides propagated route

```text
TARGET: tgw-aaa (source: tgw-attach-vpc-a, dest: tgw-attach-vpc-b)
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: VPC-A's associated TGW route table tgw-rtb-default contains a
  static route for 10.20.0.0/16 pointing at tgw-attach-vpc-c (a legacy
  attachment from a prior migration), which overrides the propagated
  route from VPC-B's attachment. VPC-A's outbound traffic for VPC-B's
  CIDR is forwarded to VPC-C, where it is dropped (Step 3a).
LAYER: TGW_STATIC_ROUTE_PRIORITY
EVIDENCE:
  - Symptom: EC2 i-aaa in VPC-A (10.10.0.0/16) cannot ping EC2 i-bbb
    in VPC-B (10.20.0.0/16). ICMP "request timeout". i-bbb never
    sees the packet in its VPC flow logs.
  - Probe: aws ec2 search-transit-gateway-routes on tgw-rtb-default
    with type=static returns:
      10.20.0.0/16 → tgw-attach-vpc-c (static, active)
  - Probe: aws ec2 search-transit-gateway-routes with type=propagated
    returns:
      10.20.0.0/16 → tgw-attach-vpc-b (propagated, active — but
      shadowed by the static route)
  - Passing: VPC-A's route table has 10.20.0.0/16 → tgw-aaa; VPC-B's
    return route table has 10.10.0.0/16 → tgw-aaa; CIDRs do not
    overlap.
REMEDIATION:
  1. Delete the stale static route:
     aws ec2 delete-transit-gateway-route \
       --transit-gateway-route-table-id tgw-rtb-default \
       --destination-cidr-block 10.20.0.0/16
  2. Verify the propagated route becomes the active forwarding route:
     aws ec2 search-transit-gateway-routes \
       --transit-gateway-route-table-id tgw-rtb-default \
       --filters Name=state,Values=active
CONFIRM: Before deleting the route, emit and await:
  "CONFIRM: About to delete static route 10.20.0.0/16 from
   tgw-rtb-default. Proceed? (yes/no)"
```

### Worked example — Appliance mode disabled

```text
TARGET: tgw-aaa (inspection-vpc-attachment: tgw-attach-inspection)
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: The inspection VPC's attachment has ApplianceModeSupport=disable.
  Flows from us-east-1a (where the firewall ENI lives) succeed; flows
  from us-east-1b fail because the return traffic exits the TGW in
  us-east-1b, bypassing the firewall, which drops the flow as
  out-of-state (Step 5).
LAYER: TGW_APPLIANCE_MODE
EVIDENCE:
  - Symptom: cross-VPC flows succeed when the source is in
    us-east-1a; intermittently fail when the source is in
    us-east-1b. Firewall logs show "out-of-state drop".
  - Probe: aws ec2 describe-transit-gateway-attachments on
    tgw-attach-inspection returns Options.ApplianceModeSupport=disable.
  - Passing: TGW route tables contain correct routes for both VPCs;
    no static routes override; CIDRs do not overlap.
REMEDIATION:
  1. Enable appliance mode:
     aws ec2 modify-transit-gateway-attachment \
       --transit-gateway-attachment-id tgw-attach-inspection \
       --options ApplianceModeSupport=enable
  2. Verify flows from us-east-1b now succeed.
CONFIRM: Before modifying the attachment, emit and await:
  "CONFIRM: About to enable ApplianceModeSupport on
   tgw-attach-inspection. Proceed? (yes/no)"
```

## Anti-Patterns — NEVER

- NEVER declare ROOT_CAUSE_IDENTIFIED without a failing probe that
  matches the symptom. A "process of elimination" diagnosis erodes
  operator trust when the real cause is elsewhere.
- NEVER diagnose only the forward path. Routing is bidirectional. A
  one-way ping that times out is just as likely a missing return
  route in the destination VPC as a missing forward route in the TGW.
- NEVER assume "both VPCs are attached to the TGW" means traffic
  will flow. Attachment is necessary but not sufficient — association
  AND propagation are independent controls.
- NEVER assume TGW peering is transitive. Each pair of TGWs that
  needs to exchange traffic requires a direct peering attachment.
- NEVER use a cross-VPC security group reference through a TGW. Unlike
  VPC peering (same region), TGW does NOT support cross-VPC SG
  references. Use a CIDR block, a managed prefix list, or a same-VPC
  SG reference.
- NEVER point a VPC's default route `0.0.0.0/0` at the TGW unless the
  VPC is in a centralized-egress design with a dedicated egress VPC.
- NEVER expect multicast to "just work" on a TGW. Multicast requires a
  dedicated multicast domain, members are statically added by ENI, and
  IGMP is not supported.
- NEVER confuse TGW flow logs with VPC flow logs. TGW flow logs show
  the TGW's view; VPC flow logs show the VPC's view. Correlate both
  for end-to-end debugging.
- NEVER enable appliance mode on a non-inspection attachment. It adds
  an unnecessary cross-AZ hop and increases latency for all flows
  transiting that attachment.
- NEVER assume overlapping CIDRs are routable on a TGW. TGW uses
  longest-prefix match; the broader CIDR is shadowed. There is no
  NAT-on-TGW. Re-CIDR one of the VPCs.
- NEVER conclude "the TGW is broken" without checking AWS Health.
  Regional TGW degradation can mimic a route-table issue; always run
  `aws health describe-events` if multiple attachments fail
  simultaneously with no config change.
- NEVER perform state-changing operations as diagnostic probes. Every
  probe in this skill is read-only. State changes are remediations,
  gated behind CONFIRM.

## Pre-flight safety checks (run before any state-changing CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`modify-transit-gateway-attachment`,
  `delete-transit-gateway-route`, `create-transit-gateway-route`,
  `associate-transit-gateway-route-table`,
  `enable-transit-gateway-route-table-propagation`), emit and await
  operator approval.
- **Read-only first.** Every probe is read-only.
- **Deleting a static route** is reversible (re-create with
  `create-transit-gateway-route`). Verify the propagated route takes
  effect immediately after the delete.
- **Enabling appliance mode** takes effect within seconds but causes a
  brief traffic disruption on existing flows through the inspection
  attachment. Plan outside a traffic peak.
- **Creating a TGW peering** requires the peer TGW's owner to accept.
  Cross-account/cross-region peerings can take minutes to reach
  `available`.
- **Associating an attachment with a different route table**
  immediately affects outbound routing for that attachment. Verify
  the new route table has all necessary propagated routes before
  switching.
- **Bulk remediation batch limit.** Batch into groups of at most 5
  attachments, emit a single CONFIRM per batch, verify between
  batches.

## Remediation guidance (command index)

- **TGW_ROUTE_TABLE_ASSOCIATION**: `associate-transit-gateway-route-table`
- **TGW_ROUTE_TABLE_PROPAGATION**: `enable-transit-gateway-route-table-propagation`
- **TGW_STATIC_ROUTE_PRIORITY**: `delete-transit-gateway-route` (stale static)
- **TGW_OVERLAPPING_CIDR**: re-CIDR one VPC (no NAT-on-TGW)
- **TGW_PEERING_NON_TRANSITIVE**: `create-transit-gateway-peering-attachment` (direct peering)
- **TGW_VPN_DX_ROUTING**: verify BGP / DX gateway association / allowed prefixes
- **TGW_MULTICAST_DOMAIN**: `register-transit-gateway-multicast-group-members`
- **VPC_DEFAULT_ROUTE_TGW**: `create-route --transit-gateway-id` (return path)
- **TGW_APPLIANCE_MODE**: `modify-transit-gateway-attachment --options ApplianceModeSupport=enable`
- **TGW_DNS_RESOLUTION**: Route 53 Resolver inbound + outbound endpoints + forwarding rule
- **TGW_FLOW_LOGS**: `create-flow-logs --resource-type transit-gateway`
- **TGW_SG_CROSS_VPC**: replace cross-VPC SG ref with CIDR / prefix list (`authorize-security-group-ingress --ip-ranges`)

See `references/tgw-routing-reference.md` for the full command index
and `references/tgw-attachment-and-appliance-mode.md` for attachment-
type and appliance-mode detail.

## Domain

AWS CloudOps / Transit Gateway Networking, Routing Diagnostics,
Inter-VPC and Cross-Region Connectivity, Appliance-Mode Inspection,
and Peering Topology.

## AWS documentation

- **AWS Transit Gateway User Guide** — https://docs.aws.amazon.com/vpc/latest/tgw/
- **TGW route tables** — https://docs.aws.amazon.com/vpc/latest/tgw/tgw-route-tables.html
- **TGW appliance mode** — https://docs.aws.amazon.com/vpc/latest/tgw/appliance-mode.html
- **TGW peering attachments** — https://docs.aws.amazon.com/vpc/latest/tgw/tgw-peering.html
- **TGW multicast domain** — https://docs.aws.amazon.com/vpc/latest/tgw/tgw-multicast-overview.html
- **TGW flow logs** — https://docs.aws.amazon.com/vpc/latest/tgw/tgw-flow-logs.html
- **TGW VPN attachments** — https://docs.aws.amazon.com/vpc/latest/tgw/tgw-vpn-attachments.html
- **TGW Direct Connect gateway associations** — https://docs.aws.amazon.com/directconnect/latest/UserGuide/direct-connect-gateways-intro.html
- **Route 53 Resolver** — https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver.html
- **AWS Health** — https://docs.aws.amazon.com/health/latest/ug/
