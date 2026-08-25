---
name: vpn-connection-deployer
description: 'Provisions AWS Site-to-Site VPN connections with production defaults: customer gateway (CGW), virtual private gateway (VPG) vs transit gateway (TGW) VPN attachment, VPN connection (IPSec), routing (static vs dynamic/BGP), tunnel options (IKE versions, encryption algorithms, Phase 1/2 SA lifetimes, dead peer detection), dual-tunnel redundancy, CloudWatch monitoring (TunnelState, TunnelDataIn/Out), acceleration via Global Accelerator, redundant VPN connections, IPv6 support, and outside IP address types (public vs private NAT). Emits a READY_TO_DEPLOY checklist with verification commands. Use when creating a Site-to-Site VPN, connecting an on-premises network to AWS, configuring BGP over VPN, setting up dual-tunnel redundancy, or attaching a VPN to a transit gateway. Triggers: create site-to-site vpn, customer gateway, virtual private gateway, vpn connection ipsec, bgp over vpn, dual tunnel redundancy, transit gateway vpn attachment, vpn cloudwatch monitoring, global accelerator vpn, vpn ipv6.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with ec2 access (and cross-account STS assume-role if CGW is in another account). Works with Terraform aws_customer_gateway / aws_vpn_gateway / aws_vpn_connection / aws_vpn_connection_route / aws_ec2_transit_gateway_vpn_attachment resources and CloudFormation AWS::EC2::CustomerGateway / AWS::EC2::VPNGateway / AWS::EC2::VPNConnection templates.'
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
  tags: aws, site-to-site-vpn, vpn-connection, customer-gateway, virtual-private-gateway, cloudops, deploy, networking, provisioning, ipsec, bgp, dual-tunnel
  dependencies: aws-orchestrator
  keywords: aws, site-to-site vpn, vpn connection, customer gateway, virtual private gateway, transit gateway vpn attachment, cloudops, deploy, provisioning, ipsec, bgp, dual tunnel, ike, encryption, cloudwatch, global accelerator, ipv6
  when_to_use: Invoke when the user wants to create an AWS Site-to-Site VPN connection (IPSec) between an on-premises network and AWS, configure BGP or static routing over VPN, set up dual-tunnel redundancy, attach a VPN to a transit gateway, customize tunnel options (IKE, encryption, lifetimes, DPD), accelerate VPN traffic via Global Accelerator, or monitor VPN tunnels via CloudWatch. Do NOT invoke for AWS Client VPN (use client-vpn-endpoint-deployer), VPC peering (use vpc-peering-deployer), Direct Connect (use direct-connect skills), or VPC endpoints / PrivateLink.
---

# VPN Connection Deployer

An AWS CloudOps agent skill that provisions AWS Site-to-Site VPN
connections with correct defaults. The skill walks the operator through
customer gateway creation, the VPG-vs-TGW-attachment decision, IPSec
VPN connection creation, static-vs-BGP routing, tunnel-option
customization (IKE versions, encryption algorithms, Phase 1/2 SA
lifetimes, dead peer detection), dual-tunnel redundancy, CloudWatch
monitoring, Global Accelerator acceleration, and IPv6 support, captures
topology and routing decisions, explains why each default matters, and
emits a READY_TO_DEPLOY checklist with copy-pasteable verification
commands.

## Activation keywords

create Site-to-Site VPN, customer gateway, virtual private gateway,
VPN connection IPSec, BGP over VPN, dual-tunnel redundancy, transit
gateway VPN attachment, VPN CloudWatch monitoring, Global Accelerator
VPN, VPN IPv6.

## STRICT output contract

When this skill is invoked with a Site-to-Site VPN provisioning request
(create a VPN connection, connect on-premises to AWS, configure BGP,
set up dual tunnels, attach VPN to a TGW, customize tunnel options,
accelerate via Global Accelerator, or a partial configuration), the
agent MUST respond with the READY_TO_DEPLOY checklist defined below.
This contract is what assertion-based evals and downstream provisioning
pipelines rely on; deviating from the literal labels breaks automation
silently.

### Required output structure

The model MUST emit output using these literal labels, in this order,
as the FIRST lines of the response (no prose, headings, or disclaimers
before them):

- `VPN_CONNECTION: <vpn-id> — CGW <cgw-id> → <VPG-id | TGW-id>` — first line
- `VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING` — second line
- `CHECKLIST:` followed by `- [✓]` or `- [✗]` items (one row per dimension below)
- `VERIFICATION_COMMANDS:` followed by a fenced block of copy-pasteable CLI

The CHECKLIST MUST cover every dimension, in this order: Customer
Gateway (public IP + BGP ASN), AWS-side target (VPG attached to a VPC,
or TGW), VPN connection (two IPSec tunnels), routing mode (static vs
dynamic BGP with both ASNs), Tunnel 1 (outside IP + inside CIDR + IKE
version), Tunnel 2 (same), Phase 1 crypto (encryption / integrity / DH
group / lifetime), Phase 2 crypto (encryption / integrity / PFS group /
lifetime), DPD (timeout + retries), redundancy mode (active-passive vs
active-active BGP ECMP), route propagation (VPG route propagation
enabled OR TGW route table ID), VPC route table update for the on-prem
CIDR, CloudWatch TunnelState alarm + SNS ARN, Global Accelerator
(enabled/disabled), IPv6 (enabled or IPv4 only), outside IP type (public
or NAT), and tags.

### Decision tree (determines VERDICT)

```text
Is the on-prem peer's outside IP (public or NAT) known?
├── NO  → VERDICT: PREREQUISITES_MISSING  ([✗] Customer Gateway IP)
└── YES → Is the AWS-side target ready (VPG attached to a VPC, OR a TGW exists)?
          ├── NO  → VERDICT: PREREQUISITES_MISSING  ([✗] VPG/TGW target)
          └── YES → Is the routing mode decided (static OR dynamic BGP)?
                    ├── NO  → VERDICT: PREREQUISITES_MISSING  ([✗] Routing mode)
                    └── YES → Are tunnel options decided BEFORE create (immutable after)?
                              ├── NO  → VERDICT: PREREQUISITES_MISSING  ([✗] Tunnel options — immutable post-create)
                              └── YES → If dynamic BGP, does the CGW ASN match the on-prem device ASN?
                                        ├── NO  → VERDICT: PREREQUISITES_MISSING  ([✗] BGP ASN mismatch)
                                        └── YES → All prerequisites satisfied
                                                  → VERDICT: READY_TO_DEPLOY
```

### FORBIDDEN patterns (NEVER)

1. **NEVER preface the CHECKLIST** with prose, headings, or disclaimers — emit the block as the first lines of the response.
2. **NEVER omit the VERIFICATION_COMMANDS section**, even when every checklist item passes.
3. **NEVER use generic placeholders** (`<vpn-id>`, `<your-ip>`, `<region>`) in a worked example — always use concrete VPN IDs, real outside IPs, specific 169.254.x.x/30 inside CIDRs, and exact CLI commands.
4. **NEVER mix verdict shapes** — if any prerequisite is `[✗]`, VERDICT MUST be `PREREQUISITES_MISSING` and `READY_TO_DEPLOY` MUST NOT also appear.
5. **NEVER skip a CHECKLIST row** — every dimension (CGW, target, tunnels, routing, Phase 1, Phase 2, DPD, redundancy, route propagation, CloudWatch, acceleration, IPv6, outside IP, tags) gets a `[✓]` or `[✗]` line.
6. **NEVER claim redundancy with only one tunnel configured** — both tunnels must be on the customer device; mark `[✗]` if tunnel 2 is unconfigured.
7. **NEVER omit Phase 1 AND Phase 2 parameters** — a tunnel row without crypto details (AES / SHA / DH group / lifetime) hides the silent failure mode where the tunnel comes UP then drops at the first rekey (~1 hour).
8. **NEVER list a static-routed VPN as "automatic failover"** — static routes have no health detection. Mark active-passive with DPD only.

### Perfect example — dual-tunnel BGP VPN with AES256/SHA256/DH17 IKEv2

This is the EXACT shape the model emits for a positive scenario. Copy
the literal labels, the bracket glyphs, and the fenced command block.
Both tunnels are BGP-active (ECMP); route propagation flows via the TGW
route table. Replace the concrete values with the scenario's values;
do not genericise them into placeholders.

```text
VPN_CONNECTION: vpn-0abc123def456 — CGW cgw-0fedcba98765 → TGW tgw-000111222333
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Customer Gateway: cgw-0fedcba98765 (203.0.113.12, BGP ASN 65000)
  [✓] AWS-side target: TGW tgw-000111222333 (attachment tgw-attach-1a2b3c4d)
  [✓] VPN connection: vpn-0abc123def456 — two IPSec tunnels
  [✓] Routing: Dynamic BGP (AWS ASN 64512 ↔ customer ASN 65000)
  [✓] Tunnel 1: outside 3.221.215.181 — inside 169.254.10.0/30 — IKEv2
  [✓] Tunnel 2: outside 3.221.215.204 — inside 169.254.10.4/30 — IKEv2
  [✓] Phase 1: AES256 / SHA256 / DH group 17 / lifetime 28800s
  [✓] Phase 2: AES256 / SHA256 / PFS group 17 / lifetime 3600s
  [✓] DPD: timeout 30s, retries 3
  [✓] Redundancy: active-active (BGP ECMP across both tunnels)
  [✓] Route propagation: TGW route table tgw-rtb-000aaa111 (propagation enabled, association confirmed)
  [✓] VPC route table update: rtb-0abc111222 (TGW propagation active for 10.20.0.0/16)
  [✓] CloudWatch: TunnelState alarm on arn:aws:sns:us-east-1:123456789012:vpn-alerts (period 60s, 5 eval periods)
  [✓] Acceleration: Global Accelerator disabled
  [✓] IPv6: IPv4 only
  [✓] Outside IP: public (203.0.113.12, no NAT)
  [✓] Tags: Environment=production, Topology=onprem-to-tgw, Owner=netops
VERIFICATION_COMMANDS:
  aws ec2 describe-vpn-connections --vpn-connection-ids vpn-0abc123def456 --region us-east-1
  aws ec2 describe-customer-gateways --customer-gateway-ids cgw-0fedcba98765 --region us-east-1
  aws ec2 describe-transit-gateway-attachments --filters Name=resource-id,Values=vpn-0abc123def456 --region us-east-1
  aws cloudwatch get-metric-statistics --namespace AWS/VPN --metric-name TunnelState --dimensions Name=VpnId,Value=vpn-0abc123def456 Name=TunnelIpAddress,Value=3.221.215.181 --start-time 2026-08-11T00:00:00Z --end-time 2026-08-11T00:10:00Z --period 60 --statistics Minimum --region us-east-1
```

If any prerequisite fails, emit the SAME shape with
`VERDICT: PREREQUISITES_MISSING`, the failing row marked `[✗]` with a
specific gap citation (e.g. `[✗] Customer Gateway: on-prem ASN 65000
does not match CGW ASN 65100`), the passing rows still listed, and
VERIFICATION_COMMANDS showing the command that would confirm the gap.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Customer Gateway (CGW) | On-prem peer identity |
| Step 2 — VPG vs TGW attachment | AWS-side attachment target |
| Step 3 — VPN connection (IPSec) | Provisioning step |
| Step 4 — Routing (static vs dynamic/BGP) | Route propagation |
| Step 5 — Tunnel options (IKE, encryption, lifetimes, DPD) | Security customization |
| Step 6 — Dual-tunnel redundancy | High availability |
| Step 7 — CloudWatch monitoring | Operational visibility |
| Step 8 — Global Accelerator acceleration | Latency reduction |
| Step 9 — Transit Gateway VPN attachment | Hub-and-spoke topology |
| Step 10 — IPv6 + Outside IP types | Addressing |
| Step 11 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/tunnel-options-and-ike.md | Tunnel/IKE detail |
| references/routing-and-bgp.md | Routing + BGP detail |

## Mindset

**One-line takeaway:** An AWS Site-to-Site VPN connection is a pair of
IPSec tunnels between AWS and a customer gateway device. Each VPN
connection always has TWO tunnels for redundancy, terminating on two
different AWS endpoints. Traffic flows only after BOTH sides configure
routes (static) or establish BGP sessions (dynamic).

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

## Configuration dependency graph (novel heuristic)

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

## Expert heuristic: dual-tunnel active-active vs active-passive

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

## Expert heuristic: BGP vs static route preference

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

## Expert heuristic: IKE lifecycle negotiation caveats

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

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Customer gateway public IP (or NAT IP) | CGW is the peer identity | Confirm on-prem device's outside IP |
| On-prem BGP ASN (if dynamic routing) | Must match the CGW's BGP ASN | `aws ec2 describe-customer-gateways` |
| Target VPC exists (for VPG-attached VPN) | VPG must attach to an existing VPC | `aws ec2 describe-vpcs --vpc-ids <vpc-id>` |
| TGW exists (for TGW-attached VPN) | TGW VPN attachment needs a TGW | `aws ec2 describe-transit-gateways` |
| Route table IDs (for static routing) | Static routes need route tables | `aws ec2 describe-route-tables` |
| Customer device supports IKEv1 or IKEv2 | Must match tunnel options | Check vendor documentation |
| Outside IP type decision (public vs NAT) | Affects CGW IP + NAT-T encapsulation | Determine NAT topology |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`.

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Customer Gateway (CGW)

The Customer Gateway is the AWS-side representation of the on-premises
VPN device. It MUST exist before the VPN connection is created.

```bash
# Customer Gateway with public IP + BGP ASN (dynamic routing)
CGW_ID=$(aws ec2 create-customer-gateway \
  --type ipsec.1 \
  --public-ip 203.0.113.12 \
  --bgp-asn 65000 \
  --region us-east-1 \
  --query 'CustomerGateway.CustomerGatewayId' --output text)

echo "Customer Gateway: $CGW_ID"
```

For a NAT'd on-prem device, use the NAT's public IP and enable UDP
NAT-T encapsulation in tunnel options.

## Step 2 — VPG vs TGW attachment (AWS-side target)

| Target | Use case | Route propagation |
|---|---|---|
| Virtual Private Gateway (VPG) | Single-VPC connectivity | VPC route table propagation (enable-vgw-route-propagation) |
| Transit Gateway (TGW) | Hub-and-spoke, multi-VPC | TGW route table propagation |

**VPG-attached VPN:**

```bash
# Create and attach the VPG
VPG_ID=$(aws ec2 create-vpn-gateway --type ipsec.1 --region us-east-1 \
  --query 'VpnGateway.VpnGatewayId' --output text)

aws ec2 attach-vpn-gateway --vpn-gateway-id "$VPG_ID" \
  --vpc-id vpc-aaa11122 --region us-east-1
```

**TGW-attached VPN:** no separate VPG needed — specify
`--transit-gateway-id` at VPN creation time.

**Decision criteria:**
- 1 VPC, simple connectivity → VPG (cheaper, no TGW hourly)
- Multi-VPC, hub-and-spoke, or transitive routing → TGW
- Share VPN across many VPCs → TGW (VPG is single-VPC only)

## Step 3 — VPN connection (IPSec)

Create the VPN connection with the CGW and AWS-side target.

```bash
# VPG-attached VPN
VPN_ID=$(aws ec2 create-vpn-connection --type ipsec.1 \
  --customer-gateway-id "$CGW_ID" --vpn-gateway-id "$VPG_ID" \
  --region us-east-1 \
  --query 'VpnConnection.VpnConnectionId' --output text)

# TGW-attached VPN (creates a TGW VPN attachment automatically)
VPN_ID=$(aws ec2 create-vpn-connection --type ipsec.1 \
  --customer-gateway-id "$CGW_ID" --transit-gateway-id "$TGW_ID" \
  --region us-east-1 \
  --query 'VpnConnection.VpnConnectionId' --output text)
```

**Download the customer-side configuration** (IPSec parameters for the
on-prem device, vendor-specific):

```bash
aws ec2 describe-vpn-connections --vpn-connection-ids "$VPN_ID" \
  --output text \
  --query 'VpnConnections[0].CustomerGatewayConfiguration' \
  --region us-east-1 > customer-config.xml
```

**Critical:** tunnels stay DOWN until the customer device loads this
configuration and initiates. AWS cannot bring tunnels UP unilaterally.

## Step 4 — Routing (static vs dynamic/BGP)

| Routing | AWS-side action | Customer-side action | Route health |
|---|---|---|---|
| Static | `create-vpn-connection-route` per prefix | Static route per VPC CIDR via tunnel | None — black-hole on tunnel failure |
| Dynamic (BGP) | VPG: enable route propagation; TGW: enable TGW propagation | BGP neighbor config (ASN + AWS-side 169.254.x.x) | Automatic — BGP withdraws on tunnel failure |

**Static route + VPG route propagation:**

```bash
aws ec2 create-vpn-connection-route --vpn-connection-id "$VPN_ID" \
  --destination-cidr-block 10.0.0.0/16 --region us-east-1

aws ec2 enable-vgw-route-propagation --route-table-id rtb-private111 \
  --gateway-id "$VPG_ID" --region us-east-1
```

**BGP:** the CGW's `--bgp-asn` enables BGP. AWS advertises VPC (or
TGW-attached) prefixes to the customer device. The customer device must
advertise on-prem prefixes to AWS for bidirectional routing.

**For production HA, prefer BGP.** BGP detects tunnel failures and
withdraws routes automatically.

## Step 5 — Tunnel options (IKE, encryption, lifetimes, DPD)

Tunnel options are set at VPN-creation time via `--options`. They are
IMMUTABLE after creation — to change them, delete and recreate the VPN.

```bash
VPN_ID=$(aws ec2 create-vpn-connection \
  --type ipsec.1 \
  --customer-gateway-id "$CGW_ID" \
  --transit-gateway-id "$TGW_ID" \
  --options '{"StaticRoutesOnly":false,"TunnelOptions":[
    {"TunnelInsideCidr":"169.254.10.0/30","PreSharedKey":"example-key-1",
     "Phase1EncryptionAlgorithms":["AES256"],"Phase2EncryptionAlgorithms":["AES256"],
     "Phase1IntegrityAlgorithms":["SHA256"],"Phase2IntegrityAlgorithms":["SHA256"],
     "Phase1DHGroupNumbers":[{"Value":17}],"Phase2DHGroupNumbers":[{"Value":17}],
     "Phase1LifetimeSeconds":28800,"Phase2LifetimeSeconds":3600,
     "IKEVersions":[{"Value":"ikev2"}],
     "StartupAction":"start","DPDTimeoutSeconds":30,"DPDRetries":3},
    {"TunnelInsideCidr":"169.254.10.4/30","PreSharedKey":"example-key-2",
     "Phase1EncryptionAlgorithms":["AES256"],"Phase2EncryptionAlgorithms":["AES256"],
     "Phase1IntegrityAlgorithms":["SHA256"],"Phase2IntegrityAlgorithms":["SHA256"],
     "Phase1DHGroupNumbers":[{"Value":17}],"Phase2DHGroupNumbers":[{"Value":17}],
     "Phase1LifetimeSeconds":28800,"Phase2LifetimeSeconds":3600,
     "IKEVersions":[{"Value":"ikev2"}],
     "StartupAction":"start","DPDTimeoutSeconds":30,"DPDRetries":3}
  ]}' \
  --region us-east-1 \
  --query 'VpnConnection.VpnConnectionId' --output text)
```

**Key parameters:** `IKEVersions` (`ikev2` preferred, `ikev1` legacy);
`Phase1EncryptionAlgorithms` (AES-128, AES-256);
`Phase2EncryptionAlgorithms` (AES-128, AES-256, ESP);
`Phase1/2IntegrityAlgorithms` (SHA-1 legacy, SHA-256);
`Phase1/2DHGroupNumbers` (2 legacy, 14-21 modern; Phase 2 = PFS group);
`Phase1LifetimeSeconds` (default 28800 / 8h);
`Phase2LifetimeSeconds` (default 3600 / 1h);
`DPDTimeoutSeconds` and `DPDRetries` (dead peer detection).

**Critical:** both Phase 1 and Phase 2 parameters MUST match on both
sides. A Phase 2 mismatch causes tunnels that come UP but drop at the
first rekey (~1 hour).

## Step 6 — Dual-tunnel redundancy

Every VPN connection has TWO tunnels. For redundancy, BOTH tunnels must
be configured on the customer device.

**Verify both tunnels are UP:**

```bash
aws ec2 describe-vpn-connections --vpn-connection-ids "$VPN_ID" \
  --query 'VpnConnections[0].VgwTelemetry' \
  --region us-east-1 --output table
# Expected: both tunnels show Status "up"
```

| Mode | Tunnel 1 | Tunnel 2 | Failover |
|---|---|---|---|
| Active-passive (static) | primary | standby | Customer device detects failure, switches to tunnel 2 |
| Active-active (BGP ECMP) | ~50% traffic | ~50% traffic | Automatic — BGP withdraws failed tunnel's routes |
| Active-active (priority) | higher priority | lower priority | Automatic via BGP LOCAL_PREF or AS_PATH prepend |

**Redundant VPN connections:** for maximum HA, create TWO VPN
connections to TWO customer gateways (two on-prem devices). Each VPN
has two tunnels — total of 4 tunnels. With BGP, all 4 tunnels can be
active (4-way ECMP) for maximum throughput and redundancy.

## Step 7 — CloudWatch monitoring

Site-to-Site VPN emits CloudWatch metrics per tunnel.

| Metric | What it means | Alert threshold |
|---|---|---|
| `TunnelState` | 1 = UP, 0 = DOWN | Alert if < 1 for > 5 min |
| `TunnelDataIn` | Bytes inbound on the tunnel | Baseline + anomaly |
| `TunnelDataOut` | Bytes outbound on the tunnel | Baseline + anomaly |

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "vpn-${VPN_ID}-tunnel1-down" \
  --metric-name TunnelState --namespace AWS/VPN \
  --dimensions Name=VpnId,Value=$VPN_ID Name=TunnelIpAddress,Value=3.0.0.0 \
  --statistic Minimum --period 60 --evaluation-periods 5 \
  --threshold 1 --comparison-operator LessThanThreshold \
  --alarm-actions "arn:aws:sns:us-east-1:123456789012:vpn-alerts" \
  --region us-east-1
```

**Critical:** if TunnelState shows no data, the tunnel has never come
UP. Verify the customer device has loaded the configuration and the
IPSec parameters match.

## Step 8 — Global Accelerator acceleration

For latency-sensitive workloads, accelerate VPN traffic via AWS Global
Accelerator (routes traffic over the AWS global backbone instead of the
public internet).

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

## Step 9 — Transit Gateway VPN attachment

For hub-and-spoke topologies, attach the VPN to a TGW.

```bash
# VPN with TGW target (attachment created automatically)
VPN_ID=$(aws ec2 create-vpn-connection --type ipsec.1 \
  --customer-gateway-id "$CGW_ID" --transit-gateway-id "$TGW_ID" \
  --region us-east-1 \
  --query 'VpnConnection.VpnConnectionId' --output text)

# Find + associate the TGW VPN attachment
ATTACH_ID=$(aws ec2 describe-transit-gateway-attachments \
  --filters "Name=resource-id,Values=$VPN_ID" \
  --query 'TransitGatewayAttachments[0].TransitGatewayAttachmentId' \
  --output text --region us-east-1)

aws ec2 associate-transit-gateway-route-table \
  --transit-gateway-route-table-id tgw-rtb-aaa111 \
  --transit-gateway-attachment-id "$ATTACH_ID" --region us-east-1
```

**Critical:** TGW VPN attachments propagate routes via TGW route
tables. Enable route propagation on the TGW route table for the VPN
attachment's routes to be visible.

## Step 10 — IPv6 + Outside IP address types

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

## Step 11 — Recent features

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

## NEVER do these things

1. **NEVER assume creating the VPN connection brings tunnels UP.**
   Tunnels stay DOWN until the customer device loads the configuration
   and initiates. AWS cannot bring tunnels UP unilaterally. Verify
   tunnel state via CloudWatch TunnelState after customer-side
   configuration.

2. **NEVER configure only one tunnel and claim redundancy.** AWS
   provisions two tunnels per VPN connection, but redundancy only
   exists if BOTH are configured on the customer device. The #1
   redundancy failure is "I created the VPN but only configured
   tunnel 1."

3. **NEVER use static routing for production HA without DPD.** Static
   routes have NO route health detection — a tunnel failure black-holes
   traffic until the customer device detects it. For production HA, use
   BGP (automatic withdrawal) or static + DPD with failover.

4. **NEVER try to modify tunnel options after creation.** Tunnel
   options (IKE, encryption, lifetimes, DPD) are IMMUTABLE after VPN
   creation. To change them, delete and recreate the VPN connection.
   Decide tunnel options BEFORE creating the VPN.

5. **NEVER mismatch Phase 1 or Phase 2 parameters.** A Phase 1
   mismatch means the tunnel never establishes. A Phase 2 mismatch
   means the tunnel comes UP but drops at the first rekey (~1 hour).
   Verify BOTH Phase 1 AND Phase 2 match on both sides.

6. **NEVER forget to enable VPG route propagation.** For VPG-attached
   VPNs, route propagation to the VPC route table is NOT automatic.
   Call `enable-vgw-route-propagation` for each route table that
   should receive VPN routes. Without it, traffic from the VPC never
   reaches the VPN.

7. **NEVER use a NAT'd on-prem device without UDP NAT-T.** If the
   on-prem device is behind a NAT, the CGW's public IP is the NAT's
   public IP, and UDP NAT-T encapsulation must be enabled in tunnel
   options. Without NAT-T, IPSec ESP packets are dropped by the NAT.

8. **NEVER assume Global Accelerator can be added post-creation.**
   Acceleration (`Accelerate:true`) can ONLY be set at VPN creation
   time. To accelerate an existing VPN, create a NEW accelerated VPN
   and migrate traffic.

9. **NEVER mix BGP and static routing on the same tunnel.** Mixing
   routing types on the same tunnel causes unpredictable route
   preference. Use BGP on both tunnels, or static on both tunnels.

10. **NEVER assume a TGW VPN attachment propagates routes automatically.**
    TGW-attached VPNs propagate via TGW route tables, which must be
    explicitly configured. Associate the attachment with a TGW route
    table and enable route propagation on that table.

## Output format

```text
VPN_CONNECTION: <vpn-id> — CGW <cgw-id> → <VPG-id|TGW-id>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Customer Gateway: <cgw-id> (<public-ip>, BGP ASN <asn>)
  [✓|✗] AWS-side target: VPG <vpg-id> (attached to <vpc-id>) | TGW <tgw-id>
  [✓|✗] VPN connection: <vpn-id> — two IPSec tunnels
  [✓|✗] Routing: Static (routes added) | Dynamic BGP (ASN <aws-asn> ↔ <customer-asn>)
  [✓|✗] Tunnel 1: <outside-ip> — inside CIDR <169.254.x.x/30> — IKEv<1|2>
  [✓|✗] Tunnel 2: <outside-ip> — inside CIDR <169.254.x.x/30> — IKEv<1|2>
  [✓|✗] Phase 1: <encryption> / <integrity> / DH group <n> / lifetime <s>
  [✓|✗] Phase 2: <encryption> / <integrity> / PFS group <n> / lifetime <s>
  [✓|✗] DPD: timeout <s>, retries <n>
  [✓|✗] Redundancy: active-passive | active-active (BGP ECMP)
  [✓|✗] Route propagation: VPG route propagation enabled | TGW route table <tgw-rtb-id>
  [✓|✗] CloudWatch: TunnelState alarm on <sns-arn>
  [✓|✗] Acceleration: Global Accelerator enabled | Disabled
  [✓|✗] IPv6: enabled (routes added) | IPv4 only
  [✓|✗] Outside IP: public (<ip>) | private NAT (<nat-ip>)
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws ec2 describe-vpn-connections --vpn-connection-ids <vpn-id> --region <region>
  aws cloudwatch get-metric-statistics --namespace AWS/VPN --metric-name TunnelState --dimensions Name=VpnId,Value=<vpn-id> --start-time <iso> --end-time <iso> --period 60 --statistics Minimum --region <region>
```

### Worked example — TGW-attached VPN with BGP and IKEv2

```text
VPN_CONNECTION: vpn-111222333 — CGW cgw-aaa111 → TGW tgw-000111222333
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Customer Gateway: cgw-aaa111 (203.0.113.12, BGP ASN 65000)
  [✓] AWS-side target: TGW tgw-000111222333
  [✓] VPN connection: vpn-111222333 — two IPSec tunnels
  [✓] Routing: Dynamic BGP (ASN 64512 ↔ 65000)
  [✓] Tunnel 1: 3.221.215.181 — inside CIDR 169.254.10.0/30 — IKEv2
  [✓] Tunnel 2: 3.221.215.204 — inside CIDR 169.254.10.4/30 — IKEv2
  [✓] Phase 1: AES256 / SHA256 / DH group 17 / lifetime 28800s
  [✓] Phase 2: AES256 / SHA256 / PFS group 17 / lifetime 3600s
  [✓] DPD: timeout 30s, retries 3
  [✓] Redundancy: active-active (BGP ECMP)
  [✓] Route propagation: TGW route table tgw-rtb-aaa111
  [✓] CloudWatch: TunnelState alarm on arn:aws:sns:us-east-1:123456789012:vpn-alerts
  [✓] Acceleration: Disabled
  [✓] IPv6: IPv4 only
  [✓] Outside IP: public (203.0.113.12)
  [✓] Tags: Environment=production, Topology=onprem-to-tgw
VERIFICATION_COMMANDS:
  aws ec2 describe-vpn-connections --vpn-connection-ids vpn-111222333 --region us-east-1
  aws cloudwatch get-metric-statistics --namespace AWS/VPN --metric-name TunnelState --dimensions Name=VpnId,Value=vpn-111222333 --start-time 2026-08-11T00:00:00Z --end-time 2026-08-11T00:10:00Z --period 60 --statistics Minimum --region us-east-1
```

## Error handling

### Tunnels stuck DOWN
- The customer device has not loaded the configuration or has not
  initiated. Verify the configuration XML loaded (from
  `describe-vpn-connections --query CustomerGatewayConfiguration`).
  Check IPSec parameters (IKE, encryption, PSK) match on both sides.
  For NAT'd devices, verify UDP NAT-T is enabled and the NAT allows
  UDP 500/4500.

### Tunnels UP but no traffic flows
- Routes are missing on one side. Static: verify
  `create-vpn-connection-route` was called per prefix. BGP: verify the
  BGP session is established. VPG-attached: verify
  `enable-vgw-route-propagation`. TGW-attached: verify the attachment
  is associated with a TGW route table with propagation enabled.

### Tunnels come UP but drop after ~1 hour
- Phase 2 SA lifetime or parameter mismatch. Phase 2 rekey happens at
  the lifetime boundary (~3600s). If Phase 2 parameters do not match,
  the tunnel drops at the first rekey. Verify Phase 2 parameters.

### BGP session never establishes
- BGP ASN mismatch, or BGP neighbors are not configured. Verify the
  CGW's `--bgp-asn` matches the on-prem device's BGP ASN. Verify the
  on-prem device has a BGP neighbor configured with the AWS-side inside
  IP (169.254.x.x).

### Route not propagating to TGW
- The TGW VPN attachment is not associated with a TGW route table, or
  propagation is not enabled. Call
  `associate-transit-gateway-route-table` and verify the route table
  has propagation enabled for the VPN attachment.

## Domain

AWS CloudOps / Amazon Site-to-Site VPN Provisioning & Hybrid Network
Connectivity.

## AWS documentation

- **Site-to-Site VPN Guide** — https://docs.aws.amazon.com/vpn/latest/s2svpn/VPC_VPN.html
- **Customer Gateway / VPG / VPN connection** — https://docs.aws.amazon.com/vpn/latest/s2svpn/SetUpVPNConnections.html
- **Tunnel options** — https://docs.aws.amazon.com/vpn/latest/s2svpn/VPNTunnels.html
- **Routing (static vs BGP)** — https://docs.aws.amazon.com/vpn/latest/s2svpn/VPNRoutingTypes.html
- **Transit Gateway VPN attachment** — https://docs.aws.amazon.com/vpc/latest/tgw/tgw-vpn-attachments.html
- **Global Accelerator for VPN** — https://docs.aws.amazon.com/global-accelerator/latest/dg/about-accelerators.html
- **CloudWatch VPN metrics** — https://docs.aws.amazon.com/vpn/latest/s2svpn/monitoring-cloudwatch-vpn.html
- **IPv6 in VPN** — https://docs.aws.amazon.com/vpn/latest/s2svpn/ipv6-support.html
