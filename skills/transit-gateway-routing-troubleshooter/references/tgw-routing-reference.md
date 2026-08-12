# TGW Routing Reference Guide

Supplementary reference for the Transit Gateway Routing Troubleshooter
skill. Loaded on-demand when a diagnostic needs route table priority
rules, attachment-type route learning, command syntax, or the
overlapping-CIDR truth table.

## TGW route table priority

TGW route tables use longest-prefix match; for equal prefix length,
static routes beat propagated routes. There is no multipath across
attachments for the same CIDR.

| Type | Prefix | Tie-break | Behaviour |
|---|---|---|---|
| Static | /16 | Beats propagated /16 | Always wins for equal prefix length |
| Propagated | /16 | Loses to static /16 | Shadowed when a static route exists for the same CIDR |
| Static | /24 | Beats static /16 (longer prefix) | Longer prefix always wins |
| Propagated | /24 | Beats static /16 (longer prefix) | Longer prefix always wins |
| Propagated (two attachments, same /16) | /16 | Arbitrary | TGW does not multipath; picks one |

### Search commands

```bash
# All active routes (the forwarding table the TGW uses)
aws ec2 search-transit-gateway-routes \
  --transit-gateway-route-table-id <rtb-id> \
  --filters Name=state,Values=active --output json

# Only static routes (to find overrides)
aws ec2 search-transit-gateway-routes \
  --transit-gateway-route-table-id <rtb-id> \
  --filters Name=type,Values=static --output json

# Only propagated routes (to verify propagation is working)
aws ec2 search-transit-gateway-routes \
  --transit-gateway-route-table-id <rtb-id> \
  --filters Name=type,Values=propagated --output json
```

### Route table operations

```bash
# Create a static route
aws ec2 create-transit-gateway-route \
  --transit-gateway-route-table-id <rtb-id> \
  --destination-cidr-block 10.50.0.0/16 \
  --transit-gateway-attachment-id <attach-id>

# Delete a static route (so the propagated route takes over)
aws ec2 delete-transit-gateway-route \
  --transit-gateway-route-table-id <rtb-id> \
  --destination-cidr-block 10.50.0.0/16

# Associate an attachment with a route table
aws ec2 associate-transit-gateway-route-table \
  --transit-gateway-route-table-id <rtb-id> \
  --transit-gateway-attachment-id <attach-id>

# Enable propagation of an attachment into a route table
aws ec2 enable-transit-gateway-route-table-propagation \
  --transit-gateway-route-table-id <rtb-id> \
  --transit-gateway-attachment-id <attach-id>

# List associations and propagations
aws ec2 get-transit-gateway-route-table-associations \
  --transit-gateway-route-table-id <rtb-id> --output json

aws ec2 get-transit-gateway-route-table-propagations \
  --transit-gateway-route-table-id <rtb-id> --output json
```

## Attachment types and route learning

| Type | Routes learned by TGW? | Notes |
|---|---|---|
| VPC | Yes — VPC's CIDR(s) | One CIDR per VPC by default; secondary CIDRs propagate if attached |
| VPN (dynamic, BGP) | Yes — advertised prefixes via BGP | Static VPN requires a manual static TGW route |
| VPN (static) | No — must add a static TGW route | Use `create-transit-gateway-route` |
| Direct Connect gateway | Yes — via DX gateway association | Allowed-prefixes list controls what is learned |
| Peering (another TGW) | Yes — peer TGW's attachment CIDRs | Non-transitive; each pair needs a direct peering |
| Connect (GRE-based) | Yes — BGP over GRE | Used for SD-WAN appliances |

## VPC route table pointing at TGW

For traffic to leave a VPC toward the TGW, the VPC's route table must
have a route for the destination CIDR pointing at the TGW:

```bash
aws ec2 create-route \
  --route-table-id <vpc-rtb-id> \
  --destination-cidr-block 10.20.0.0/16 \
  --transit-gateway-id tgw-aaa
```

### Default route 0.0.0.0/0 to TGW

A default route `0.0.0.0/0 → tgw-aaa` is valid ONLY in a centralized-
egress design where a dedicated egress VPC owns the IGW / NAT
Gateways. In any other topology, the default route to the TGW
blackholes internet-bound traffic.

```bash
# Check the default route in a VPC route table
aws ec2 describe-route-tables \
  --filters Name=vpc-id,Values=<vpc-id> --output json | \
  jq '.RouteTables[].Routes[] | select(.DestinationCidrBlock=="0.0.0.0/0")'
```

If `GatewayId` starts with `igw-`, this is correct for an internet-
facing VPC. If it points at a `TransitGatewayId`, verify the
centralized-egress design.

## Overlapping CIDR truth table

| VPC-A CIDR | VPC-B CIDR | Overlap? | TGW behaviour |
|---|---|---|---|
| 10.0.0.0/16 | 10.20.0.0/16 | No | Routes independently; no conflict |
| 10.0.0.0/16 | 10.0.0.0/16 | Exact | TGW cannot route to both; one attachment's route is arbitrary |
| 10.0.0.0/16 | 10.0.1.0/24 | Overlapping subnet | Longest-prefix match: 10.0.1.0/24 wins; 10.0.0.0/16 shadowed for the /24 portion |
| 10.0.0.0/16 | 172.16.0.0/16 | No | Routes independently |
| 10.0.0.0/8 | 10.1.0.0/16 | Overlapping subnet | Longest-prefix match: 10.1.0.0/16 wins |

There is no NAT-on-TGW to translate around the overlap. The only fix
is to re-CIDR one of the VPCs.

## VPN and Direct Connect routing

### VPN attachments

```bash
# List VPN attachments on the TGW
aws ec2 describe-transit-gateway-attachments \
  --filters Name=resource-type,Values=vpn \
  --filters Name=transit-gateway-id,Values=<tgw-id> --output json

# Check the customer gateway and BGP status
aws ec2 describe-customer-gateways --output json
aws ec2 describe-vpn-connections --output json
```

For dynamic (BGP) VPNs, the on-prem routes are advertised into the
TGW automatically. For static VPNs, add a static TGW route:

```bash
aws ec2 create-transit-gateway-route \
  --transit-gateway-route-table-id <rtb-id> \
  --destination-cidr-block 10.99.0.0/16 \
  --transit-gateway-attachment-id <vpn-attach-id>
```

### Direct Connect gateway associations

```bash
aws directconnect describe-direct-connect-gateways --output json
aws directconnect describe-direct-connect-gateway-associations --output json
```

The DX gateway sits between the on-prem router and the TGW. The
association's `AllowedPrefixes` controls what on-prem CIDRs are
propagated into the TGW. If the target CIDR is excluded, traffic
cannot reach it.

## Peering attachments (cross-TGW)

```bash
# Create a peering request
aws ec2 create-transit-gateway-peering-attachment \
  --transit-gateway-id <local-tgw> \
  --peer-transit-gateway-id <remote-tgw> \
  --peer-region <remote-region>

# Accept a peering (on the peer TGW's account/region)
aws ec2 accept-transit-gateway-peering-attachment \
  --transit-gateway-peering-attachment-id <peering-id>

# List peering attachments
aws ec2 describe-transit-gateway-peering-attachments \
  --filters Name=transit-gateway-id,Values=<tgw-id> --output json
```

Peering states: `initiatingRequest`, `pending-acceptance`, `active`,
`available`, `failed`, `deleting`, `deleted`, `rejected`,
`rejecting`, `failing`.

Only `available` carries traffic. The peer TGW's owner must accept
the peering; cross-account and cross-region peerings take minutes.

## Flow logs

```bash
# Create a TGW flow log
aws ec2 create-flow-logs \
  --resource-type transit-gateway \
  --resource-id <tgw-id> \
  --log-group-name <cw-log-group> \
  --deliver-logs-permission-arn <iam-role-arn> \
  --traffic-type ALL

# Describe existing flow logs
aws ec2 describe-flow-logs \
  --filter Name=resource-type,Values=transit-gateway \
  --filter Name=resource-id,Values=<tgw-id> --output json
```

The IAM role for the flow log needs `logs:CreateLogStream`,
`logs:PutLogEvents`, and `logs:DescribeLogGroups` on the destination
log group. The destination CloudWatch Logs group must exist before
creating the flow log.

TGW flow logs show the TGW's view of the flow. A flow that enters the
TGW and is blackholed appears as `ACCEPT` ingress with no
corresponding egress. Correlate VPC flow logs on both the source and
destination sides for end-to-end debugging.

## DNS resolution across TGW attachments

```bash
# Check VPC DNS attributes
aws ec2 describe-vpc-attribute --vpc-id <vpc-id> --attribute enableDnsSupport --output json
aws ec2 describe-vpc-attribute --vpc-id <vpc-id> --attribute enableDnsHostnames --output json

# List Route 53 Resolver endpoints and rules
aws route53resolver list-resolver-endpoints --output json
aws route53resolver list-resolver-rules --output json
```

For cross-VPC DNS resolution:
1. Both VPCs need `enableDnsSupport: true` and `enableDnsHostnames:
   true`.
2. Deploy Route 53 Resolver inbound endpoints in the destination VPC
   (the VPC whose hostnames you want to resolve).
3. Deploy Route 53 Resolver outbound endpoints in the source VPC.
4. Create a forwarding rule that directs queries for the destination
   VPC's domain to the inbound endpoint IPs.
5. Share the forwarding rule with the source VPC (or associate it).

## Multicast domain

```bash
# List multicast domains on the TGW
aws ec2 describe-transit-gateway-multicast-domains \
  --transit-gateway-id <tgw-id> --output json

# Search multicast groups (members and sources)
aws ec2 search-transit-gateway-multicast-groups \
  --transit-gateway-multicast-domain-id <domain-id> --output json | \
  jq '.MulticastGroups[] | {GroupIpAddress, NetworkInterfaceId, GroupMember, GroupSource}'

# Add a receiver ENI to a multicast group
aws ec2 register-transit-gateway-multicast-group-members \
  --transit-gateway-multicast-domain-id <domain-id> \
  --network-interface-ids <eni-id> \
  --group-ip-address 224.0.1.1
```

Constraints:
- One multicast domain per TGW (within a region).
- IGMP is not supported; members are statically registered by ENI.
- The TGW does not route multicast between TGWs (peering does not
  carry multicast).
- Sources are Network Load Balancers or instances with
  `AWSSupportsMulticast=true`.

## AWS Health event categories that affect TGW

| Category | Likely impact |
|---|---|
| `AWS_TRANSITGATEWAY_SERVICE` | Region-wide TGW degradation; multiple attachments fail simultaneously |
| `AWS_VPN_SERVICE` | VPN attachments drop tunnels; BGP routes withdraw |
| `AWS_DIRECTCONNECT_SERVICE` | DX gateway associations lose routes |
| `AWS_REGIONAL_EVENT` | Multiple services affected; broad customer impact |

Always probe `aws health describe-events` for regional issues before
declaring a customer-side root cause during a wide-impact incident.
