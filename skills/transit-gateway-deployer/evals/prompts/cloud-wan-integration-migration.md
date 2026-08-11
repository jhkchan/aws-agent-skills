# Eval prompt: cloud-wan-integration-migration

Design a deployment plan for attaching two existing Transit Gateways
to an AWS Cloud WAN core network for policy-driven segmentation.
Emit the standard VERDICT block.

Requirements:

- Existing TGW 1: prod-tgw-us-east-1 (ASN 64512, us-east-1, ACTIVE,
  3 VPC attachments, default route table with auto-association +
  auto-propagation)
- Existing TGW 2: prod-tgw-eu-west-1 (ASN 64513, eu-west-1, ACTIVE,
  2 VPC attachments, default route table with auto-association +
  auto-propagation)
- Global network: global-network-0abc (exists, registered with
  Network Manager)
- Core network: core-network-0abc (exists, created from the global
  network)
- Core network policy defines two segments: prod, non-prod
- Attach BOTH TGWs to the core network as TRANSIT_GATEWAY attachments
- Migration is non-disruptive: existing TGW route tables remain
  in place until the operator explicitly re-associates attachments
  to Cloud WAN-managed route tables

Existing-account context: the core network policy has been applied
and the core network is in state `DEPLOYED`. Both TGWs are ACTIVE
in their respective regions. The migration team wants to attach
both TGWs in one operation.
