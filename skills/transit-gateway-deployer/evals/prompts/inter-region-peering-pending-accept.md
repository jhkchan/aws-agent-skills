# Eval prompt: inter-region-peering-pending-accept

Design a deployment plan for an inter-region Transit Gateway topology
with peering. Emit the standard VERDICT block.

Requirements:

- Source TGW: prod-tgw-us-east-1 (ASN 64512, us-east-1, ACTIVE)
- Peer TGW: prod-tgw-eu-west-1 (ASN 64513, eu-west-1, ACTIVE,
  same account 111111111111)
- VPC attachment in us-east-1: vpc-0app1 (subnets in us-east-1a/b/c,
  all available)
- VPC attachment in eu-west-1: vpc-0app1-eu (subnets in eu-west-1a/b/c,
  all available)
- Route tables: default route table in each TGW with
  auto-association + auto-propagation enabled
- Peering between the two TGWs (request submitted from us-east-1)

Existing-account context: the peering request was created via
create-transit-gateway-peering-attachment and is currently in
`pendingAcceptance` state. The peer owner (same account) has not
yet called accept-transit-gateway-peering-attachment in eu-west-1.
Both TGWs are ACTIVE in their respective regions. The plan should
note acceptance as a required step before traffic flows.
