# Cross-Account, Connect, and Cloud WAN Reference

Supplementary reference for the Transit Gateway Deployer skill. Use
when designing RAM shares, cross-account VPC attachments, Connect
attachments for SD-WAN, multicast domains, or AWS Cloud WAN
integration.

## RAM share lifecycle

```
Owner account                            Consumer account
─────────────                            ─────────────────
1. create-resource-share
   (resource-arns = TGW ARN,
    principals = consumer acct)
                ─── invitation ────>
                                         2. accept-resource-share-invitation
                                            (state = ACTIVE)
                                         3. create-transit-gateway-vpc-attachment
                                            (transit-gateway-id = shared TGW,
                                             vpc-id = consumer VPC,
                                             subnet-ids = consumer subnets)
                <── attachment create ─
4. (if AutoAcceptSharedAttachments=disable)
   accept-transit-gateway-vpc-attachment
   (state = available)
```

If `AutoAcceptSharedAttachments=enable`, step 4 is automatic. For
production, use `disable` — explicit owner approval is a security
control.

Verify share state from either account:

```bash
aws ram get-resource-shares --resource-arns <tgw-arn>
aws ram get-resource-share-invitations --resource-share-arns <share-arn>
```

## Connect attachment architecture

```
┌────────────────────────────────────────────────────────────────┐
│  AWS TGW                                                       │
│                                                                │
│  ┌────────────────────────┐    ┌──────────────────────────┐   │
│  │  VPC attachment        │    │  Connect attachment      │   │
│  │  (transport)           ├───>│  (Protocol=GRE)          │   │
│  │  vpc-0sdwan-transit    │    │                          │   │
│  └────────────────────────┘    └────────┬─────────────────┘   │
│                                         │                      │
│                                ┌────────▼─────────────────┐   │
│                                │  Connect peer            │   │
│                                │  PeerAddress=10.0.1.10   │   │
│                                │  PeerAsn=65000           │   │
│                                │  InsideCidr=169.254.0/29 │   │
│                                └────────┬─────────────────┘   │
└─────────────────────────────────────────┼──────────────────────┘
                                          │ GRE tunnel
                            ┌─────────────▼─────────────┐
                            │  SD-WAN controller        │
                            │  (Cisco/Fortinet/Velocloud)│
                            │  in VPC vpc-0sdwan-transit │
                            └─────────────┬─────────────┘
                                          │ BGP
                            ┌─────────────▼─────────────┐
                            │  On-prem branch networks  │
                            └───────────────────────────┘
```

| Layer | What it carries |
|---|---|
| VPC attachment (transport) | IP reachability between TGW and VPC where SD-WAN lives |
| Connect attachment | GRE tunnel between TGW and Connect peer |
| Connect peer (BGP) | Route exchange between TGW and SD-WAN |
| SD-WAN overlay | Encrypted/segmented transport to branch networks |

The Connect attachment does NOT encrypt. The SD-WAN controller
handles its own encryption (DMVPN, IPsec, etc.). For internet-based
transport, use a Site-to-Site VPN attachment as the transport for
the Connect attachment.

## Connect peer BGP details

| Field | Range | Notes |
|---|---|---|
| PeerAsn | 64512-65535 (or 4-byte private) | Must differ from TGW's AmazonSideAsn. |
| PeerAddress | Private IP | Reachable via the transport attachment's VPC. |
| InsideCidr | /29 minimum | Used for BGP peering. 169.254.x.y typical. |
| BgpAuthenticationKey | (optional, 2024) | MD5 auth for BGP session. |
| Protocol | `gre` | Only GRE supported. |

Up to 4 Connect peers per Connect attachment (hard limit). For
redundancy, deploy 2 Connect peers per SD-WAN controller across
different AZs.

## Multicast domain topology

```
TGW (MulticastSupport=enable)
  └─ Multicast domain: video-broadcast
       ├─ Static sources: 10.1.5.10 (encoder in vpc-producer)
       └─ Group members:
            ├─ subnet-0a1 in vpc-consumer1
            ├─ subnet-0b1 in vpc-consumer1
            └─ subnet-0a2 in vpc-consumer2
```

| Field | Effect |
|---|---|
| Igmpv2Support=enable | Members use IGMPv2 to join/leave groups dynamically |
| StaticSourcesSupport=enable | Manual source configuration via CLI/console |
| NetworkInterfaceType | `interface` (member) or `transitGateway` (source) |

Constraints:
- All members must be in subnets attached to TGW VPC attachments
  in the SAME TGW as the multicast domain.
- One subnet per VPC attachment can participate in a multicast
  domain.
- Cross-region multicast not supported.

## Network Manager global network

```bash
aws networkmanager create-global-network --description "corp-global"
aws networkmanager register-transit-gateway \
  --global-network-id global-network-0abc \
  --transit-gateway-arn arn:aws:ec2:us-east-1:111111111111:transit-gateway/tgw-0abc
```

Network Manager pulls topology metadata from registered TGWs:

- All VPC attachments, peering attachments, Connect attachments.
- Route tables and their associations/propagations.
- Cross-account attachments (requires RAM share of the global
  network to the consumer account).
- On-premises devices (registered via the Network Manager agent).

Visualization shows the live topology in the AWS console. Useful
for audit, troubleshooting, and on-call.

## AWS Cloud WAN core network

Cloud WAN sits ABOVE TGWs as a policy-driven global network layer.

| Cloud WAN concept | Maps to TGW concept |
|---|---|
| Core network | Logical container; attaches to TGWs |
| Segment | Routing isolation tier (e.g., prod, non-prod) |
| Segment action | Allow/deny routing between segments |
| Core network edge | Regional TGW |
| Core network attachment | TGW attachment to a VPC or existing resource |

Policy example (YAML, edited in console):

```yaml
version: 2021.12
segments:
  - name: prod
    require-acceptance-attachment: false
  - name: non-prod
    require-acceptance-attachment: false
segment-actions:
  - action: send-receive
    segment: prod
    share-with: [non-prod]   # bi-directional
attachment-policies:
  - rule-number: 1
    conditions:
      - type: tag-key
        operator: equals
        value: segment
    action:
      association:
        segment: ${tag:segment-value}
```

Existing TGWs attach non-disruptively. Cutover by re-associating
attachments from the original route tables to the Cloud WAN-managed
ones. Cloud WAN will overwrite manual route table changes on the
next policy application — declare route topology in the policy.

## IAM permissions cheat sheet

| Operation | Permissions |
|---|---|
| Create TGW | `ec2:CreateTransitGateway`, `CreateTags` |
| Create VPC attachment | `ec2:CreateTransitGatewayVpcAttachment`, `CreateTags` |
| Create route table | `ec2:CreateTransitGatewayRouteTable`, `CreateTags` |
| Associate / propagate | `ec2:AssociateTransitGatewayRouteTable`, `EnableTransitGatewayRouteTablePropagation` |
| Static route | `ec2:CreateTransitGatewayRoute` |
| Peering | `ec2:CreateTransitGatewayPeeringAttachment`, `AcceptTransitGatewayPeeringAttachment` |
| Connect | `ec2:CreateTransitGatewayConnect`, `CreateTransitGatewayConnectPeer` |
| Multicast | `ec2:CreateTransitGatewayMulticastDomain`, `AssociateTransitGatewayMulticastDomain` |
| RAM share | `ram:CreateResourceShare`, `AssociateResourceShare` |
| Network Manager | `networkmanager:CreateGlobalNetwork`, `RegisterTransitGateway` |
| Cloud WAN | `networkmanager:CreateCoreNetwork`, `CreateAttachment` |
