# Diagnostic commands — transit-gateway-routing-troubleshooter

Moved verbatim from SKILL.md for progressive disclosure. Load on demand.

### Pre-flight commands

```bash
# TGW and its route tables
aws ec2 describe-transit-gateways --transit-gateway-ids <tgw-id> --output json
aws ec2 describe-transit-gateway-route-tables \
  --filters Name=transit-gateway-id,Values=<tgw-id> --output json

# All attachments (VPC, VPN, Peering, Connect, Direct Connect gateway)
aws ec2 describe-transit-gateway-attachments \
  --filters Name=transit-gateway-id,Values=<tgw-id> --output json

# Association and propagation per route table
aws ec2 get-transit-gateway-route-table-associations \
  --transit-gateway-route-table-id <rtb-id> --output json
aws ec2 get-transit-gateway-route-table-propagations \
  --transit-gateway-route-table-id <rtb-id> --output json

# Search the actual routes the TGW will use
aws ec2 search-transit-gateway-routes \
  --transit-gateway-route-table-id <rtb-id> \
  --filters Name=state,Values=active --output json

# Flow logs on the TGW
aws ec2 describe-flow-logs \
  --filter Name=resource-type,Values=transit-gateway --output json
```
## Per-step probe commands

#### 2a: Source attachment's associated route table

```bash
aws ec2 describe-transit-gateway-attachments \
  --filters Name=transit-gateway-attachment-id,Values=<source-attach-id> \
  --output json | jq '.TransitGatewayAttachments[].Association.TransitGatewayRouteTableId'
```
#### 2b: Destination CIDR in the associated route table

```bash
aws ec2 search-transit-gateway-routes \
  --transit-gateway-route-table-id <source-rtb-id> \
  --filters Name=type,Values=propagated,static --output json | \
  jq '.Routes[] | select(.DestinationCidrBlock | startswith("<dest-cidr-prefix>"))'
```
#### 2c: Return path (destination → source)

```bash
aws ec2 describe-route-tables \
  --filters Name=vpc-id,Values=<dest-vpc-id> --output json | \
  jq '.RouteTables[].Routes[] | select(.DestinationCidrBlock | startswith("<source-cidr-prefix>"))'
```
#### 2d: Default route 0.0.0.0/0 pointing at TGW

```bash
aws ec2 describe-route-tables \
  --filters Name=vpc-id,Values=<vpc-id> --output json | \
  jq '.RouteTables[].Routes[] | select(.DestinationCidrBlock=="0.0.0.0/0")'
```
#### 3a: Static routes overriding propagated

```bash
aws ec2 search-transit-gateway-routes \
  --transit-gateway-route-table-id <rtb-id> \
  --filters Name=type,Values=static --output json | \
  jq '.Routes[] | select(.DestinationCidrBlock | startswith("<dest-cidr-prefix>"))'
```
#### 3b: Overlapping CIDR

```bash
aws ec2 describe-vpcs --vpc-ids <vpc-a-id> <vpc-b-id> --output json | \
  jq '.Vpcs[] | {VpcId, CidrBlock, CidrBlockAssociationSet}'
```
#### 4a: Peering attachment state

```bash
aws ec2 describe-transit-gateway-peering-attachments \
  --filters Name=transit-gateway-id,Values=<tgw-a-id> --output json | \
  jq '.TransitGatewayPeeringAttachments[] | {TransitGatewayPeeringAttachmentId, State, AccepterTgwInfo, RequesterTgwInfo}'
```
#### 4b: Route tables on BOTH TGWs

```bash
aws ec2 search-transit-gateway-routes \
  --transit-gateway-route-table-id <local-rtb> \
  --filters Name=type,Values=propagated,static --output json | \
  jq '.Routes[] | select(.TransitGatewayAttachments[].TransitGatewayAttachmentId=="<peering-attach-id>")'
```
### Step 5: Appliance mode

```bash
aws ec2 describe-transit-gateway-attachments \
  --transit-gateway-attachment-ids <inspection-vpc-attachment-id> --output json | \
  jq '.TransitGatewayAttachments[].Options.ApplianceModeSupport'
```
#### 6a: On-prem CIDR in the TGW route table

```bash
aws ec2 search-transit-gateway-routes \
  --transit-gateway-route-table-id <rtb-id> \
  --filters Name=type,Values=propagated,static --output json | \
  jq '.Routes[] | select(.DestinationCidrBlock | startswith("<onprem-cidr-prefix>"))'
```
#### 6b: VPN attachment's association

```bash
aws ec2 describe-transit-gateway-attachments \
  --filters Name=resource-type,Values=vpn \
  --filters Name=transit-gateway-id,Values=<tgw-id> --output json | \
  jq '.TransitGatewayAttachments[] | {TransitGatewayAttachmentId, Association, State}'
```
#### 6c: DX gateway association

```bash
aws directconnect describe-direct-connect-gateways --output json
aws directconnect describe-direct-connect-gateway-associations --output json
```
### Step 7: Multicast domain

```bash
aws ec2 describe-transit-gateway-multicast-domains \
  --transit-gateway-id <tgw-id> --output json

aws ec2 search-transit-gateway-multicast-groups \
  --transit-gateway-multicast-domain-id <domain-id> --output json | \
  jq '.MulticastGroups[] | {GroupIpAddress, NetworkInterfaceId, GroupMember}'
```
### Step 8: DNS resolution across TGW attachments

```bash
aws ec2 describe-vpc-attribute --vpc-id <vpc-id> --attribute enableDnsSupport --output json
aws ec2 describe-vpc-attribute --vpc-id <vpc-id> --attribute enableDnsHostnames --output json
aws route53resolver list-resolver-endpoints --output json
aws route53resolver list-resolver-rules --output json
```
### Step 8b: TGW flow logs

```bash
aws ec2 describe-flow-logs \
  --filter Name=resource-type,Values=transit-gateway \
  --filter Name=resource-id,Values=<tgw-id> --output json
```
### Step 8c: Cross-VPC security group references

```bash
aws ec2 describe-security-groups \
  --filters Name=vpc-id,Values=<vpc-a-id> --output json | \
  jq '.SecurityGroups[].IpPermissions[] | .UserIdGroupPairs[]?'
```
## Remediation guidance (command index)

- **TGW_ROUTE_TABLE_ASSOCIATION**: `associate-transit-gateway-route-table`
- **TGW_ROUTE_TABLE_PROPAGATION**: `enable-transit-gateway-route-table-propagation`
- **TGW_STATIC_ROUTE_PRIORITY**: `delete-transit-gateway-route` (stale static)
- **TGW_OVERLAPPING_CIDR**: re-CIDR one VPC (no NAT-on-TGW)
- **TGW_PEERING_NON_TRANSITIVE**: `create-transit-gateway-peering-attachment` (direct peering)
- **TGW_VPN_DX_ROUTING**: verify BGP / DX gateway association / allowed prefixes
- **TGW_MULTICAST_DOMAIN**: `register-transit-gateway-multicast-group-members`
- **VPC_DEFAULT_ROUTE_TGW**: `create-route --transit-gateway-id` (return path)
- **TGW_APPLIANCE_MODE**: `modify-transit-gateway-attachment --options ApplianceModeSupport=enable`
- **TGW_DNS_RESOLUTION**: Route 53 Resolver inbound + outbound endpoints + forwarding rule
- **TGW_FLOW_LOGS**: `create-flow-logs --resource-type transit-gateway`
- **TGW_SG_CROSS_VPC**: replace cross-VPC SG ref with CIDR / prefix list (`authorize-security-group-ingress --ip-ranges`)
