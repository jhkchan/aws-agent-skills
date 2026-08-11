# End-to-end usage scenario: transit-gateway-deployer

A walkthrough showing the skill producing a deployment plan for a
production single-region Transit Gateway with three VPC attachments
and a single default route table. Demonstrates the READY_TO_DEPLOY
verdict, architecture checklist, and ordered deploy-command list.

## Input (user prompt)

> Provision a Transit Gateway for our us-east-1 hub. We have three
> VPCs (app1, app2, shared) and want them to all route to each
> other. Use ASN 64512, enable DNS, disable multicast, disable
> auto-accept for cross-account (we may add consumer accounts
> later). Use the default route table with auto-association and
> auto-propagation — keep it simple for now.

## Expected behavior

1. **Pre-flight:** The skill validates the spec — TGW ASN unique
   within the account (no peering pair yet), three VPC attachments
   with subnets all `available`, AZ scope consistent
   (us-east-1a/b/c) across all three attachments, IAM permissions
   confirmed. No peering, no Connect, no multicast, no RAM share.
2. **TGW options:** ASN 64512, DNS enabled, multicast disabled,
   AutoAcceptSharedAttachments disabled, default route table
   association and propagation enabled (simple topology).
3. **VPC attachments:** One subnet per AZ, consistent AZs across
   attachments, appliance mode disabled (no NVA inspection).
4. **Route tables:** Default route table auto-wires all
   attachments. No explicit association or propagation needed.
5. **Verdict:** READY_TO_DEPLOY — all checklist dimensions pass.

## Expected output

```text
TGW: prod-tgw-us-east-1
VERDICT: READY_TO_DEPLOY
TARGET: prod-tgw-us-east-1
PRE_CHECKS:
  - [PASS] TGW ASN 64512 unique within the account
  - [PASS] DNS support enabled, DNS propagation enabled
  - [PASS] VPC vpc-0app1 subnets subnet-0a1, subnet-0b1, subnet-0c1 all available, /28+
  - [PASS] VPC vpc-0app2 subnets subnet-0a2, subnet-0b2, subnet-0c2 all available, /28+
  - [PASS] VPC vpc-shared subnets subnet-0a3, subnet-0b3, subnet-0c3 all available, /28+
  - [PASS] AZ scope us-east-1a/b/c consistent across all three VPC attachments
  - [PASS] DefaultRouteTableAssociation=enable, DefaultRouteTablePropagation=enable (simple flat topology)
  - [PASS] AutoAcceptSharedAttachments=false (production posture)
  - [PASS] IAM principal holds ec2:CreateTransitGateway*, AssociateTransitGatewayRouteTable, EnableTransitGatewayRouteTablePropagation
STEPS:
  1. CONFIRM: About to create-tgw prod-tgw-us-east-1 in account 111111111111 region us-east-1. Creates TGW with ASN 64512, three VPC attachments, default route table. Estimated cost: $36.50/mo base + 3 * $0.05/hr * 730 hr = $109.50/mo for attachments + ~$0.02/GB processed. Proceed? (yes/no)
  2. aws ec2 create-transit-gateway --description "prod-tgw-us-east-1" --options AmazonSideAsn=64512,AutoAcceptSharedAttachments=disable,DefaultRouteTableAssociation=enable,DefaultRouteTablePropagation=enable,VpnEcmpSupport=enable,DnsSupport=enable,MulticastSupport=disable --tag-specifications "ResourceType=transit-gateway,Tags=[{Key=Name,Value=prod-tgw-us-east-1}]"
  3. aws ec2 create-transit-gateway-vpc-attachment --transit-gateway-id <tgw-id> --vpc-id vpc-0app1 --subnet-ids subnet-0a1 subnet-0b1 subnet-0c1 --options ApplianceModeSupport=disable,DnsSupport=enable --tag-specifications "ResourceType=transit-gateway-attachment,Tags=[{Key=Name,Value=app1-tgw}]"
  4. aws ec2 create-transit-gateway-vpc-attachment --transit-gateway-id <tgw-id> --vpc-id vpc-0app2 --subnet-ids subnet-0a2 subnet-0b2 subnet-0c2 --options ApplianceModeSupport=disable,DnsSupport=enable --tag-specifications "ResourceType=transit-gateway-attachment,Tags=[{Key=Name,Value=app2-tgw}]"
  5. aws ec2 create-transit-gateway-vpc-attachment --transit-gateway-id <tgw-id> --vpc-id vpc-shared --subnet-ids subnet-0a3 subnet-0b3 subnet-0c3 --options ApplianceModeSupport=disable,DnsSupport=enable --tag-specifications "ResourceType=transit-gateway-attachment,Tags=[{Key=Name,Value=shared-tgw}]"
POST_VERIFY:
  - (pending execution)
  - describe-transit-gateways returns State=available
  - describe-transit-gateway-vpc-attachments returns 3 attachments all State=available
  - Each attachment auto-associated with default route table, each propagates to default route table
  - EC2 in vpc-0app1 reaches EC2 in vpc-0app2 and EC2 in vpc-shared (traceroute via TGW)
TGW_OPTIONS: ASN 64512 DNS enabled multicast disabled auto-accept disabled
ATTACHMENTS: 3 VPC + 0 peering + 0 connect
ROUTE_TABLES: default only (auto-association + auto-propagation)
RAM_SHARE: 0 principals (no cross-account attachments)
CLOUD_WAN: not attached
NOTES:
  - All VPCs route to each other via the default route table (flat topology).
  - For future segmentation, switch to DefaultRouteTableAssociation=disable + DefaultRouteTablePropagation=disable and add explicit route tables per tier.
  - Cost: $36.50/mo TGW base + 3 * $0.05/hr * 730 hr = $109.50/mo for attachments + ~$0.02/GB processed.
```

## What the baseline (no-skill) response misses

A generic assistant without this skill would:
- Not call out the AZ-scope consistency rule (the most common cause
  of cross-AZ charges in TGW topologies).
- Not flag AutoAcceptSharedAttachments=disable as a production
  posture decision (vs. the convenience default).
- Not distinguish default route table association from propagation
  (relevant for future segmentation).
- Not include the CONFIRM gate with cost estimate.
- Not produce a deterministic VERDICT block for downstream
  automation.

The skill converts an open-ended "set up a Transit Gateway" prompt
into a deterministic, pre-checked, ordered deploy plan with a single
READY_TO_DEPLOY or PREREQUISITES_MISSING verdict.
