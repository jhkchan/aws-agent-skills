# Advanced patterns — transit-gateway-deployer

Moved verbatim from SKILL.md for progressive disclosure. Load on demand.

## Mindset — three facts that make TGW provisioning different

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
**Transit Gateway limits (2026):**

- TGWs per region per account: 5 (soft limit; raise via support).
- VPC attachments per TGW: 50 (soft; raise to 500). Route tables per TGW: 50 (raise to 100).
- Routes per route table: 10000. Peering attachments per TGW: 50.
- Connect attachments per TGW: 20. Connect peers per Connect attachment: 4 (hard).
- Multicast domains per TGW: 20. Multicast group members per domain: 1000.
- Supported ASNs: 64512-65535 (private 2-byte), 4200000000-4294967294 (private 4-byte).
- Throughput: up to 50 Gbps per attachment (burst 100 Gbps); 500 Gbps aggregate; inter-region peering up to 50 Gbps.

**Appliance mode deep-dive:** when enabled, the TGW preserves the
source AZ for return traffic, allowing the NVA to handle asymmetric
flows. Without appliance mode, return packets may exit a different
AZ's ENI, breaking stateful firewalls.
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
