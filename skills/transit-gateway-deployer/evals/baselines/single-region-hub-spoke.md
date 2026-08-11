# Baseline (no-skill) response: single-region-hub-spoke

This file captures what a generic assistant produces WITHOUT the
transit-gateway-deployer skill loaded — the contrast that proves
the skill adds structure around the association vs. propagation
distinction, AZ-scope consistency, AutoAcceptSharedAttachments,
appliance mode, and the confused-deputy trust policy.

---

Here's a plan to set up your Transit Gateway.

The TGW will:
- Connect the three VPCs (app1, app2, shared)
- Use ASN 64512
- Enable DNS so the VPCs can use Route 53 Resolver
- Let all VPCs route to each other

Steps:

1. Create the TGW.
2. Create three VPC attachments.
3. Use the default route table for everything.

Commands:

```
aws ec2 create-transit-gateway --description "prod-tgw-us-east-1" \
  --options AmazonSideAsn=64512
aws ec2 create-transit-gateway-vpc-attachment --transit-gateway-id <tgw-id> \
  --vpc-id vpc-0app1 --subnet-ids subnet-0a1 subnet-0b1 subnet-0c1
aws ec2 create-transit-gateway-vpc-attachment --transit-gateway-id <tgw-id> \
  --vpc-id vpc-0app2 --subnet-ids subnet-0a2 subnet-0b2 subnet-0c2
aws ec2 create-transit-gateway-vpc-attachment --transit-gateway-id <tgw-id> \
  --vpc-id vpc-shared --subnet-ids subnet-0a3 subnet-0b3 subnet-0c3
```

Once the attachments are available, the VPCs should be able to
route to each other. Let me know if you need help with the IAM
permissions.
