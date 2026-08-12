---
name: transit-gateway-deployer
description: >-
  Provisions production-grade AWS Transit Gateway topologies with
  secure defaults: TGW creation (Amazon ASN, DNS support, multicast),
  VPC attachments with subnet selections, TGW route tables
  (association + propagation), inter-region peering connections,
  Connect attachments (GRE tunnels for SD-WAN), TGW Network Manager
  (global network visualization), cross-account sharing via RAM, and
  AWS Cloud WAN integration. Emits READY_TO_DEPLOY with an ordered
  CLI plan or PREREQUISITES_MISSING with the specific gap. Use when
  building hub-and-spoke or mesh topologies, configuring inter-region
  TGW peering, deploying Connect attachments for SD-WAN appliances,
  sharing a TGW across accounts via RAM, or migrating to Cloud WAN.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). No AWS CLI required for offline plan generation.
  Live deployment uses aws ec2 create-transit-gateway,
  create-transit-gateway-vpc-attachment, create-transit-gateway-route-table,
  associate-transit-gateway-route-table, enable-transit-gateway-route-table-propagation,
  create-transit-gateway-peering-attachment,
  create-transit-gateway-connect, create-transit-gateway-connect-peer,
  create-transit-gateway-multicast-domain, aws ram create-resource-share,
  aws networkmanager create-global-network, create-core-network
  (AWS CLI v2, SSO or key-based credentials).
keywords:
  - Transit Gateway
  - TGW deploy
  - TGW creation
  - Amazon ASN
  - VPC attachment
  - subnet selection
  - TGW route table
  - route association
  - route propagation
  - peering connection
  - inter-region peering
  - TGW Connect
  - GRE tunnel
  - SD-WAN
  - Connect attachment
  - Connect peer
  - Network Manager
  - global network
  - RAM share
  - cross-account TGW
  - TGW multicast
  - multicast domain
  - AWS Cloud WAN
  - core network
tags: [transit-gateway, tgw, networking, deploy, hub-and-spoke, peering, connect-attachment, ram-share, cloud-wan, multicast]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: Networking
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  when_to_use: >-
    Provisioning a new Transit Gateway for hub-and-spoke or mesh
    topology, configuring VPC attachments with subnet selections,
    building TGW route tables with association and propagation,
    deploying inter-region peering connections between regional TGWs,
    deploying Connect attachments with GRE tunnels for SD-WAN
    appliances, sharing a TGW across AWS accounts via RAM, configuring
    multicast domains, integrating with AWS Cloud WAN, or migrating
    from VPC peering to TGW.
  activation_triggers:
    - "create Transit Gateway"
    - "deploy Transit Gateway"
    - "TGW hub and spoke"
    - "TGW VPC attachment"
    - "TGW route table"
    - "TGW route propagation"
    - "TGW peering connection"
    - "inter-region TGW peering"
    - "TGW Connect attachment"
    - "TGW Connect GRE"
    - "SD-WAN Connect attachment"
    - "TGW Network Manager"
    - "global network TGW"
    - "RAM share TGW"
    - "cross-account Transit Gateway"
    - "TGW multicast domain"
    - "AWS Cloud WAN"
    - "core network TGW"
    - "TGW ASN"
    - "TGW DNS support"
  invocation_schema: >-
    Input (one of): (a) a deployment spec — TGW options (ASN, DNS,
    multicast, AutoAcceptSharedAttachments), VPC attachments with
    subnet IDs, route table topology with associations and
    propagations, optional peering connections, optional Connect
    attachments with BGP/GRE peer config, optional RAM share
    principals, optional Cloud WAN integration; (b) a partial spec
    for interactive refinement; (c) an existing TGW ID for review
    against the well-architected checklist. Output: TGW_SPEC,
    VERDICT, ARCHITECTURE, CHECKLIST[], FINDINGS[], DEPLOY_COMMANDS
    — where VERDICT is READY_TO_DEPLOY or PREREQUISITES_MISSING.
---

# Transit Gateway Deployer

## What this skill does

Provisions production-grade AWS Transit Gateway topologies with
secure defaults: TGW creation (Amazon ASN, DNS support, multicast,
AutoAcceptSharedAttachments), VPC attachments with subnet selections,
TGW route tables (association + propagation model), inter-region
peering connections, Connect attachments with GRE tunnels for SD-WAN
appliances, TGW Network Manager for global topology visualization,
cross-account sharing via AWS RAM, multicast domains, and AWS Cloud
WAN integration. Emits a deployment plan with a READY_TO_DEPLOY
checklist.

## Mindset

**One-line takeaway:** a Transit Gateway is a **regional,
cloud-native router** that scales VPC-to-VPC, VPC-to-VPN, and
VPC-to-on-prem connectivity without the pairwise explosion of VPC
peering. One TGW per region (typical), attachments plug VPCs and
remote networks in, and route tables (with association and
propagation) express the routing policy.

Three facts make TGW provisioning different from "a big VPC peering
mesh":

- **Route tables in TGW use BOTH association AND propagation — they
  are not the same.** Association = which route table an attachment
  LOOKS UP its routes in (one default + extras). Propagation = which
  route tables an attachment INJECTS its routes INTO (many). An
  attachment can be associated with one route table and propagate to
  many. Misunderstanding this is the #1 cause of "I can't route
  between VPCs" outages.

- **Cross-account attachments require TWO-SIDED consent.** The TGW
  owner account shares the TGW via RAM; the consumer account creates
  the VPC attachment. With `AutoAcceptSharedAttachments=false`
  (recommended for production), the TGW owner must also `accept` the
  attachment after the consumer creates it. Skipping the accept step
  leaves the attachment in `pendingAcceptance` forever.

- **Connect attachments carry the BGP/EIGRP control plane of your
  SD-WAN.** A TGW Connect attachment rides on top of a VPC or Direct
  Connect gateway attachment and establishes GRE tunnels to a
  Connect peer (your SD-WAN controller or branch appliance). Routes
  the peer advertises via BGP land in the TGW route table as
  propagated routes. Connect is NOT a VPN replacement — it assumes
  the underlying transport is already encrypted.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **Quick reference** | Verdict thresholds + checklist matrix + TGW limits | Before any operation |
| **Pre-flight** | TGW/VPC/subnet gate, RAM, peering, Connect, BGP | Before executing any CLI |
| **Process** | Per-step: TGW create, VPC attach, route tables, peering, Connect, multicast, Network Manager, RAM, Cloud WAN | When choosing each step |
| **Common patterns** | Single-region hub-spoke / inter-region peering / SD-WAN Connect / Cloud WAN migration | Boilerplate lookup |
| **STRICT output contract** | Required TGW/VERDICT/PRE_CHECKS/STEPS/POST_VERIFY block | Formatting the response |
| **NEVER (top 5)** | Hard rules preventing common insecure patterns | Review before deploy |
| **Expert heuristic** | When to use TGW route tables vs. security group-based segmentation | Choosing segmentation model |

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `PREREQUISITES_MISSING` | Any pre-check failed (VPC subnet not in `available` state, subnet AZ scope mismatch across attachments, TGW ASN conflict, route table association/propagation conflict, peering attachment not in `available` state in peer region, RAM share `PENDING`/`REJECTED`, Connect peer BGP ASN mismatch, multicast domain member in different TGW, Direct Connect gateway already associated with another TGW, TGW `deleting`/`failed`) | List failures, do NOT execute |
| `READY_TO_DEPLOY` | All pre-checks passed; awaiting CONFIRM gate | Emit exact CLI sequence with full topology config, wait for operator yes |

**Deployment checklist (every dimension must pass):**

| Dimension | Requirement | Step |
|---|---|---|
| TGW ASN | 64512-65535 (private) or specific 4-byte range; unique per TGW peering pair | Step 1 |
| DNS support | `enableDnsSupport` true (recommended) — allows VPC-resident Route 53 Resolver to be reached via TGW | Step 1 |
| DNS propagation | `enableDnsPropagation` true (recommended) — DNS hostnames propagate across attachments | Step 1 |
| Multicast | Disabled by default; enable only with explicit multicast domain plan | Step 1 |
| AutoAcceptSharedAttachments | `false` for production (recommended) — owner accepts cross-account attachments explicitly | Step 1 |
| Default route table association | `true` (recommended for simple topology) or `false` (multi-table segmentation) | Step 1 |
| Default route table propagation | `true` (recommended for simple topology) or `false` (multi-table segmentation) | Step 1 |
| VPC attachment subnets | One subnet per AZ; subnets must be `available`; minimum /28 | Step 2 |
| VPC attachment AZ scope | Same AZs across all attachments in a topology for predictable routing | Step 2 |
| Appliance mode | Disabled by default; enable for firewalls/NVA in-line inspection | Step 2 |
| Route tables | One per segmentation tier (prod/non-prod/segment-X) | Step 3 |
| Associations | Each attachment associated with one route table | Step 3 |
| Propagations | Each attachment propagates to one or more route tables | Step 3 |
| Static routes | Added explicitly with `create-transit-gateway-route` (blackhole optional) | Step 3 |
| Peering | Inter-region or intra-region; peer region TGW exists and `available` | Step 4 |
| Connect attachment | Backed by a VPC or Direct Connect gateway attachment | Step 5 |
| Connect peer | BGP ASN and peer GRE address; inside CIDR /29 minimum | Step 5 |
| Multicast domain | Members in same TGW; IGMP snooping optional | Step 6 |
| Network Manager | Global network contains TGW for topology view | Step 7 |
| RAM share | Principal accepted in consumer account before attachment creation | Step 8 |
| Cloud WAN | Core network attached to TGW via `create-attachment` | Step 9 |

**Transit Gateway limits (2026):**

- TGWs per region per account: 5 (soft limit; raise via support).
- VPC attachments per TGW: 50 (soft; raise to 500). Route tables per TGW: 50 (raise to 100).
- Routes per route table: 10000. Peering attachments per TGW: 50.
- Connect attachments per TGW: 20. Connect peers per Connect attachment: 4 (hard).
- Multicast domains per TGW: 20. Multicast group members per domain: 1000.
- Supported ASNs: 64512-65535 (private 2-byte), 4200000000-4294967294 (private 4-byte).
- Throughput: up to 50 Gbps per attachment (burst 100 Gbps); 500 Gbps aggregate; inter-region peering up to 50 Gbps.

## Pre-flight: deployment specification gate (run before architecture output)

Before producing the deployment plan, validate the input specification.
Several requirements **block deployment** — proceeding with an invalid
spec produces a non-functional or insecure TGW topology.

**Live-account pre-flight checks (skip if doing offline architecture plan):**

1. Verify IAM permissions: `ec2:CreateTransitGateway*`, `AssociateTransitGatewayRouteTable`,
   `EnableTransitGatewayRouteTablePropagation`, `ec2:ModifyTransitGateway`,
   plus `ram:CreateResourceShare` for cross-account.
2. Verify each VPC subnet is `available` and AZ scope is consistent:
   `aws ec2 describe-subnets --subnet-ids <list>` returns `State=available`.
3. Verify no conflicting TGW ASN: each TGW in a peering pair must have
   a unique ASN. `aws ec2 describe-transit-gateways` returns ASNs.
4. For RAM shares: verify `aws ram get-resource-shares` shows the
   share `ACTIVE` and accepted by the consumer account.
5. For peering: verify the peer-region TGW exists in the peer account
   via `describe-transit-gateways --region <peer-region>`.
6. For Connect: verify the underlying VPC or Direct Connect gateway
   attachment is `available` in the same TGW.
7. For multicast: verify TGW `Options.MulticastSupport=enable`
   (cannot be added after creation).

| Attribute | Value | Effect on plan |
|---|---|---|
| AutoAcceptSharedAttachments | `false` | Owner must explicitly accept each cross-account attachment after creation. Recommended for prod. |
| DefaultRouteTableAssociation | `true` | New attachments auto-associate to the default route table. Simpler but less isolation. |
| DefaultRouteTableAssociation | `false` | Owner must explicitly associate each attachment. Required for multi-table segmentation. |
| ApplianceModeSupport | `enable` | Hairpin traffic through an NVA in a VPC attachment. Required for centralized firewall inspection. |
| MulticastSupport | `enable` | Enables multicast domains. Cannot be toggled after creation. |

**If the deployment spec is incomplete** (missing VPC IDs, subnet
lists, or TGW topology), output:

```text
TGW_SPEC: <name-or-unknown>
VERDICT: PREREQUISITES_MISSING
REASON: Deployment specification is missing required fields (<list>).
Cannot produce a TGW plan without <field> — the resulting deployment
would be non-functional or insecure.
REQUIRED:
  - tgw_asn (64512-65535 or 4-byte private range)
  - vpc_attachments (list of {vpc_id, subnet_ids})
  - route_table_topology (associations + propagations per attachment)
  - ram_share_principals (cross-account consumer account IDs, optional)
  - peering_peers / connect_attachments (optional lists)
```

## Process — Architecture planning (apply in order, produce deployment plan)

### Step 0: Expert knowledge — non-obvious TGW behaviors that change the plan

- **Association and propagation are DIFFERENT operations.** An
  attachment is **associated** with one route table (for its own
  lookups) and **propagates** to zero or many route tables (injecting
  its routes). Forgetting to set the propagation leaves the
  attachment's routes invisible to other attachments' route tables,
  even though the VPC is attached.

- **Default route table association and propagation are set at TGW
  creation time.** If both `true`, new attachments auto-associate
  and auto-propagate to the default route table. If either `false`,
  manage explicitly. For multi-tier segmentation, set both to
  `false`.

- **Cross-account attachments require the consumer account to create
  the VPC attachment, not the TGW owner.** The owner shares the TGW
  via RAM; the consumer calls `create-transit-gateway-vpc-attachment`
  with the shared TGW ID. With `AutoAcceptSharedAttachments=false`,
  the owner then calls `accept-transit-gateway-vpc-attachment`.
  Missing either side leaves the attachment in `pendingAcceptance`.

- **VPC attachment subnets must be one-per-AZ, and the AZ set should
  be consistent across attachments.** Each attachment uses one
  subnet per AZ (TGW places an ENI in each). If attachment A uses
  us-east-1a/b/c and B uses us-east-1a/b/d, traffic between c and d
  crosses AZs via the TGW, incurring cross-AZ charges.

- **Peering attachments do NOT auto-accept.** The peer TGW's owner
  must call `accept-transit-gateway-peering-attachment` in the peer
  region. The peering stays in `pendingAcceptance` until accepted.
  Intra-region peering between TGWs in the same account auto-accepts.

- **Connect attachments ride on top of an existing transport
  attachment.** A Connect attachment requires a backing VPC or
  Direct Connect gateway attachment. The Connect peer (your SD-WAN
  appliance) terminates the GRE tunnel and establishes BGP. Connect
  does NOT encrypt — assumes underlying transport already does.

- **Multicast cannot be enabled after TGW creation.** Set
  `Options.MulticastSupport=enable` at `create-transit-gateway`
  time. Disabling later is destructive (requires TGW recreation).

- **Route table propagation is one-way.** If A propagates to B, B
  sees A's routes. B does NOT automatically propagate back to A —
  set B's propagation explicitly. Most common cause of asymmetric
  routing in TGW topologies.

### Step 1: TGW creation — ASN, DNS, multicast, defaults

```bash
aws ec2 create-transit-gateway \
  --description "prod-tgw-us-east-1" \
  --options AmazonSideAsn=64512,AutoAcceptSharedAttachments=disable,DefaultRouteTableAssociation=enable,DefaultRouteTablePropagation=enable,VpnEcmpSupport=enable,DnsSupport=enable,MulticastSupport=disable \
  --tag-specifications "ResourceType=transit-gateway,Tags=[{Key=Name,Value=prod-tgw-us-east-1}]"
```

| Option | Recommended | Effect |
|---|---|---|
| `AmazonSideAsn` | 64512-65535 | Unique per peering pair. Document the ASN allocation across TGWs. |
| `AutoAcceptSharedAttachments` | `disable` (prod) | Owner accepts cross-account attachments explicitly. |
| `DefaultRouteTableAssociation` / `Propagation` | `enable` (simple), `disable` (segmented) | Whether new attachments auto-associate / auto-propagate. |
| `VpnEcmpSupport` | `enable` | Enables ECMP across multiple VPN tunnels for higher throughput. |
| `DnsSupport` | `enable` | Allows Route 53 Resolver to be reachable across attachments. |
| `MulticastSupport` | `disable` (default) | Enable only with explicit multicast use case. Cannot be toggled later. |
| `TransitGatewayCidrBlocks` | (optional) | /24-/29 CIDRs the TGW advertises. Required for private NAT use cases. |

### Step 2: VPC attachments — subnets, AZ scope, appliance mode

```bash
aws ec2 create-transit-gateway-vpc-attachment \
  --transit-gateway-id tgw-0abc123 \
  --vpc-id vpc-0abc123 \
  --subnet-ids subnet-0a1 subnet-0b1 subnet-0c1 \
  --options ApplianceModeSupport=disable,DnsSupport=enable,Ipv6Support=disable \
  --tag-specifications "ResourceType=transit-gateway-attachment,Tags=[{Key=Name,Value=prod-vpc-app1-tgw}]"
```

| Subnet selection rule | Effect |
|---|---|
| One subnet per AZ | TGW places an ENI in each. Avoid multiple subnets per AZ. |
| AZ set consistent across attachments | Avoids cross-AZ traffic within TGW (cross-AZ charges apply). |
| Minimum /28 subnet | TGW ENI needs 6+ IPs per subnet. |
| Appliance mode `enable` for NVAs | Hairpins traffic through a firewall/NVA in a VPC attachment. Required for centralized inspection. |

**Appliance mode deep-dive:** when enabled, the TGW preserves the
source AZ for return traffic, allowing the NVA to handle asymmetric
flows. Without appliance mode, return packets may exit a different
AZ's ENI, breaking stateful firewalls.

### Step 3: Route tables — associations and propagations

```bash
# Create a non-default route table for "prod" segmentation tier
aws ec2 create-transit-gateway-route-table --transit-gateway-id tgw-0abc123 \
  --tag-specifications "ResourceType=transit-gateway-route-table,Tags=[{Key=Name,Value=prod-rtb}]"

# Associate a VPC attachment with a route table (one association per attachment)
aws ec2 associate-transit-gateway-route-table --transit-gateway-route-table-id tgw-rtb-0prod \
  --transit-gateway-attachment-id tgw-attach-0app1

# Propagate an attachment's routes INTO a route table (many propagations allowed)
aws ec2 enable-transit-gateway-route-table-propagation --transit-gateway-route-table-id tgw-rtb-0prod \
  --transit-gateway-attachment-id tgw-attach-0app1

# Add a static route (e.g., default route to a firewall NVA attachment)
aws ec2 create-transit-gateway-route --transit-gateway-route-table-id tgw-rtb-0prod \
  --destination-cidr-block 0.0.0.0/0 --transit-gateway-attachment-id tgw-attach-0firewall --blackhole false
```

| Operation | CLI | Effect |
|---|---|---|
| Association | `associate-transit-gateway-route-table` | Attachment uses this route table for its own lookups. One per attachment (default + extras). |
| Propagation | `enable-transit-gateway-route-table-propagation` | Attachment's routes injected INTO the route table. Many per attachment. |
| Static route | `create-transit-gateway-route` | Explicit CIDR → attachment mapping. Use for default routes, blackholes, summary routes. |
| Blackhole | `create-transit-gateway-route --blackhole` | Drops traffic to the CIDR. Use for quarantine, segmentation boundaries. |

**Anti-pattern:** NEVER assume association == propagation. An
attachment associated with route table A but NOT propagating to A
will have its own lookups but its routes will NOT appear in A. Set
both operations explicitly for multi-table topologies.

### Step 4: Peering connections — inter-region and intra-region

```bash
# Request peering (in source TGW owner account, source region)
aws ec2 create-transit-gateway-peering-attachment --transit-gateway-id tgw-0source \
  --peer-transit-gateway-id tgw-0peer --peer-region eu-west-1 --peer-account-id 111111111111 \
  --tag-specifications "ResourceType=transit-gateway-peering-attachment,Tags=[{Key=Name,Value=us-east-1-to-eu-west-1}]"

# Accept peering (in peer TGW owner account, peer region)
aws ec2 accept-transit-gateway-peering-attachment --transit-gateway-peering-attachment-id tgw-attach-0peer --region eu-west-1
```

| Peering type | Acceptance model | Bandwidth |
|---|---|---|
| Intra-region, same owner | Auto-accepts (owner matches) | Up to 50 Gbps |
| Intra-region, cross-account | Manual accept required | Up to 50 Gbps |
| Inter-region (any account) | Manual accept in peer region + RAM visibility | Up to 50 Gbps, AWS backbone transit |

Peering attachments appear in BOTH TGWs. Each TGW must add the
peering's routes to its route tables (either via propagation or
static routes). Forgetting the reverse-direction propagation is the
most common cause of asymmetric routing in inter-region topologies.

### Step 5: Connect attachments — GRE tunnels for SD-WAN

```bash
# 1. Create the Connect attachment (requires existing transport attachment)
aws ec2 create-transit-gateway-connect --transport-transit-gateway-attachment-id tgw-attach-0transport \
  --options Protocol=gre --tag-specifications "ResourceType=transit-gateway-connect,Tags=[{Key=Name,Value=sdwan-connect}]"

# 2. Create the Connect peer (your SD-WAN appliance endpoint)
aws ec2 create-transit-gateway-connect-peer --transit-gateway-attachment-id tgw-attach-0connect \
  --peer-address 10.0.1.10 --bgp-options PeerAsn=65000 --inside-cidr-cidrs 169.254.0.0/29 \
  --tag-specifications "ResourceType=transit-gateway-connect-peer,Tags=[{Key=Name,Value=sdwan-peer-1}]"
```

| Field | Range | Notes |
|---|---|---|
| Transport attachment | VPC or Direct Connect gateway | Must be `available` in the same TGW. |
| Protocol | `gre` (only GRE supported) | Encapsulates the SD-WAN overlay. |
| PeerAddress | Private IP of SD-WAN appliance | Reachable via the transport attachment. |
| PeerAsn | 64512-65535 (or 4-byte private) | Must differ from TGW's AmazonSideAsn. |
| InsideCidr | /29 minimum | Used for BGP peering. 169.254.x.y range typical. |

**BGP routes** advertised by the Connect peer land in the Connect
attachment's route table as propagated routes. The TGW installs
them as routes to the Connect attachment, allowing VPCs to reach
on-prem networks behind the SD-WAN.

**Anti-pattern:** NEVER use Connect as a VPN replacement. Connect
does NOT encrypt — it tunnels GRE over an existing transport. For
encrypted internet-based transport, use a Site-to-Site VPN
attachment as the transport for the Connect attachment.

### Step 6: Multicast domains — optional multicast routing

```bash
# TGW must be created with MulticastSupport=enable
aws ec2 create-transit-gateway-multicast-domain \
  --transit-gateway-id tgw-0abc123 \
  --options Igmpv2Support=enable,StaticSourcesSupport=enable \
  --tag-specifications "ResourceType=transit-gateway-multicast-domain,Tags=[{Key=Name,Value=video-multicast}]"

# Add group members (VPC attachments)
aws ec2 associate-transit-gateway-multicast-domain \
  --transit-gateway-multicast-domain-id tgw-mc-0abc \
  --transit-gateway-attachment-id tgw-attach-0app1 \
  --subnet-ids subnet-0a1
```

Multicast domains enable one-to-many streaming within a TGW (video
broadcast, financial market data, gaming backplanes). All members
must be in the same TGW. IGMPv2 support optional; static sources
optional.

### Step 7: TGW Network Manager — global topology visualization

```bash
# 1. Create a global network
aws networkmanager create-global-network \
  --description "corp-global-network" \
  --tags Key=Name,Value=corp-global-network

# 2. Register the TGW with the global network
aws networkmanager register-transit-gateway \
  --global-network-id global-network-0abc \
  --transit-gateway-arn arn:aws:ec2:us-east-1:111111111111:transit-gateway/tgw-0abc123
```

Network Manager visualizes the global topology across all registered
TGWs (and their attachments, peers, and Connect peers) in a single
console view. Requires registering each TGW with the global network.
Cross-account TGWs require the consumer account to register as well
(via RAM share of the global network).

### Step 8: Cross-account sharing via AWS RAM

```bash
# Owner: share the TGW with consumer account 222222222222
aws ram create-resource-share --name prod-tgw-share \
  --resource-arns arn:aws:ec2:us-east-1:111111111111:transit-gateway/tgw-0abc123 \
  --principals 222222222222

# Consumer: accept the share, then create the VPC attachment
aws ram accept-resource-share-invitation --resource-share-invitation-arn <invitation-arn>
aws ec2 create-transit-gateway-vpc-attachment --transit-gateway-id tgw-0abc123 \
  --vpc-id vpc-0consumer-vpc --subnet-ids subnet-0c1 subnet-0c2 subnet-0c3

# Owner: accept the consumer's attachment (when AutoAcceptSharedAttachments=disable)
aws ec2 accept-transit-gateway-vpc-attachment --transit-gateway-vpc-attachment-id tgw-attach-0consumer
```

| Step | Account | Action |
|---|---|---|
| Share TGW | Owner | `ram create-resource-share` |
| Accept share | Consumer | `ram accept-resource-share-invitation` |
| Create VPC attachment | Consumer | `ec2 create-transit-gateway-vpc-attachment` |
| Accept VPC attachment (if `AutoAcceptSharedAttachments=disable`) | Owner | `ec2 accept-transit-gateway-vpc-attachment` |

### Step 9: AWS Cloud WAN integration (2024+)

```bash
# 1. Create a global network + core network in one step (Cloud WAN)
aws networkmanager create-core-network --global-network-id global-network-0abc \
  --description "corp-core-network" --tags Key=Name,Value=corp-core-network

# 2. Attach an existing TGW to the core network
aws networkmanager create-attachment --core-network-id core-network-0abc \
  --attachment-type TRANSIT_GATEWAY --edge-location us-east-1 \
  --resource-arn arn:aws:ec2:us-east-1:111111111111:transit-gateway/tgw-0abc123
```

Cloud WAN provides a policy-driven global network abstraction on top
of TGWs. The core network policy defines segments (e.g., prod,
non-prod, shared-services) and routing rules; Cloud WAN translates
the policy into TGW route tables and propagations. Use Cloud WAN
when managing more than ~5 TGWs globally. Existing TGWs can be
attached non-disruptively; cutover happens by re-associating
attachments from the original route tables to the Cloud WAN-managed
ones.

## Common patterns

- **Single-region hub-and-spoke.** One TGW; three VPC attachments
  (shared, app1, app2). Single default route table with
  auto-association and auto-propagation. All VPCs route to each
  other. Use for simple topologies (under 5 VPCs, no segmentation).

- **Segmented multi-tier (prod/non-prod/shared).** Three route
  tables: `prod-rtb`, `nonprod-rtb`, `shared-rtb`. Each attachment
  associated with its tier's route table. Shared propagates to both
  prod and non-prod; prod and non-prod do NOT propagate to each
  other (isolation). Default route table is the "reject-all" sink.

- **Inter-region peering for DR.** TGW in us-east-1 peers with TGW
  in us-west-2. VPC routes propagate to both TGWs. Single AWS
  backbone transit path. Use for active-passive DR topologies.

- **Centralized egress via NVA (appliance mode).** All VPCs route
  0.0.0.0/0 to a firewall VPC attachment with appliance mode
  enabled. The firewall inspects and forwards to NAT Gateway or
  Direct Connect.

- **SD-WAN Connect for hybrid.** A Connect attachment rides on a
  VPC attachment; Connect peer is a Cisco/Fortinet/Velocloud SD-WAN
  controller. BGP routes for on-prem branches land in the TGW route
  table as propagated routes.

- **Cloud WAN migration.** Existing multi-region TGW topology
  attached to a Cloud WAN core network. Policy defines three
  segments (prod, non-prod, shared). Cloud WAN creates managed route
  tables; cutover by re-associating attachments.

## Output format — MANDATORY literal labels

Every response MUST begin with the block below — no preamble, no
conversational opening. The labels are **case-sensitive all-caps
keywords** — write them EXACTLY as shown. Do NOT write a preamble.
Start with `TGW:` and stop after `NOTES:`.

```text
TGW: <tgw-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
TARGET: <tgw-name> (tgw-id: <id> for updates)
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
CHECKLIST:
  TGW_CONFIG:
    ASN: <64512-65535>
    DNS support: <enabled|disabled>
    Multicast: <enabled|disabled>
    AutoAcceptSharedAttachments: <enabled|disabled>
  VPC_ATTACHMENTS:
    - Name: <name> | VPC: <vpc-id> | Subnets: <subnet-id list> | AZs: <az list> | Appliance mode: <enabled|disabled>
  ROUTE_TABLES:
    - Name: <rtb-name> | Associations: <attachment-name list> | Propagations: <attachment-name list>
  ROUTE_ENTRIES:
    - Route table: <rtb-name> | Destination: <cidr> | Target: <attachment-name|blackhole>
  RAM_SHARE: <count> principals (auto-accept <enabled|disabled>)
  NETWORK_MANAGER: <registered|not registered> global-network <id>
  CLOUD_WAN: <attached|not attached> core-network <id>
STEPS:
  1. CONFIRM: About to <operation> TGW <name> in account <account> region <region>. This will <consequence>. Estimated monthly cost: <$X>. Proceed? (yes/no)
  2. <exact CLI command — no placeholders>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
NOTES: <segmentation model, peering direction, cost posture>
```

**Status marker semantics:**
- `[PASS]` — check passed.
- `[FAIL]` — check failed; cite the reason.

**PREREQUISITES_MISSING verdict:** if any pre-check fails, verdict
is `PREREQUISITES_MISSING` with each gap listed. Do NOT also emit
`READY_TO_DEPLOY`.

## STRICT output contract

### Required output structure

Every response MUST begin with the block from "Output format" —
no preamble, no conversational opening. The `TGW:` and `VERDICT:`
lines are always the first two lines.

### FORBIDDEN output patterns

- **NEVER start with "Let me analyze…" or "I'll create…"** — the
  `TGW:` line is always the FIRST line. No conversational preamble.
- **NEVER use lowercase verdict values** — emit `READY_TO_DEPLOY`
  or `PREREQUISITES_MISSING` (not `ready`, `prerequisites`).
- **NEVER omit PRE_CHECKS** — every pre-check run must appear with
  `[PASS]` or `[FAIL]` and a specific reason for each failure. An
  empty PRE_CHECKS block is non-compliant.
- **NEVER conflate route table association with propagation** — emit
  both as separate ROUTE_TABLES entries. Association = which route
  table an attachment LOOKS UP routes in; propagation = which route
  tables an attachment INJECTS its routes into.
- **NEVER emit a plan with placeholder values** (e.g., `<tgw-id>`,
  `<vpc-id>`) in a READY_TO_DEPLOY plan — every field must be
  populated with actual values from the input.
- **NEVER omit the CONFIRM gate** as the first STEPS entry for any
  state-changing operation.
- **NEVER deploy cross-account attachments without RAM share steps** —
  the owner creates the RAM share; the consumer creates the VPC
  attachment; the owner accepts the attachment (when
  `AutoAcceptSharedAttachments=false`). Missing either side leaves
  the attachment in `pendingAcceptance`.
- **NEVER claim success without verifying each attachment is
  `available`** via `describe-transit-gateway-vpc-attachments` —
  attachments in `pendingAcceptance` are non-functional.
- **NEVER deploy a peering attachment without verifying acceptance
  in the peer region** — a `pendingAcceptance` peering is
  non-functional.

### Worked example — TGW with 3 VPC attachments + cross-account RAM sharing

```text
TGW: prod-tgw-us-east-1
VERDICT: READY_TO_DEPLOY
TARGET: prod-tgw-us-east-1 (tgw-id: tgw-0abc123def)
PRE_CHECKS:
  - [PASS] TGW ASN 64512 unique within peering pair (peer TGW us-west-2 uses 64513)
  - [PASS] DNS support enabled, DNS propagation enabled
  - [PASS] VPC vpc-0app1 subnets subnet-0a1, subnet-0b1, subnet-0c1 all available, /28+
  - [PASS] VPC vpc-0app2 subnets subnet-0a2, subnet-0b2, subnet-0c2 all available, /28+
  - [PASS] VPC vpc-shared (account 222222222222) subnets subnet-0x1, subnet-0x2, subnet-0x3 all available, /28+
  - [PASS] AZ scope us-east-1a/b/c consistent across all three VPC attachments
  - [PASS] RAM share to 222222222222 is ACTIVE and accepted by consumer
  - [PASS] IAM principal holds ec2:CreateTransitGateway*, AssociateTransitGatewayRouteTable, EnableTransitGatewayRouteTablePropagation, ram:CreateResourceShare
  - [PASS] AutoAcceptSharedAttachments=false for production topology
CHECKLIST:
  TGW_CONFIG:
    ASN: 64512
    DNS support: enabled
    Multicast: disabled
    AutoAcceptSharedAttachments: disabled
    Default route table association: disabled
    Default route table propagation: disabled
  VPC_ATTACHMENTS:
    - Name: app1-tgw-attach | VPC: vpc-0app1 | Subnets: subnet-0a1, subnet-0b1, subnet-0c1 | AZs: us-east-1a/b/c | Appliance mode: disabled
    - Name: app2-tgw-attach | VPC: vpc-0app2 | Subnets: subnet-0a2, subnet-0b2, subnet-0c2 | AZs: us-east-1a/b/c | Appliance mode: disabled
    - Name: shared-tgw-attach | VPC: vpc-shared (acct 222222222222) | Subnets: subnet-0x1, subnet-0x2, subnet-0x3 | AZs: us-east-1a/b/c | Appliance mode: disabled
  ROUTE_TABLES:
    - Name: prod-rtb | Associations: app1-tgw-attach, app2-tgw-attach | Propagations: app1-tgw-attach, app2-tgw-attach, shared-tgw-attach
    - Name: shared-rtb | Associations: shared-tgw-attach | Propagations: shared-tgw-attach
  ROUTE_ENTRIES:
    - Route table: prod-rtb | Destination: 0.0.0.0/0 | Target: shared-tgw-attach
    - Route table: shared-rtb | Destination: 10.0.0.0/8 | Target: blackhole
  RAM_SHARE: 1 principal (account 222222222222, auto-accept disabled)
  NETWORK_MANAGER: registered global-network global-network-0abc
  CLOUD_WAN: not attached
STEPS:
  1. CONFIRM: About to create TGW prod-tgw-us-east-1 in account 111111111111 region us-east-1. Creates TGW (ASN 64512), 3 VPC attachments (2 in-owner, 1 cross-account via RAM), 2 route tables, 4 propagations, 2 static routes, 1 RAM share to 222222222222. Estimated cost: $36.50/mo base + $109.50/mo attachments + $0.02/GB processed. Proceed? (yes/no)
  2. aws ec2 create-transit-gateway --description "prod-tgw-us-east-1" --options AmazonSideAsn=64512,AutoAcceptSharedAttachments=disable,DefaultRouteTableAssociation=disable,DefaultRouteTablePropagation=disable,VpnEcmpSupport=enable,DnsSupport=enable,MulticastSupport=disable --tag-specifications "ResourceType=transit-gateway,Tags=[{Key=Name,Value=prod-tgw-us-east-1}]"
  3. aws ec2 create-transit-gateway-route-table --transit-gateway-id tgw-0abc123def --tag-specifications "ResourceType=transit-gateway-route-table,Tags=[{Key=Name,Value=prod-rtb}]"
  4. aws ec2 create-transit-gateway-route-table --transit-gateway-id tgw-0abc123def --tag-specifications "ResourceType=transit-gateway-route-table,Tags=[{Key=Name,Value=shared-rtb}]"
  5. aws ec2 create-transit-gateway-vpc-attachment --transit-gateway-id tgw-0abc123def --vpc-id vpc-0app1 --subnet-ids subnet-0a1 subnet-0b1 subnet-0c1 --options ApplianceModeSupport=disable,DnsSupport=enable --tag-specifications "ResourceType=transit-gateway-attachment,Tags=[{Key=Name,Value=app1-tgw-attach}]"
  6. aws ec2 create-transit-gateway-vpc-attachment --transit-gateway-id tgw-0abc123def --vpc-id vpc-0app2 --subnet-ids subnet-0a2 subnet-0b2 subnet-0c2 --options ApplianceModeSupport=disable,DnsSupport=enable --tag-specifications "ResourceType=transit-gateway-attachment,Tags=[{Key=Name,Value=app2-tgw-attach}]"
  7. aws ram create-resource-share --name prod-tgw-share --resource-arns arn:aws:ec2:us-east-1:111111111111:transit-gateway/tgw-0abc123def --principals 222222222222
  8. # CONSUMER ACCOUNT 222222222222: aws ram accept-resource-share-invitation --resource-share-invitation-arn <invitation-arn>
  9. # CONSUMER ACCOUNT 222222222222: aws ec2 create-transit-gateway-vpc-attachment --transit-gateway-id tgw-0abc123def --vpc-id vpc-shared --subnet-ids subnet-0x1 subnet-0x2 subnet-0x3 --tag-specifications "ResourceType=transit-gateway-attachment,Tags=[{Key=Name,Value=shared-tgw-attach}]"
  10. # OWNER ACCOUNT 111111111111: aws ec2 accept-transit-gateway-vpc-attachment --transit-gateway-vpc-attachment-id tgw-attach-0shared
  11. aws ec2 associate-transit-gateway-route-table --transit-gateway-route-table-id tgw-rtb-0prod --transit-gateway-attachment-id tgw-attach-0app1
  12. aws ec2 associate-transit-gateway-route-table --transit-gateway-route-table-id tgw-rtb-0prod --transit-gateway-attachment-id tgw-attach-0app2
  13. aws ec2 associate-transit-gateway-route-table --transit-gateway-route-table-id tgw-rtb-0shared --transit-gateway-attachment-id tgw-attach-0shared
  14. aws ec2 enable-transit-gateway-route-table-propagation --transit-gateway-route-table-id tgw-rtb-0prod --transit-gateway-attachment-id tgw-attach-0app1
  15. aws ec2 enable-transit-gateway-route-table-propagation --transit-gateway-route-table-id tgw-rtb-0prod --transit-gateway-attachment-id tgw-attach-0app2
  16. aws ec2 enable-transit-gateway-route-table-propagation --transit-gateway-route-table-id tgw-rtb-0prod --transit-gateway-attachment-id tgw-attach-0shared
  17. aws ec2 enable-transit-gateway-route-table-propagation --transit-gateway-route-table-id tgw-rtb-0shared --transit-gateway-attachment-id tgw-attach-0shared
  18. aws ec2 create-transit-gateway-route --transit-gateway-route-table-id tgw-rtb-0prod --destination-cidr-block 0.0.0.0/0 --transit-gateway-attachment-id tgw-attach-0shared --blackhole false
  19. aws ec2 create-transit-gateway-route --transit-gateway-route-table-id tgw-rtb-0shared --destination-cidr-block 10.0.0.0/8 --blackhole
POST_VERIFY:
  - (pending execution)
  - describe-transit-gateways returns State=available for tgw-0abc123def
  - describe-transit-gateway-vpc-attachments returns 3 attachments all State=available (cross-account shared-tgw-attach accepted)
  - describe-transit-gateway-route-tables returns 2 route tables (prod-rtb, shared-rtb)
  - prod-rtb has 3 propagations (app1, app2, shared) and 1 static route (0.0.0.0/0 -> shared)
  - shared-rtb has 1 propagation (shared) and 1 blackhole route (10.0.0.0/8)
  - EC2 in vpc-0app1 reaches EC2 in vpc-shared and vpc-0app2 (traceroute via TGW)
NOTES:
  - Segmentation: prod-rtb for app1+app2; shared-rtb for shared-services VPC (cross-account 222222222222).
  - Shared reaches prod (propagation enabled to prod-rtb); prod reaches shared (default route 0.0.0.0/0 -> shared-tgw-attach for egress).
  - Reverse isolation: prod-rtb does NOT propagate to shared-rtb; shared-rtb only sees its own routes plus the 10.0.0.0/8 blackhole.
  - Cross-account flow: owner (111111111111) shared TGW via RAM -> consumer (222222222222) accepted share -> consumer created VPC attachment -> owner accepted attachment (AutoAcceptSharedAttachments=false).
  - Cost: $36.50/mo TGW base + 3 * $0.05/hr * 730 hr = $109.50/mo for attachments + ~$0.02/GB processed.
```

## NEVER (top 5)

These are the highest-impact, most-frequent failure modes in Transit
Gateway deployments. Violating any one of these is a correctness or
security regression.

1. **NEVER conflate route table association with propagation.**
   Association = which route table an attachment LOOKS UP routes in
   (one per attachment). Propagation = which route tables an
   attachment INJECTS its routes into (many). Forgetting propagation
   is the #1 cause of "I attached the VPC but can't reach it"
   outages. Always emit both as separate PRE_CHECKS rows.

2. **NEVER deploy cross-account attachments without verifying the
   RAM share is `ACTIVE` in the consumer account.** A `PENDING` or
   `REJECTED` share prevents the consumer from creating the VPC
   attachment. With `AutoAcceptSharedAttachments=false`, the owner
   must also `accept` the consumer's attachment after creation.

3. **NEVER enable multicast after TGW creation.** Multicast support
   is set at `create-transit-gateway` time and cannot be toggled
   later. If you anticipate multicast in 1-2 years, enable it at
   creation — the cost is identical.

4. **NEVER use inconsistent AZ scopes across VPC attachments without
   documenting the cross-AZ traffic impact.** Attachment A in
   us-east-1a/b/c and B in us-east-1a/b/d forces cross-AZ traffic
   between c and d, incurring cross-AZ transfer charges.

5. **NEVER deploy a Connect attachment as a VPN replacement.**
   Connect rides on top of a VPC or Direct Connect gateway
   attachment and does NOT encrypt — it tunnels GRE over an existing
   transport. For internet-based transport, use a Site-to-Site VPN
   attachment as the transport for the Connect attachment. SD-WAN
   appliances handle their own encryption; do not assume Connect
   provides it.

## Expert heuristic: TGW route tables vs. security group segmentation

Segmentation in a TGW topology can be enforced at TWO layers: TGW
route tables (network-layer isolation) or VPC security groups
(instance-layer isolation). The heuristic below resolves which to use.

| Signal | Choose |
|---|---|
| Hard isolation between prod and non-prod (audit/compliance) | TGW route tables (no propagation between tiers) |
| Soft segmentation between application tiers within a VPC | Security groups (more flexible) |
| Many segments (>5) with complex routing policies | TGW route tables (security groups don't scale) |
| Per-instance or per-subnet access control | Security groups (TGW is per-VPC) |
| Compliance regime requiring "air gap" between environments | TGW route tables with blackhole routes |
| Cross-account isolation | TGW route tables (security groups are account-scoped) |

**Decision rules:**

- Default to TGW route tables for any topology with 3+ VPCs or
  multiple segmentation tiers. Use security groups for fine-grained
  access within a VPC.
- For "air gap" compliance (e.g., PCI scope isolation), use TGW
  route tables with no cross-tier propagation plus blackhole routes.
- For Cloud WAN topologies, let Cloud WAN manage the route tables —
  manual route table changes inside a Cloud WAN-managed TGW will be
  overwritten by the next policy application.
- Security groups are always recommended ADDITIONALLY — defense in
  depth. They do not replace route table segmentation.

ALWAYS emit the segmentation model as a PRE_CHECKS row naming the
route table topology, the segmentation tiers, and the propagation
directions.

## Recent AWS features (2024-2026)

- **AWS Cloud WAN (2022-2024):** global network abstraction on top
  of TGWs. Policy-driven segmentation, route table management, and
  cross-region policy application. Existing TGWs attach non-disruptively.

- **TGW multicast domains (2023-2024):** IGMPv2 support, static
  sources, cross-VPC multicast group membership. Must be enabled at
  TGW creation. Use for video broadcast, financial market data,
  gaming backplanes.

- **TGW Connect with BGP (2023-2025):** Connect peers exchange BGP
  routes with the TGW, injecting on-prem SD-WAN routes as propagated
  routes. BGP MD5 authentication (2024). GRE-only protocol (no
  IPsec) — assumes underlying transport encrypts.

- **Inter-region peering enhancements (2024):** up to 50 Gbps per
  peering connection, lower latency via AWS backbone, Flow Logs
  support for peering traffic.

- **TGW Flow Logs (2023-2024):** VPC Flow Logs format captures TGW
  traffic including peering and Connect attachment traffic. Send to
  CloudWatch Logs, S3, or Kinesis.

- **Network Manager topology (2024-2025):** real-time topology view
  of all registered TGWs, attachments, peers, and Connect peers.
  Includes on-prem device registration for hybrid views.

- **Appliance mode IPv6 (2024):** preserved AZ semantics extended to
  IPv6 traffic; improved handling of stateful firewall asymmetric
  flows.

## AWS documentation

- **AWS Transit Gateway User Guide** — https://docs.aws.amazon.com/vpc/latest/tgw/what-is-transit-gateway.html
- **TGW route tables** — https://docs.aws.amazon.com/vpc/latest/tgw/tgw-route-tables.html
- **TGW VPC attachments** — https://docs.aws.amazon.com/vpc/latest/tgw/tgw-vpc-attachments.html
- **TGW peering attachments** — https://docs.aws.amazon.com/vpc/latest/tgw/tgw-peering.html
- **TGW Connect attachments** — https://docs.aws.amazon.com/vpc/latest/tgw/tgw-connect.html
- **TGW multicast domains** — https://docs.aws.amazon.com/vpc/latest/tgw/tgw-multicast-overview.html
- **AWS Cloud WAN User Guide** — https://docs.aws.amazon.com/networkmanager/latest/cloudwan/what-is-cloudwan.html
- **TGW API Reference** — https://docs.aws.amazon.com/AWSEC2/latest/APIReference/Amazon_EC2_Transit_Gateways.html
