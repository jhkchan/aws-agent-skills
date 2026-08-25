# Advanced Patterns - vpn-connection-deployer

## Mindset deep dive: three provisioning misconceptions (moved from SKILL.md)

Three misconceptions dominate Site-to-Site VPN misdesign at provisioning
time:

- **"Creating the VPN connection is enough."** It is not. Creating the
  VPN connection provisions the two IPSec tunnels, but NO traffic flows
  until routes are configured on BOTH the AWS side (route table / TGW
  propagation) AND the customer side (on-prem device). Static routes
  require explicit `create-vpn-connection-route` calls or route-table
  association; BGP requires the customer device to bring up the BGP
  session. This is the #1 cause of "my VPN doesn't pass traffic" tickets.

- **"One tunnel is enough for redundancy."** AWS provisions TWO tunnels
  per VPN connection by default. However, both tunnels only provide
  redundancy if BOTH are actively configured on the customer device. A
  common mistake is to configure only tunnel 1 and leave tunnel 2 down
  — the customer thinks they have redundancy but only one tunnel is
  carrying traffic. For active-active, enable BGP ECMP or set tunnel
  priority; for active-passive, ensure the customer device fails over
  to tunnel 2 when tunnel 1 drops.

- **"BGP and static routing are interchangeable."** They are not. BGP
  enables route health detection — if a tunnel fails, BGP withdraws
  the route, and traffic shifts automatically. Static routes have no
  health detection — if a tunnel fails, the static route remains, and
  traffic is black-holed until the customer device detects the failure
  (via DPD or SLA probes). For production HA, BGP is strongly preferred.

## Configuration dependency graph detail (moved from SKILL.md)

Site-to-Site VPN configurations are NOT independent. The customer
gateway must exist before the VPN connection. The VPN connection's
target (VPG or TGW) must be selected before creation. Routes propagate
only after tunnels are UP. Use this graph to sequence provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Customer Gateway (CGW) | on-prem public IP (or private IP for NAT) known; BGP ASN if dynamic | CGW does not validate reachability until VPN is created | the peer identity for VPN |
| Virtual Private Gateway (VPG) | the target VPC exists | VPG must be ATTACHED (attach-vpn-gateway) before VPN creation; attach is async | AWS-side endpoint for VPC-attached VPN |
| Transit Gateway (TGW) | TGW exists in the account | TGW VPN attachment is created at VPN-creation time; attachment propagates via TGW route tables | AWS-side endpoint for hub-and-spoke VPN |
| VPN connection (IPSec) | CGW + (VPG-attached OR TGW-id) both exist | tunnels stay DOWN until the customer device brings them up; AWS cannot initiate | two IPSec tunnels |
| Static routes | VPN connection exists; tunnels UP | static routes do NOT detect tunnel failure — traffic black-holed until customer-side failover | traffic flow per-prefix |
| BGP (dynamic routes) | VPN connection exists; customer device has matching BGP ASN + neighbor config | BGP requires the CUSTOMER device to initiate the session; AWS advertises VPC/TGW prefixes | auto-failover + route health |
| Tunnel options | set at VPN-creation time via --options | IMMUTABLE after creation — must delete and recreate VPN to change IKE, encryption, or lifetimes | customized IPSec parameters |
| CloudWatch monitoring | VPN connection exists | TunnelState / TunnelDataIn / TunnelDataOut emit at 1-min interval; no metric = tunnel never came UP | operational visibility |
| Global Accelerator | VPN connection exists; acceleration enabled at creation | CANNOT be added post-creation — must create a NEW accelerated VPN; changes billing | lower latency via AWS backbone |

**The tunnel-options-are-immutable row is the one a baseline model
misses.** A baseline model suggests "update the tunnel encryption" or
"add DPD" — impossible without deleting and recreating the VPN. The
procedure below forces an explicit decision on tunnel options BEFORE
creation.

**Cross-dependency gotchas:**
- BGP and static routing on the same tunnel causes unpredictable route
  preference. Use BGP on both tunnels, or static on both tunnels.
- The customer gateway's BGP ASN must match the on-prem device's BGP
  ASN. A mismatch means BGP never establishes.
- VPG-attached VPNs propagate routes to the VPC route table (enable
  VPG route propagation). TGW-attached VPNs propagate via TGW route
  tables (separate configuration).
- For a NAT'd on-prem device, the CGW's IP is the PUBLIC IP of the NAT
  device, not the on-prem device's private IP. UDP NAT-T encapsulation
  is required.

## Expert heuristic: dual-tunnel active-active vs active-passive (moved from SKILL.md)

A baseline model says "create the VPN, it has two tunnels." The correct
heuristic recognizes that BOTH tunnels must be configured on the
customer device, and the traffic-distribution mode depends on routing.

```text
VPN connection (vpn-xxx) has TWO tunnels:
  Tunnel 1 → AWS endpoint A (outside IP 3.x.x.x) — inside 169.254.x.x/30
  Tunnel 2 → AWS endpoint B (outside IP 3.y.y.y) — inside 169.254.y.y/30

Active-Passive (default, static routing):
  ├── Tunnel 1: primary (route priority lower)
  └── Tunnel 2: standby (only used when Tunnel 1 DOWN)
  → Customer device must detect Tunnel 1 failure (DPD or SLA) and switch

Active-Active (BGP + ECMP, or BGP AS_PATH prepending):
  ├── Tunnel 1: carries ~50% of traffic
  └── Tunnel 2: carries ~50% of traffic
  → BGP ECMP over both tunnels; requires customer device BGP ECMP support

For production HA: prefer BGP dynamic routing + active-active.
For simple failover: static routing + active-passive with DPD enabled.
```

**Key implication:** the #1 redundancy failure is "I created the VPN
with two tunnels but only configured tunnel 1 on my device." Always
verify BOTH tunnels are configured and UP via CloudWatch TunnelState.

## Expert heuristic: BGP vs static route preference (moved from SKILL.md)

```text
Routing decision tree:
  ├── Need automatic failover + route health detection?
  │     └── YES → BGP (dynamic routing)
  │           ├── AWS side: BGP ASN 64512 (default) or custom ASN on VPG/TGW
  │           ├── Customer side: matching BGP ASN + neighbor (169.254.x.x AWS-side)
  │           └── BGP advertises VPC/TGW prefixes; route health auto-detected
  │
  ├── Simple connectivity, manual failover acceptable?
  │     └── YES → Static routing
  │           ├── AWS side: create-vpn-connection-route per prefix
  │           ├── Customer side: static route to VPC CIDR via tunnel
  │           └── NO route health — tunnel failure black-holes traffic
  │
  └── Already using Direct Connect + need VPN backup?
        └── YES → BGP with AS_PATH prepending on Direct Connect
              ├── Direct Connect preferred (shorter AS_PATH)
              └── VPN backup (longer AS_PATH via prepending)
```

**Key implication:** for any production workload requiring automatic
failover, BGP is strongly preferred. Static routing requires customer-
side detection mechanisms (DPD, SLA probes, BFD if supported).

## Expert heuristic: IKE lifecycle negotiation caveats (moved from SKILL.md)

IKE has two phases, and a baseline model often conflates them. Each
phase has its own lifetime, and mismatched lifetimes cause tunnel
flapping.

```text
IKE Phase 1 (secure management channel):
  ├── Negotiates: encryption (AES-128/256), integrity (SHA-1/SHA-256),
  │                PRF, Diffie-Hellman group (2/14/15/16/17/18/19/20/21)
  ├── Lifetime: default 28800 seconds (8 hours)
  ├── Rekey: Phase 1 SA rekey at lifetime boundary
  └── Mismatch = tunnel never establishes

IKE Phase 2 (IPSec data SA — one per tunnel):
  ├── Negotiates: ESP encryption, ESP integrity, PFS group, DH group
  ├── Lifetime: default 3600 seconds (1 hour)
  ├── Rekey: Phase 2 SA rekey happens more frequently than Phase 1
  └── Mismatch = tunnel establishes but drops at first rekey

Dead Peer Detection (DPD):
  ├── Detects peer failure (interval + max retries)
  ├── Default: DPD enabled, interval 10s, retries 3
  └── Without DPD, a tunnel failure may not be detected for the full
      Phase 1 lifetime (8 hours of black-hole)
```

**Key implication:** Phase 2 rekey mismatches cause tunnels that come
UP but drop after ~1 hour. Always verify both Phase 1 AND Phase 2
parameters match on both sides. DPD is critical for static-routed VPNs
— without it, the customer device may not detect tunnel failure.

## Step 6 - redundancy mode table (moved from SKILL.md)

| Mode | Tunnel 1 | Tunnel 2 | Failover |
|---|---|---|---|
| Active-passive (static) | primary | standby | Customer device detects failure, switches to tunnel 2 |
| Active-active (BGP ECMP) | ~50% traffic | ~50% traffic | Automatic — BGP withdraws failed tunnel's routes |
| Active-active (priority) | higher priority | lower priority | Automatic via BGP LOCAL_PREF or AS_PATH prepend |

## Step 6 - redundant VPN connections, four tunnels (moved from SKILL.md)

**Redundant VPN connections:** for maximum HA, create TWO VPN
connections to TWO customer gateways (two on-prem devices). Each VPN
has two tunnels — total of 4 tunnels. With BGP, all 4 tunnels can be
active (4-way ECMP) for maximum throughput and redundancy.

## Step 8 - Global Accelerator accelerated VPN (moved from SKILL.md)

```bash
VPN_ID=$(aws ec2 create-vpn-connection --type ipsec.1 \
  --customer-gateway-id "$CGW_ID" --transit-gateway-id "$TGW_ID" \
  --options '{"Accelerate":true}' \
  --region us-east-1 \
  --query 'VpnConnection.VpnConnectionId' --output text)
```

**Critical:** `Accelerate:true` can ONLY be set at creation time. It
CANNOT be added to an existing VPN connection — create a NEW accelerated
VPN. Acceleration changes billing (Global Accelerator data-transfer
pricing applies in addition to VPN hours).

## Step 10 - IPv6 + Outside IP address types (moved from SKILL.md)

**IPv6 support:** Site-to-Site VPN supports IPv6 traffic inside tunnels
if both the VPC and the on-prem network have IPv6 ranges. The outside
(tunnel endpoints) still use IPv4 public IPs.

```bash
aws ec2 create-vpn-connection-route --vpn-connection-id "$VPN_ID" \
  --destination-cidr-block 2600:1f18:4113:a100::/56 --region us-east-1
```

**Outside IP address types:**

| Type | When to use | CGW IP |
|---|---|---|
| Publicly routable | On-prem device has a public IP | Public IP of the device |
| Private (behind NAT) | On-prem device behind a NAT | Public IP of the NAT device |

For NAT'd devices, the CGW's `--public-ip` is the NAT's public IP, and
UDP NAT-T encapsulation must be enabled. The on-prem device initiates
the tunnel to AWS (AWS cannot initiate to a NAT'd device).

## Step 11 - Recent AWS features 2023-2026 (moved from SKILL.md)

**Recent AWS features (2023-2026):**

- **IKEv2 default (2023-2024):** IKEv2 is now the default IKE version
  for new VPN connections. IKEv1 is supported but deprecated. IKEv2
  supports modern cryptography and is more resilient to rekey issues.

- **Inside IP address customization (2023-2024):** The tunnel inside
  CIDR (169.254.x.x/30) can be customized at creation time. Useful for
  overlapping inside CIDRs across multiple VPN connections.

- **Global Accelerator for VPN (2023-2024):** Acceleration can be
  enabled at VPN creation to route traffic over the AWS global backbone,
  reducing latency for cross-region VPN connections. Cannot be added
  post-creation.

- **BGP MD5 authentication (2024-2025):** MD5 authentication for BGP
  sessions over VPN, providing additional security for the BGP control
  plane. Requires customer device support.

- **Transit Gateway support for VPN ECMP (2024-2025):** TGW-attached
  VPNs support ECMP across multiple tunnels, enabling active-active
  load balancing for higher throughput.

- **CloudWatch VPN metrics enhancement (2024-2025):** Enhanced metrics
  including per-tunnel error counts and SLA measurements.

- **IPv6 inside tunnels (2024-2026):** IPv6 traffic inside VPN tunnels
  for dual-stack VPC and on-prem networks. Outside addresses remain IPv4.

- **Private IPv4 outside addresses (2025-2026):** Private IPv4 outside
  addresses for VPN connections behind NAT gateways, enabling fully
  private VPN topologies without public IPs.
