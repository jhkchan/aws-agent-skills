# TGW Attachment and Appliance Mode Reference

Supplementary reference for the Transit Gateway Routing Troubleshooter
skill. Loaded on-demand when a diagnostic needs attachment state
detail, appliance-mode behaviour, subnet/AZ placement, or security
group cross-VPC constraints.

## Attachment states and their effect on routing

| State | Effect |
|---|---|
| `available` | Attachment is up; carries traffic normally. |
| `pending` / `modifying` | A change is in flight (new VPC, peering request, appliance-mode toggle). Routing may be unstable; wait for `available`. |
| `failing` / `failed` | The attachment failed to establish. Common for peering where the peer rejected, or VPN where tunnels are down. |
| `deleting` / `deleted` | The attachment is gone; traffic to its CIDR blackholes. |
| `rejecting` / `rejected` (peering) | Peer TGW rejected the peering; no traffic will ever flow. Re-establish peering. |

```bash
# All attachments on a TGW with state
aws ec2 describe-transit-gateway-attachments \
  --filters Name=transit-gateway-id,Values=<tgw-id> --output json | \
  jq '.TransitGatewayAttachments[] | {TransitGatewayAttachmentId, ResourceType, State, SubnetIds, Options}'

# Single attachment detail
aws ec2 describe-transit-gateway-attachments \
  --transit-gateway-attachment-ids <attach-id> --output json | \
  jq '.TransitGatewayAttachments[] | {State, Association, Options, SubnetIds}'
```

## VPC attachment subnet and AZ placement

A VPC attachment is placed in one or more subnets, each in a different
AZ. The attachment's data-plane ENIs live in those subnets. Traffic
from a VPC resource to the TGW must reach one of those ENIs.

- An attachment in `subnet-a-public us-east-1a` only has a data-plane
  ENI in `us-east-1a`. Traffic from a resource in `us-east-1b` to the
  TGW incurs a cross-AZ hop to `us-east-1a`'s ENI before exiting the
  VPC.
- For high-throughput or latency-sensitive workloads, attach in
  multiple AZs (one subnet per AZ).
- The subnets do NOT need to be the same subnets where the EC2
  resources live. The VPC route table directs traffic to the TGW
  regardless of which subnet the ENI is in.

```bash
# Check the subnets/AZs for a VPC attachment
aws ec2 describe-transit-gateway-attachments \
  --transit-gateway-attachment-ids <vpc-attach-id> --output json | \
  jq '.TransitGatewayAttachments[].SubnetIds'

# Cross-reference subnet AZs
aws ec2 describe-subnets --subnet-ids <subnet-id-1> <subnet-id-2> --output json | \
  jq '.Subnets[] | {SubnetId, AvailabilityZone, CidrBlock}'
```

### Wrong-subnet/AZ failure mode

If a VPC attachment is placed in a subnet whose route table does NOT
have a route to the TGW, the attachment's ENI is unreachable from
other subnets in the VPC. Symptom: traffic from some subnets in the
VPC reaches the TGW; traffic from others does not.

```bash
# Check the route table for the subnet where the attachment ENI lives
aws ec2 describe-route-tables \
  --filters Name=association.subnet-id,Values=<attach-subnet-id> --output json | \
  jq '.RouteTables[].Routes'

# Also check the main route table for the VPC (covers subnets without explicit associations)
aws ec2 describe-route-tables \
  --filters Name=vpc-id,Values=<vpc-id> Name=association.main,Values=true --output json | \
  jq '.RouteTables[].Routes'
```

If the route table lacks a route for the destination CIDR pointing at
the TGW, the traffic never leaves the VPC. This is
`LAYER: TGW_ATTACHMENT_WRONG_SUBNET`.

## Appliance mode

Appliance mode is enabled per-attachment on the INSPECTION VPC's
attachment (the VPC that contains the stateful firewall / IDS / IPS).

```bash
# Check appliance mode on an attachment
aws ec2 describe-transit-gateway-attachments \
  --transit-gateway-attachment-ids <attach-id> --output json | \
  jq '.TransitGatewayAttachments[].Options.ApplianceModeSupport'

# Enable appliance mode
aws ec2 modify-transit-gateway-attachment \
  --transit-gateway-attachment-id <inspection-attach-id> \
  --options ApplianceModeSupport=enable
```

### How appliance mode changes routing

| Appliance mode | Source-AZ preservation | Cross-AZ stateful firewall | Use case |
|---|---|---|---|
| `disable` (default) | Preserved | Drops cross-AZ return flows | Standard routing |
| `enable` on inspection attachment | Override — return routes through the appliance's AZ | Works for cross-AZ flows | Stateful inspection, IDS/IPS, firewalls |

Without appliance mode, the TGW preserves the source AZ: a packet
entering the TGW in `us-east-1a` exits in `us-east-1a`. A stateful
inspection appliance with its ENI in `us-east-1a` sees the ingress
flow. The destination VPC replies; the reply enters the TGW in the
destination's AZ (e.g., `us-east-1b`). Without appliance mode, the
TGW forwards the reply directly to the source VPC in `us-east-1b`,
bypassing the inspection VPC entirely. The firewall never sees the
return half of the flow and drops it as out-of-state.

With appliance mode, the TGW routes the return traffic for any flow
that transited the inspection VPC back through the inspection VPC's
AZ, regardless of the original source AZ. The firewall sees both
halves of every flow and enforces stateful rules correctly.

### When NOT to enable appliance mode

- On a non-inspection attachment: it adds an unnecessary cross-AZ hop
  and increases latency for all flows transiting that attachment.
- On a peering attachment: peering attachments do not carry
  inspection traffic; appliance mode has no useful effect.

### Appliance mode and AZ resilience

For appliance mode to provide cross-AZ resilience, the inspection VPC
must have attachment ENIs in multiple AZs. If the inspection VPC is
attached in only one AZ and that AZ fails, all flows transiting the
inspection VPC fail, regardless of appliance mode. Attach the
inspection VPC in at least two AZs for HA.

## Security group cross-VPC constraints

TGW does NOT support cross-VPC security group references. A security
group in VPC-A cannot use `sg-xxx` from VPC-B as a source rule, even
if both VPCs are attached to the same TGW.

This works in VPC peering (same region only), which makes it a
frequent confusion when migrating from VPC peering to TGW.

### Detecting invalid cross-VPC SG references

```bash
# Find SG rules that reference a GroupId in a different VPC
aws ec2 describe-security-groups \
  --filters Name=vpc-id,Values=<vpc-a-id> --output json | \
  jq '.SecurityGroups[] | {
    GroupId,
    VpcId,
    CrossVpcRefs: [.IpPermissions[].UserIdGroupPairs[]?
      | select(.VpcId != null and .VpcId != "<vpc-a-id>")]
  } | select(.CrossVpcRefs | length > 0)'
```

Any result indicates a cross-VPC SG reference that is invalid for a
TGW topology.

### Replacing cross-VPC SG references

Replace the cross-VPC SG reference with:
- The peer VPC's CIDR block, or
- A managed prefix list containing the peer VPC's CIDRs.

```bash
# Replace with a CIDR block
aws ec2 revoke-security-group-ingress \
  --group-id <sg-id> \
  --ip-permissions IpProtocol=tcp,FromPort=443,ToPort=443,UserIdGroupPairs=[{GroupId=<peer-sg-id>,VpcId=<peer-vpc-id>}]

aws ec2 authorize-security-group-ingress \
  --group-id <sg-id> \
  --ip-permissions IpProtocol=tcp,FromPort=443,ToPort=443,IpRanges=[{CidrIp=<peer-vpc-cidr>}]
```

### Prefix list alternative

For topologies with many CIDRs, use a managed prefix list:

```bash
aws ec2 create-managed-prefix-list \
  --prefix-list-name "tgw-vpc-b-cidrs" \
  --address-family ipv4 \
  --max-entries 10

aws ec2 modify-managed-prefix-list \
  --prefix-list-id <pl-id> \
  --add-entries Cidr=10.20.0.0/16,Description="VPC-B"

aws ec2 authorize-security-group-ingress \
  --group-id <sg-id> \
  --ip-permissions IpProtocol=tcp,FromPort=443,ToPort=443,PrefixListIds=[{PrefixListId=<pl-id>}]
```

## Reachability Analyzer for end-to-end verification

When the route-table probes pass but the symptom persists, use
Reachability Analyzer to trace the exact path:

```bash
# Create a path from source ENI to destination ENI
aws ec2 create-network-insights-path \
  --source <source-eni-id> \
  --destination <destination-eni-id> \
  --protocol tcp \
  --destination-port 443 --output json

# Start the analysis
aws ec2 start-network-insights-analysis \
  --network-insights-path-id <path-id> --output json
```

The result identifies the exact component (route table, SG, NACL,
TGW route table) that blocks the flow.
