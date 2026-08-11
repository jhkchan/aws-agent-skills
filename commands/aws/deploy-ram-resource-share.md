---
description: Deploy an AWS RAM resource share with production-grade configuration (resource type selection for Subnets, Transit Gateways, Route53 Resolver rules, License Manager, Dedicated Hosts, Capacity Reservations, Image Builder; principal association with account IDs, OU ARNs, Organization ARNs; permission association with AWS-managed and customer-managed permissions; allow-external-principals control). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create ram resource share"
  - "share subnet across accounts"
  - "share transit gateway"
  - "ram principal association"
  - "ram permission association"
  - "share route53 resolver rules"
  - "ram organization share"
  - "customer managed permissions ram"
  - "ram ou principal"
  - "license manager sharing"
  - "dedicated host sharing"
  - "capacity reservation sharing"
  - "image builder sharing"
  - "ram vs vpc peering"
routes_to: ram-resource-share-deployer
---

# /aws:deploy-ram-resource-share

Activate the `ram-resource-share-deployer` skill and deploy an AWS RAM
resource share with production-grade configuration.

## What it does

The skill walks a 9-step deployment procedure and emits a
READY_TO_DEPLOY checklist:

1. Resource type selection (Subnet, Transit Gateway, Resolver Rules,
   License Manager, Dedicated Host, Capacity Reservation, Image Builder)
2. Principal selection (account IDs, OU ARNs, Organization ARN)
3. Create the resource share
4. Share with Organization or OU
5. Permission association (managed and customer-managed)
6. Associate additional resources
7. Associate additional principals
8. Accept invitations (external accounts only)
9. Verification and post-deployment checks

## When to use

- You need to create a new RAM resource share.
- You want to share subnets across accounts for centralized networking.
- You want to share a Transit Gateway with the entire Organization.
- You need to share Route53 Resolver rules with specific OUs.
- You want to create customer-managed permissions for fine-grained control.
- You want to compare resource sharing vs VPC peering.

## How to invoke

### Slash command

```
/aws:deploy-ram-resource-share
```

Then provide: resource share name, resource type and ARNs, principals
(account IDs, OU ARN, or Organization ARN), permission type (managed
or customer-managed), allow external principals flag, and tags.

### Natural language

Any of these routes to the same skill:

- "share subnets across accounts"
- "share a transit gateway with the organization"
- "create a RAM resource share"
- "share Route53 Resolver rules with an OU"
- "create a customer-managed permission for RAM"

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The output checklist feeds into verification pipelines and audit skills.

## Example

```
You: /aws:deploy-ram-resource-share

     Share subnets subnet-abc123 and subnet-def456 from account
     123456789012 with accounts 111111111111 and 222222222222 via
     RAM. Same Organization, all features. Default permission.
     Internal only. Name: shared-subnets-prod.

Skill:
  RESOURCE_SHARE: shared-subnets-prod
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓]      Resource share name — shared-subnets-prod
    [✓]      Resource type — ec2:Subnet (subnet-abc123, subnet-def456)
    [✓]      Principals — 111111111111, 222222222222 (account IDs)
    [✓]      Permission association — AWSRAMDefaultPermissionSubnet (managed)
    [✓]      Allow external principals — false (internal accounts only)
    [✓]      Sharing visibility — INTERNAL (principals in same Organization)
    [✓]      Feature set — ALL (Organization all features enabled)
    [✓]      Resource share status — ACTIVE
    [✓]      Tags — Environment=production, Application=networking
  VERIFICATION_COMMANDS:
    aws ram get-resource-shares --resource-share-arns arn:aws:ram:us-east-1:123456789012:resource-share/shared-subnets-prod
    aws ram list-principals --resource-owner SELF --resource-share-arn arn:aws:ram:us-east-1:123456789012:resource-share/shared-subnets-prod
    aws ram list-resources --resource-owner SELF --resource-share-arn arn:aws:ram:us-east-1:123456789012:resource-share/shared-subnets-prod
    aws ram list-permissions --resource-owner SELF
```

## References

- Skill definition: `skills/ram-resource-share-deployer/SKILL.md`
- Deployment CLI commands: `skills/ram-resource-share-deployer/references/deployment-cli-commands.md`
- Permissions, resource types, vs peering guide: `skills/ram-resource-share-deployer/references/permissions-and-resource-types.md`
- Eval suite: `skills/ram-resource-share-deployer/evals/evals.json`
