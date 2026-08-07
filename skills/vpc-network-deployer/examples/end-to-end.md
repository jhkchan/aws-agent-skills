# End-to-end usage scenario: vpc-network-deployer

A walkthrough showing the skill producing a deployment plan for a
production 3-AZ VPC with three tiers (public/private/database), HA NAT
topology, Gateway + Interface endpoints, Flow Logs, and dual-stack IPv6.
Demonstrates the READY_TO_DEPLOY verdict, network architecture validation
checklist, and ordered deploy-command list.

## Input (user prompt)

> Design a production VPC for a new microservices platform. We need
> public-facing ALBs, private ECS Fargate workloads, and a private RDS
> database tier. Three AZs in us-east-1, HA NAT, and all the standard
> VPC endpoints. We also want IPv6 dual-stack.

## Expected behavior

1. **Pre-flight:** The skill validates the deployment spec — region,
   CIDR, AZ count, tier list, NAT strategy all present. No CIDR overlap
   with existing VPCs (10.10.0.0/16, 10.20.0.0/16) or on-prem.
2. **CIDR planning:** Allocates 10.0.0.0/16 across 3 tiers × 3 AZs with
   /20 per tier per AZ, leaving 50% reserved for growth.
3. **Route table design:** Public → IGW, private → AZ-local NAT,
   database → local-only (no internet egress).
4. **Endpoints:** Gateway (S3, DynamoDB — free) + Interface (Secrets
   Manager, SSM, KMS, CloudWatch Logs, STS, ECR — ~$190/month).
5. **Cost estimate:** ~$232/month (NAT $96 + Interface Endpoints $126 +
   Flow Logs S3 $10).
6. **Verdict:** READY_TO_DEPLOY — all 11 checklist dimensions pass.

## Expected output

```text
VPC_SPEC: prod-microservices-vpc
VERDICT: READY_TO_DEPLOY
ARCHITECTURE:
  Region: us-east-1
  CIDR: 10.0.0.0/16 (IPv4), 2600:1f18:xxxx::/56 (IPv6 dual-stack)
  AZs: [us-east-1a, us-east-1b, us-east-1c]
  Tiers:
    - Public: [10.0.0.0/20, 10.0.16.0/20, 10.0.32.0/20] → IGW
    - Private: [10.0.48.0/20, 10.0.64.0/20, 10.0.80.0/20] → NAT (HA per-AZ)
    - Database: [10.0.96.0/24, 10.0.97.0/24, 10.0.98.0/24] → local-only
  NAT: HA (3 NAT Gateways, one per AZ, ~$96/month base)
  Endpoints:
    - Gateway: S3, DynamoDB (free)
    - Interface: SecretsManager, SSM, KMS, CloudWatch Logs, STS, ECR (~$190/month)
  Flow Logs: S3 destination, 1-year retention
  DNS: enableDnsHostnames + enableDnsSupport, AmazonProvidedDNS
CHECKLIST:
  [x] CIDR 10.0.0.0/16 is RFC 1918, no overlap with existing VPCs or on-prem
  [x] Subnet tiers span 3 AZs with /20 growth headroom per tier per AZ
  [x] Public subnets route 0.0.0.0/0 → igw-prod
  [x] Private subnets route 0.0.0.0/0 → AZ-local NAT Gateway
  [x] Database subnets have local-only route table (no internet egress)
  [x] Security Groups reference by name (sg-prod-alb, sg-prod-app, sg-prod-db)
  [x] NACLs allow ephemeral ports (1024-65535) for return traffic
  [x] VPC Flow Logs capture ALL traffic to S3 with 1-year retention
  [x] Gateway Endpoints for S3 and DynamoDB deployed to all route tables
  [x] Interface Endpoints for private-service connectivity (6 services × 3 AZs)
  [x] DNS hostnames and support enabled
FINDINGS:
  - [INFO] Gateway Endpoints for S3/DynamoDB will save ~$200/month in NAT processing
  - [INFO] Estimated monthly cost: NAT $96 + Interface Endpoints $190 + Flow Logs $10 = ~$296/month
  - [NOTE] IPv6 dual-stack requires Egress-Only Internet Gateway for private subnets
DEPLOY_COMMANDS:
  1. aws ec2 create-vpc --cidr-block 10.0.0.0/16 --amazon-provided-ipv6-cidr-block
  2. aws ec2 modify-vpc-attribute --vpc-id <vpc> --enable-dns-hostnames
  3. aws ec2 modify-vpc-attribute --vpc-id <vpc> --enable-dns-support
  4. aws ec2 create-internet-gateway + attach
  5. aws ec2 create-egress-only-internet-gateway
  6. aws ec2 create-subnet (×9: 3 tiers × 3 AZs)
  7. aws ec2 create-nat-gateway (×3: one per AZ, in public subnets)
  8. aws ec2 create-route-table (×7: 1 public + 3 private + 3 database)
  9. aws ec2 create-security-group (×4: alb, app, db, bastion)
  10. aws ec2 create-network-acl (×3: one per tier)
  11. aws ec2 create-flow-logs --traffic-type ALL --log-destination-type s3
  12. aws ec2 create-vpc-endpoint --vpc-endpoint-type Gateway (×2: S3, DynamoDB)
  13. aws ec2 create-vpc-endpoint --vpc-endpoint-type Interface (×6 services)
```

## Post-deployment verification

After running the deploy commands, verify the VPC is correctly
provisioned:

```bash
# Verify subnets span all 3 AZs with correct CIDRs
aws ec2 describe-subnets --filters "Name=vpc-id,Values=vpc-xxx" \
  --query 'Subnets[*].[SubnetId,CidrBlock,AvailabilityZone]' --output table

# Verify route tables — database tier should have NO 0.0.0.0/0 route
aws ec2 describe-route-tables --filters "Name=vpc-id,Values=vpc-xxx" \
  --query 'RouteTables[*].[RouteTableId,Routes[*].[DestinationCidrBlock,Target]]'

# Verify NAT Gateways are Available and in public subnets
aws ec2 describe-nat-gateways --filter "Name=vpc-id,Values=vpc-xxx" \
  --query 'NatGateways[*].[NatGatewayId,State]'

# Verify Gateway Endpoints are in route tables
aws ec2 describe-vpc-endpoints --filters "Name=vpc-id,Values=vpc-xxx" \
  --query 'VpcEndpoints[*].[ServiceName,State,VpcEndpointType]'
```

## Common pitfalls to verify after deployment

1. **Database subnet has no internet route.** Confirm the database route
   table has only `10.0.0.0/16 → local`. A stray `0.0.0.0/0` route breaks
   the defense-in-depth model.
2. **Gateway Endpoint added to all route tables.** New route tables
   created after the Gateway Endpoint do NOT inherit the endpoint. Add
   them explicitly.
3. **Interface Endpoints have private DNS enabled.** Without
   `--private-dns-enabled`, SDKs route API calls through the NAT Gateway
   instead of the endpoint.
4. **NACLs allow ephemeral ports.** Without the ephemeral-port rule
   (1024-65535 inbound), all outbound HTTPS connections fail silently.
