# Worked examples — transit-gateway-deployer

Moved verbatim from SKILL.md for progressive disclosure. Load on demand.

### Step 1: TGW creation — ASN, DNS, multicast, defaults

```bash
aws ec2 create-transit-gateway \
  --description "prod-tgw-us-east-1" \
  --options AmazonSideAsn=64512,AutoAcceptSharedAttachments=disable,DefaultRouteTableAssociation=enable,DefaultRouteTablePropagation=enable,VpnEcmpSupport=enable,DnsSupport=enable,MulticastSupport=disable \
  --tag-specifications "ResourceType=transit-gateway,Tags=[{Key=Name,Value=prod-tgw-us-east-1}]"
```
### Step 2: VPC attachments — subnets, AZ scope, appliance mode

```bash
aws ec2 create-transit-gateway-vpc-attachment \
  --transit-gateway-id tgw-0abc123 \
  --vpc-id vpc-0abc123 \
  --subnet-ids subnet-0a1 subnet-0b1 subnet-0c1 \
  --options ApplianceModeSupport=disable,DnsSupport=enable,Ipv6Support=disable \
  --tag-specifications "ResourceType=transit-gateway-attachment,Tags=[{Key=Name,Value=prod-vpc-app1-tgw}]"
```
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
### Step 4: Peering connections — inter-region and intra-region

```bash
# Request peering (in source TGW owner account, source region)
aws ec2 create-transit-gateway-peering-attachment --transit-gateway-id tgw-0source \
  --peer-transit-gateway-id tgw-0peer --peer-region eu-west-1 --peer-account-id 111111111111 \
  --tag-specifications "ResourceType=transit-gateway-peering-attachment,Tags=[{Key=Name,Value=us-east-1-to-eu-west-1}]"

# Accept peering (in peer TGW owner account, peer region)
aws ec2 accept-transit-gateway-peering-attachment --transit-gateway-peering-attachment-id tgw-attach-0peer --region eu-west-1
```
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
