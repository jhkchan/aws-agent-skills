# Gateway Endpoints and DNS — VPC Endpoint Policy Troubleshooter

Deep reference on Gateway endpoint routing (S3/DynamoDB, route table
mechanics, prefix lists, no SG/DNS), DNS resolution for interface
endpoints (private DNS, private hosted zones, VPC DNS settings), and
endpoint service health diagnostics (NLB-backed, target health, health
check failures). Loaded on demand by the skill — kept out of the main
SKILL.md body so the diagnostic procedure stays scannable.

## Gateway endpoint routing

### How Gateway endpoints differ from interface endpoints

Gateway endpoints (S3 and DynamoDB only) route traffic through a route
table entry, NOT through ENIs. This fundamental difference means:

- No security group (no ENI exists)
- No DNS configuration (routing is via prefix list in the route table)
- No per-endpoint ENI cost (Gateway endpoints are free)
- Must be explicitly added to each route table

```text
Gateway endpoint traffic flow:
  Client (10.0.1.5) → sends S3 request
    → Route table lookup for S3 prefix list (e.g., pl-68a54001)
    ├── Route table has vpce entry for pl-68a54001 → traffic via endpoint (FREE)
    └── Route table has NO vpce entry → traffic via 0.0.0.0/0 (NAT Gateway, COSTS MONEY)
```

### Prefix lists

Gateway endpoints use AWS-managed prefix lists to identify S3 and
DynamoDB IP ranges. The prefix list is automatically managed by AWS.

```bash
# Get the prefix list for S3
aws ec2 describe-managed-prefix-lists \
  --filters Name=owner-id,Values=AWS \
  --query 'PrefixLists[?contains(PrefixListName, `s3`)].{Name:PrefixListName,Id:PrefixListId}' \
  --output table --region us-east-1

# Get the prefix list for DynamoDB
aws ec2 describe-managed-prefix-lists \
  --filters Name=owner-id,Values=AWS \
  --query 'PrefixLists[?contains(PrefixListName, `dynamodb`)].{Name:PrefixListName,Id:PrefixListId}' \
  --output table --region us-east-1
```

### Verify the Gateway endpoint is in the route table

```bash
# List all Gateway endpoints and their route tables
aws ec2 describe-vpc-endpoints \
  --filters Name=vpc-endpoint-type,Values=Gateway \
  --query 'VpcEndpoints[*].{Id:VpcEndpointId,Service:ServiceName,Routes:RouteTableIds}' \
  --output table --region us-east-1

# Check a specific route table for Gateway endpoint entries
aws ec2 describe-route-tables \
  --route-table-ids rtb-private-1 \
  --query 'RouteTables[0].Routes[?VpcEndpointId!=`null`].{Dest:DestinationCidrBlock,PrefixList:DestinationPrefixListId,Endpoint:VpcEndpointId}' \
  --output table --region us-east-1
```

### Add a Gateway endpoint to additional route tables

```bash
# Add the endpoint to more route tables
aws ec2 modify-vpc-endpoint \
  --vpc-endpoint-id vpce-s3gateway123 \
  --add-route-table-ids rtb-private-2 rtb-private-3 \
  --region us-east-1

# Remove from a route table (if needed)
aws ec2 modify-vpc-endpoint \
  --vpc-endpoint-id vpce-s3gateway123 \
  --remove-route-table-ids rtb-private-3 \
  --region us-east-1
```

### Common Gateway endpoint routing failures

**Failure 1: Endpoint not in the subnet's route table**

```text
Subnet-private-2 uses route table rtb-private-2
rtb-private-2 routes:
  10.0.0.0/16 → local
  0.0.0.0/0   → nat-xxx
  (NO Gateway endpoint entry)

S3 traffic from subnet-private-2 → goes via NAT Gateway (incurs cost)
Fix: add the Gateway endpoint to rtb-private-2
```

**Failure 2: Multiple route tables, some updated, some not**

A VPC often has multiple route tables (one per subnet or AZ). The
Gateway endpoint must be in EACH route table that serves subnets
accessing S3/DynamoDB.

```bash
# List all route tables in the VPC
aws ec2 describe-route-tables \
  --filters Name=vpc-id,Values=vpc-aaa11122 \
  --query 'RouteTables[*].{Id:RouteTableId,Subnets:Associations[*].SubnetId}' \
  --output table --region us-east-1

# Check each route table for the endpoint
for RTB in $(aws ec2 describe-route-tables \
  --filters Name=vpc-id,Values=vpc-aaa11122 \
  --query 'RouteTables[*].RouteTableId' --output text --region us-east-1); do
  echo "=== $RTB ==="
  aws ec2 describe-route-tables \
    --route-table-ids "$RTB" \
    --query 'RouteTables[0].Routes[?VpcEndpointId!=`null`].{Endpoint:VpcEndpointId,Prefix:DestinationPrefixListId}' \
    --output table --region us-east-1
done
```

## DNS resolution for interface endpoints

### Private DNS for AWS services

For AWS services accessed via interface endpoints, private DNS ensures
the service's default DNS name resolves to the endpoint ENI's private IP
instead of the public IP.

**Private DNS enabled (correct):**
```text
dig ec2.us-east-1.amazonaws.com
  → resolves to 10.0.1.10 (endpoint ENI private IP)
  → traffic goes through the endpoint (no public internet, no NAT)
```

**Private DNS disabled (problematic):**
```text
dig ec2.us-east-1.amazonaws.com
  → resolves to 54.239.x.x (public IP)
  → traffic goes via public internet or NAT Gateway (bypasses endpoint)
```

### Enable/disable private DNS

```bash
# Check current state
aws ec2 describe-vpc-endpoints \
  --vpc-endpoint-ids vpce-aaa111222 \
  --query 'VpcEndpoints[0].PrivateDnsEnabled' \
  --output text --region us-east-1

# Enable private DNS
aws ec2 modify-vpc-endpoint \
  --vpc-endpoint-id vpce-aaa111222 \
  --private-dns-enabled \
  --region us-east-1

# Disable private DNS (not recommended for AWS services)
aws ec2 modify-vpc-endpoint \
  --vpc-endpoint-id vpce-aaa111222 \
  --no-private-dns-enabled \
  --region us-east-1
```

### Private DNS prerequisites

Private DNS requires:
1. The VPC must have `enableDnsHostnames` set to true
2. The VPC must have `enableDnsSupport` set to true
3. The endpoint must be for an AWS service (not a custom PrivateLink service)

```bash
# Verify VPC DNS settings
aws ec2 describe-vpc-attribute --vpc-id vpc-aaa11122 --attribute enableDnsHostnames --region us-east-1
aws ec2 describe-vpc-attribute --vpc-id vpc-aaa11122 --attribute enableDnsSupport --region us-east-1

# Enable if needed
aws ec2 modify-vpc-attribute --vpc-id vpc-aaa11122 --enable-dns-hostnames --region us-east-1
aws ec2 modify-vpc-attribute --vpc-id vpc-aaa11122 --enable-dns-support --region us-east-1
```

### Private hosted zones for non-AWS services

For custom PrivateLink services (not AWS services), a Route 53 private
hostened zone (PHZ) must be associated with the consumer VPC to resolve
the endpoint DNS name.

```bash
# Check if a PHZ is associated with the VPC
aws route53 list-hosted-zones-by-vpc \
  --vpc-id vpc-aaa11122 \
  --vpc-region us-east-1 \
  --output table

# Associate a PHZ with the VPC
aws route53 associate-vpc-with-hosted-zone \
  --hosted-zone-id Z1234567890ABC \
  --vpc VPCRegion=us-east-1,VPCId=vpc-aaa11122
```

### Common DNS failure modes

```text
Failure 1: Private DNS not enabled
  Symptom: service DNS resolves to public IP
  Fix: enable private DNS on the endpoint

  dig ssm.us-east-1.amazonaws.com → 54.x.x.x (public)
  Fix: aws ec2 modify-vpc-endpoint --vpc-endpoint-id vpce-xxx --private-dns-enabled

Failure 2: VPC DNS settings disabled
  Symptom: DNS does not resolve at all
  Fix: enable enableDnsHostnames and enableDnsSupport on VPC

  dig ssm.us-east-1.amazonaws.com → SERVFAIL
  Fix: aws ec2 modify-vpc-attribute --vpc-id vpc-xxx --enable-dns-hostnames

Failure 3: PHZ not associated with VPC (non-AWS services)
  Symptom: custom endpoint DNS name does not resolve
  Fix: associate the PHZ with the VPC

  dig my-service.custom.example.com → NXDOMAIN
  Fix: aws route53 associate-vpc-with-hosted-zone ...

Failure 4: DNS resolution conflict across VPCs
  Symptom: endpoint in VPC-A, PHZ in VPC-B, peering does not forward DNS
  Fix: enable DNS resolution across the peering connection or create a PHZ in VPC-A
```

## Endpoint service (NLB-backed) health diagnostics

For custom PrivateLink services (your own endpoint service behind an
NLB), the NLB target health determines whether traffic reaches the
backend.

### Check NLB target health

```bash
# From the PROVIDER account
# List NLBs associated with the endpoint service
aws ec2 describe-vpc-endpoint-service-configurations \
  --service-ids vpce-svc-xxx \
  --query 'ServiceConfigurations[0].{ServiceName:ServiceName,NLBArns:NetworkLoadBalancerArns}' \
  --output table --region us-east-1

# Get target groups for the NLB
aws elbv2 describe-target-groups \
  --load-balancer-arn arn:aws:elasticloadbalancing:us-east-1:999999999999:loadbalancer/net/nlb-xxx/xxx \
  --query 'TargetGroups[*].{Arn:TargetGroupArn,Port:Port,Protocol:Protocol}' \
  --output table --region us-east-1

# Check target health
aws elbv2 describe-target-health \
  --target-group-arn arn:aws:elasticloadbalancing:us-east-1:999999999999:targetgroup/tg-xxx/xxx \
  --query 'TargetHealthDescriptions[*].{Target:Target.Id,Port:Target.Port,State:TargetHealth.State,Reason:TargetHealth.Reason}' \
  --output table --region us-east-1
```

### Interpret target health states

| State | Meaning | Action |
|---|---|---|
| `healthy` | Target passes health checks | Traffic flows normally |
| `unhealthy` | Target fails health checks | Check backend instance/app |
| `initial` | Registration in progress | Wait for health check interval |
| `unused` | Target not in any AZ | Add target to correct AZ |
| `draining` | Deregistration in progress | Wait for connection draining |

### Common endpoint service health failures

**Failure 1: NLB targets unhealthy (health check mismatch)**

```text
NLB health check: TCP port 8080
Backend instance: application listening on port 80
→ Health check fails (wrong port)
Fix: update the NLB target group health check port to 80
```

**Failure 2: NLB targets unhealthy (SG blocking health check)**

```text
NLB in subnet 10.0.1.0/24
Backend instance SG allows port 8080 from 10.0.1.5 (NLB IP)
NLB scales to 10.0.1.6 → SG does not allow this IP
→ Health check fails intermittently
Fix: allow the entire NLB subnet CIDR in the backend SG
```

**Failure 3: Endpoint connection not accepted**

```text
Consumer creates endpoint → state: pending-waiting
Provider has not accepted the connection
→ Endpoint stays pending-waiting, traffic does not flow
Fix: provider accepts the connection

aws ec2 accept-vpc-endpoint-connections \
  --service-id vpce-svc-xxx \
  --vpc-endpoint-ids vpce-aaa111222 \
  --region us-east-1
```

## Terraform Gateway endpoint example

```hcl
# S3 Gateway endpoint with all route tables
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.us-east-1.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids = [
    aws_route_table.private_1.id,
    aws_route_table.private_2.id,
    aws_route_table.private_3.id,
  ]

  policy = jsonencode({
    Statement = [
      {
        Effect    = "Allow"
        Principal = "*"
        Action    = ["s3:GetObject", "s3:PutObject", "s3:ListBucket"]
        Resource  = [
          "arn:aws:s3:::my-data-bucket",
          "arn:aws:s3:::my-data-bucket/*",
        ]
      }
    ]
  })
}

# DynamoDB Gateway endpoint
resource "aws_vpc_endpoint" "dynamodb" {
  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.us-east-1.dynamodb"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.private_1.id, aws_route_table.private_2.id]
}
```
