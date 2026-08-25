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

The four Philosophy behaviours moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
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

The pre-flight gather commands moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).

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

All 11 operational gotchas moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).

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

Probe CLI moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).

If the source attachment has NO association, **ROOT_CAUSE_IDENTIFIED**
with `LAYER: TGW_ROUTE_TABLE_ASSOCIATION`. The TGW has no lookup
table for its outbound traffic.

#### 2b: Destination CIDR in the associated route table

Probe CLI moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).

If the destination CIDR is NOT present, the destination attachment
was not propagated. **ROOT_CAUSE_IDENTIFIED** with
`LAYER: TGW_ROUTE_TABLE_PROPAGATION`.

#### 2c: Return path (destination → source)

The #1 missed check. The destination VPC's route table must send the
reply back to the TGW.

Probe CLI moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).

If no route exists for the source CIDR (neither specific nor default
to the TGW), the reply goes to the IGW or is dropped.
**ROOT_CAUSE_IDENTIFIED** with `LAYER: VPC_DEFAULT_ROUTE_TGW`.

#### 2d: Default route 0.0.0.0/0 pointing at TGW

Probe CLI moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).

If the default route points at a TransitGatewayId (not `igw-`),
internet-bound traffic is blackholed unless the VPC is in a
centralized-egress design.

### Step 3: Static route priority / overlapping CIDR

Symptom: traffic reaches the WRONG target VPC.

#### 3a: Static routes overriding propagated

Probe CLI moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).

If a static route exists for the same CIDR as a propagated route and
points at a DIFFERENT attachment, the static wins. Traffic goes to
the wrong attachment. **ROOT_CAUSE_IDENTIFIED** with
`LAYER: TGW_STATIC_ROUTE_PRIORITY`.

#### 3b: Overlapping CIDR

Probe CLI moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).

If two attachments advertise overlapping CIDRs (e.g.,
`10.0.0.0/16` and `10.0.1.0/24`), the longest-prefix match wins; the
broader CIDR is shadowed for the overlapping portion.
**ROOT_CAUSE_IDENTIFIED** with `LAYER: TGW_OVERLAPPING_CIDR`. Fix:
re-CIDR one of the VPCs (no NAT-on-TGW workaround).

### Step 4: TGW peering non-transitivity

#### 4a: Peering attachment state

Probe CLI moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).

`pending-acceptance` requires peer acceptance; `rejected` is dead;
`failed` errored. Only `available` carries traffic.

#### 4b: Route tables on BOTH TGWs

Probe CLI moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).

Repeat on the remote TGW. If either side lacks the route, traffic is
one-directional.

#### 4c: Transitivity check

If the operator expects `tgw-a` to reach `tgw-c` through `tgw-b` as
an intermediate hop, **ROOT_CAUSE_IDENTIFIED** with
`LAYER: TGW_PEERING_NON_TRANSITIVE`. TGW peering is strictly peer-to-
peer. Establish a direct peering between `tgw-a` and `tgw-c`; there
is no workaround.

### Step 5: Appliance mode

Probe CLI moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).

If `ApplianceModeSupport` is `disable`, cross-AZ stateful flows are
dropped. **ROOT_CAUSE_IDENTIFIED** with `LAYER: TGW_APPLIANCE_MODE`.
Fix: enable appliance mode on the inspection VPC's attachment.

### Step 6: VPN / Direct Connect routing

#### 6a: On-prem CIDR in the TGW route table

Probe CLI moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).

If absent, the VPN/DX attachment is not propagating. For VPN: check
`CustomerGateway` BGP. For DX: check the DX gateway association.

#### 6b: VPN attachment's association

Probe CLI moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).

If the VPN attachment is associated with a different route table than
the VPC attachments use for outbound lookups, VPC outbound traffic
never finds the on-prem route.

#### 6c: DX gateway association

Probe CLI moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).

If the TGW is not associated with the DX gateway, or the allowed
prefixes exclude the target CIDR, **ROOT_CAUSE_IDENTIFIED** with
`LAYER: TGW_VPN_DX_ROUTING`.

### Step 7: Multicast domain

Probe CLI moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).

If a receiver's ENI is not in the group, it does not receive. If the
multicast domain itself does not exist, **ROOT_CAUSE_IDENTIFIED** with
`LAYER: TGW_MULTICAST_DOMAIN`.

### Step 8: DNS resolution across TGW attachments

Probe CLI moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).

Both VPCs need `enableDnsSupport: true` and `enableDnsHostnames:
true`. For cross-VPC resolution, deploy Route 53 Resolver inbound
endpoints in the destination VPC and outbound endpoints in the
source VPC; create a forwarding rule. If absent,
**ROOT_CAUSE_IDENTIFIED** with `LAYER: TGW_DNS_RESOLUTION`.

### Step 8b: TGW flow logs

Probe CLI moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).

If no flow log is configured, or the IAM role lacks
`logs:CreateLogStream` / `logs:PutLogEvents`, or the destination
CloudWatch Logs group does not exist, **ROOT_CAUSE_IDENTIFIED** with
`LAYER: TGW_FLOW_LOGS`.

### Step 8c: Cross-VPC security group references

Probe CLI moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).

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

Full appliance-mode-disabled worked example moved verbatim to [references/worked-examples.md](references/worked-examples.md).

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

The 12-entry remediation command index moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).

See `references/tgw-routing-reference.md` for the full command index
and `references/tgw-attachment-and-appliance-mode.md` for attachment-
type and appliance-mode detail.

## References (load on demand)

- [references/diagnostic-commands.md](references/diagnostic-commands.md) — pre-flight gather commands, every per-step probe CLI (Steps 2-8c), and the remediation command index
- [references/advanced-patterns.md](references/advanced-patterns.md) — Philosophy four behaviours and Step 0 operational gotchas
- [references/worked-examples.md](references/worked-examples.md) — Appliance-mode-disabled worked example
- [references/tgw-routing-reference.md](references/tgw-routing-reference.md) — full TGW routing command index
- [references/tgw-attachment-and-appliance-mode.md](references/tgw-attachment-and-appliance-mode.md) — attachment types and appliance-mode detail

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
