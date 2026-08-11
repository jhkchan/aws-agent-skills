# Eval: transit-gateway-share-organization

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — ec2:TransitGateway, Organization ARN principal, auto-accept for all accounts

## Prompt

Provision a RAM resource share in us-east-1. Name:
shared-tgw-org. Resource type: ec2:TransitGateway. Resource
ARN: arn:aws:ec2:us-east-1:123456789012:transit-gateway/
tgw-0abc123def. Principals: entire Organization
arn:aws:organizations::123456789012:organization/o-abc123def.
All features enabled. Allow external principals: false. Use
default managed permission. Tags: Environment=production,
Application=networking.
