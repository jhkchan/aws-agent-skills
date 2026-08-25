# Advanced patterns — transit-gateway-routing-troubleshooter

Moved verbatim from SKILL.md for progressive disclosure. Load on demand.

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
