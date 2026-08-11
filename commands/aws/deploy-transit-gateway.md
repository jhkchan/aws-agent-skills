---
description: Provision a production-grade AWS Transit Gateway topology with VPC attachments, route tables (association + propagation), inter-region peering, Connect attachments for SD-WAN, multicast domains, Network Manager, RAM cross-account sharing, and AWS Cloud WAN integration.
nl_triggers:
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
routes_to: transit-gateway-deployer
---

# /aws:deploy-transit-gateway

Activate the `transit-gateway-deployer` skill and produce a
deployment plan for a production-grade AWS Transit Gateway topology
with secure defaults.

## What it does

Reads a deployment specification (TGW options, VPC attachments with
subnet selections, route table topology with associations and
propagations, optional peering connections, optional Connect
attachments, optional RAM share principals, optional Cloud WAN
integration) and produces an ordered deployment plan with:

1. Pre-flight specification gate — validates TGW ASN uniqueness
   within peering pairs, VPC subnets available with /28+ CIDR and
   consistent AZ scope, route table association/propagation
   topology, RAM share `ACTIVE` in consumer accounts, peering
   acceptance state, Connect transport attachment availability,
   multicast domain membership. Blocks deployment
   (PREREQUISITES_MISSING) on missing fields or invalid config.
2. TGW creation — AmazonSideAsn (64512-65535 private range),
   DnsSupport, MulticastSupport (cannot be toggled later),
   AutoAcceptSharedAttachments (disable for prod),
   DefaultRouteTableAssociation / DefaultRouteTablePropagation,
   VpnEcmpSupport, optional TransitGatewayCidrBlocks.
3. VPC attachments — one subnet per AZ, consistent AZs across the
   topology, optional appliance mode for NVA inspection.
4. Route tables — default (auto-created) plus optional non-default
   tables. Explicit association (one per attachment) and
   propagation (many per attachment). Static routes and blackhole
   routes for default routing / segmentation.
5. Peering attachments — intra-region and inter-region. Manual
   acceptance required in peer region (peer owner must call
   `accept-transit-gateway-peering-attachment`).
6. Connect attachments — GRE tunnels on top of a VPC or Direct
   Connect gateway transport attachment. Connect peer terminates
   GRE and establishes BGP with an SD-WAN controller. Supports
   BGP MD5 authentication (2024+). NOT a VPN replacement.
7. Multicast domains — IGMPv2 support, static sources, cross-VPC
   membership. Requires MulticastSupport=enable at TGW creation.
8. Network Manager — global network topology visualization across
   all registered TGWs.
9. Cross-account sharing — AWS RAM resource share with two-sided
   handshake: owner shares, consumer accepts share, consumer
   creates VPC attachment, owner accepts attachment (when
   AutoAcceptSharedAttachments=disable).
10. AWS Cloud WAN integration — attach existing TGWs to a core
    network for policy-driven segmentation. Non-disruptive; cutover
    by re-associating attachments to Cloud WAN-managed route tables.

Emits a deterministic deployment plan per TGW:

```text
TGW: <tgw-name-or-id>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
TARGET: <tgw-name>
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. CONFIRM: About to <operation> TGW <name> in account <account> region <region>. Estimated monthly cost: <$X>. Proceed? (yes/no)
  2. <exact CLI command — no placeholders>
POST_VERIFY:
  - [PASS] <verification description>
TGW_OPTIONS: ASN <asn> DNS <enabled|disabled> multicast <enabled|disabled> auto-accept <enabled|disabled>
ATTACHMENTS: <count> VPC + <count> peering + <count> connect
ROUTE_TABLES: <count> with <count> associations and <count> propagations
RAM_SHARE: <count> principals (auto-accept <enabled|disabled>)
CLOUD_WAN: <attached|not attached> core-network <id>
NOTES: <segmentation model, peering direction, cost posture>
```

## When to invoke

Provide a deployment spec and ask any of:

- "provision a hub-and-spoke Transit Gateway"
- "deploy a multi-region TGW topology with inter-region peering"
- "TGW Connect attachment for my SD-WAN"
- "cross-account VPC attachment via RAM share"
- "Cloud WAN migration from existing TGWs"
- "TGW route table segmentation (prod vs non-prod)"
- "centralized egress via firewall NVA with appliance mode"
- "TGW multicast domain for video broadcast"

A bare "TGW + VPC attachments + deploy" also routes here via the
orchestrator.

## Inputs

- **Required:** tgw_asn (64512-65535 or 4-byte private range),
  vpc_attachments (list of {vpc_id, subnet_ids} per attachment),
  route_table_topology (associations + propagations per attachment,
  or "default" for flat topology).
- **Optional:** dns_support, multicast_support,
  auto_accept_shared_attachments, default_route_table_association,
  default_route_table_propagation, vpn_ecmp_support,
  appliance_mode_per_attachment, peering_peers (list of peer TGW
  IDs in peer regions), connect_attachments (list of
  {transport_attachment_id, peer_asn, peer_address, inside_cidr,
  bgp_auth_key}), multicast_domains, ram_share_principals,
  network_manager_global_network_id, cloud_wan_core_network_id.

## Outputs

- One VERDICT block per TGW (READY_TO_DEPLOY or
  PREREQUISITES_MISSING).
- PRE_CHECKS with all dimensions validated (ASN uniqueness, subnet
  availability, AZ scope consistency, route table wiring, RAM
  share state, peering acceptance, Connect transport, multicast
  domain membership).
- STEPS with ordered `aws ec2 create-transit-gateway*` commands
  plus prerequisite IAM/RAM setup, starting with the CONFIRM gate.
- POST_VERIFY with verification steps (describe-transit-gateways
  returns `available`; attachments `available`; route table
  associations and propagations match the topology; cross-VPC
  traceroute succeeds).
- NOTES with segmentation model, peering direction, and cost
  posture.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill
  is the Phase 1 Deploy specialist for Transit Gateway network
  topology).
- `/aws:audit-direct-connect-topology` for dedicated-network
  auditing (Direct Connect can serve as transport for TGW Connect
  attachments).
- `/aws:audit-vpc-lattice-auth` for application-layer service mesh
  (complements TGW for network-layer routing).
- `/aws:deploy-globalaccelerator` for anycast edge networking
  (Global Accelerator complements TGW for user-facing entry points).
