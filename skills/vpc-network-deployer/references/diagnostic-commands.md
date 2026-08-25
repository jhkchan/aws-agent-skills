# Diagnostic Commands — VPC Network Deployer

Deep reference content moved verbatim from `vpc-network-deployer/SKILL.md`. Loaded on demand;
see SKILL.md for the condensed core and its quick navigation.

## Live-account pre-flight checks (deployment spec gate)

**Live-account pre-flight checks (skip if doing offline architecture plan):**
1. Verify the caller can run `ec2:CreateVpc`, `ec2:CreateSubnet`,
   `ec2:CreateRouteTable`, `ec2:CreateNatGateway`, `ec2:CreateSecurityGroup`,
   `ec2:CreateFlowLogs`, and `ec2:CreateVpcEndpoint`. Surface IAM gaps
   BEFORE emitting deployment commands.
2. Check for CIDR overlap with existing VPCs:
   `aws ec2 describe-vpcs --query 'Vpcs[*].[VpcId,CidrBlock]' --output table`
3. Check for CIDR overlap with on-premises ranges (requires network
   team input — flag as a PREREQUISITES_MISSING if not provided).
4. Verify an Elastic IP is available for the NAT Gateway (default EIP
   quota is 5 per region).
5. Verify the target region has ≥3 AZs available:
   `aws ec2 describe-availability-zones --region <region> --query 'AvailabilityZones[?State==`available`].ZoneName'`

## Verification commands (run after deployment)

```bash
# Verify VPC exists and has correct CIDR
aws ec2 describe-vpcs --vpc-ids vpc-xxx --query 'Vpcs[0].[VpcId,CidrBlock,Ipv6CidrBlockAssociationSet]'

# Verify subnets exist with correct CIDRs and AZs
aws ec2 describe-subnets --filters "Name=vpc-id,Values=vpc-xxx" \
  --query 'Subnets[*].[SubnetId,CidrBlock,AvailabilityZone,Tags[?Key==`Name`].Value|[0]]' \
  --output table

# Verify route tables have correct routes
aws ec2 describe-route-tables --filters "Name=vpc-id,Values=vpc-xxx" \
  --query 'RouteTables[*].[RouteTableId,Routes[*].[DestinationCidrBlock,GatewayId,NatGatewayId]]' \
  --output table

# Verify NAT Gateways are in public subnets and Available
aws ec2 describe-nat-gateways --filter "Name=vpc-id,Values=vpc-xxx" \
  --query 'NatGateways[*].[NatGatewayId,State,SubnetId]'

# Verify Internet Gateway is attached
aws ec2 describe-internet-gateways --filters "Name=attachment.vpc-id,Values=vpc-xxx"

# Verify Security Groups exist with correct rules
aws ec2 describe-security-groups --filters "Name=vpc-id,Values=vpc-xxx" \
  --query 'SecurityGroups[*].[GroupName,GroupId,IpPermissions[*].[FromPort,ToPort,UserIdGroupPairs[*].GroupId]]'

# Verify VPC Flow Logs are active
aws ec2 describe-flow-logs --filter "Name=resource-id,Values=vpc-xxx"

# Verify VPC Endpoints exist and are available
aws ec2 describe-vpc-endpoints --filters "Name=vpc-id,Values=vpc-xxx" \
  --query 'VpcEndpoints[*].[VpcEndpointId,ServiceName,State,VpcEndpointType]'

# Verify DNS settings
aws ec2 describe-vpc-attribute --vpc-id vpc-xxx --attribute enableDnsHostnames
aws ec2 describe-vpc-attribute --vpc-id vpc-xxx --attribute enableDnsSupport

# Test connectivity from a private subnet instance
aws ssm start-session --target i-xxx  # Session Manager via SSM Interface Endpoint
# Inside the instance:
#   curl -s http://169.254.169.254/latest/meta-data/  # IMDS (should work)
#   ping 8.8.8.8  # NAT egress (should work from private subnet)
#   aws s3 ls  # Gateway Endpoint (should work without NAT)
```

## Pre-flight safety checks (run before any deployment CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`create-vpc`, `create-subnet`, `create-nat-gateway`, `delete-vpc`),
  the deployer MUST emit:
  `CONFIRM: About to deploy VPC <name> in account <account> region
  <region>. Estimated monthly cost: <$X>. This is a non-reversible
  deployment. Proceed? (yes/no)`

- **CIDR overlap check is MANDATORY.** Before `create-vpc`, run:
  `aws ec2 describe-vpcs --query 'Vpcs[*].[VpcId,CidrBlock]' --output table`
  and verify the proposed CIDR does not overlap. Overlapping VPCs cannot
  peer and produce asymmetric routing on Direct Connect.

- **Elastic IP quota check.** NAT Gateways require Elastic IPs. Default
  quota is 5 per region. Request a quota increase before deploying a
  multi-NAT topology:
  `aws service-quotas get-service-quota --service-code ec2 --quota-code L-0263D0A3`

- **Cost estimate.** The deployer MUST emit a monthly cost estimate before
  deployment:
  - NAT Gateways: ~$32/month each × count
  - Interface Endpoints: ~$7/month per AZ per endpoint
  - Flow Logs S3 storage: ~$0.023/GB/month
  - Cross-AZ data transfer: $0.01/GB (if cost-optimized NAT topology)

- **DeleteVpc is DESTRUCTIVE.** Deleting a VPC deletes all subnets,
  route tables, security groups, NACLs (default), and endpoint associations.
  The deployer MUST require confirmation for `delete-vpc` and verify no
  running instances, RDS, or ALBs are in the VPC before proceeding.

- **Tag everything at creation.** Use `--tag-specifications` on every
  `create-*` command. Tags are the primary cost-allocation mechanism. A
  VPC deployed without tags cannot be attributed to a team or project.
  Required tags: `Name`, `Environment`, `Team`, `CostCenter`.
