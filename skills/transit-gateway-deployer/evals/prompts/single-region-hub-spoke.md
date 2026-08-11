# Eval prompt: single-region-hub-spoke

Design a deployment plan for a production AWS Transit Gateway. Emit
the standard VERDICT block (TGW_SPEC, VERDICT, ARCHITECTURE,
CHECKLIST, FINDINGS, DEPLOY_COMMANDS).

Requirements:

- TGW name: prod-tgw-us-east-1, ASN 64512
- DNS support: enabled
- Multicast: disabled
- AutoAcceptSharedAttachments: disable
- DefaultRouteTableAssociation: enable
- DefaultRouteTablePropagation: enable
- VPC attachment 1: vpc-0app1, subnets subnet-0a1, subnet-0b1,
  subnet-0c1 (all available, us-east-1a/b/c)
- VPC attachment 2: vpc-0app2, subnets subnet-0a2, subnet-0b2,
  subnet-0c2 (all available, us-east-1a/b/c)
- VPC attachment 3: vpc-shared, subnets subnet-0a3, subnet-0b3,
  subnet-0c3 (all available, us-east-1a/b/c)
- All VPCs should route to each other (single-tier flat topology)
- No peering, no Connect, no multicast, no RAM share

Existing-account context: the three VPCs and subnets were validated
via describe-subnets. The account has no other TGWs in us-east-1.
IAM principal holds ec2:CreateTransitGateway,
CreateTransitGatewayVpcAttachment, CreateTransitGatewayRouteTable,
AssociateTransitGatewayRouteTable,
EnableTransitGatewayRouteTablePropagation.
