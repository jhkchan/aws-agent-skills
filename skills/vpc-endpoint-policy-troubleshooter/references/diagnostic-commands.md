# Diagnostic Commands — VPC Endpoint Policy Troubleshooter

Per-layer probe and fix command listings moved out of the SKILL.md body. Loaded on demand.

## Layer 1 — verify the endpoint's security group (ENI + SG inbound rules)

```bash
# Get the endpoint's network interface IDs
ENI_IDS=$(aws ec2 describe-vpc-endpoints \
  --vpc-endpoint-ids vpce-aaa111222 \
  --query 'VpcEndpoints[0].NetworkInterfaceIds' \
  --output text --region us-east-1)

# Get the security group attached to the endpoint ENIs
for ENI in $ENI_IDS; do
  echo "ENI: $ENI"
  aws ec2 describe-network-interfaces \
    --network-interface-ids "$ENI" \
    --query 'NetworkInterfaces[0].Groups[*].{GroupId:GroupId,GroupName:GroupName}' \
    --output table --region us-east-1
done

# Check inbound rules on the endpoint's security group
SG_ID=$(aws ec2 describe-network-interfaces \
  --network-interface-ids $(aws ec2 describe-vpc-endpoints \
    --vpc-endpoint-ids vpce-aaa111222 \
    --query 'VpcEndpoints[0].NetworkInterfaceIds' --output text) \
  --query 'NetworkInterfaces[0].Groups[0].GroupId' --output text --region us-east-1)

aws ec2 describe-security-groups \
  --group-ids "$SG_ID" \
  --query 'SecurityGroups[0].IpPermissions[*].{Protocol:IpProtocol,From:FromPort,To:ToPort,Source:IpRanges[*].CidrIp}' \
  --output table --region us-east-1
```

## Layer 1 — fix: add inbound rule from client subnet

```bash
aws ec2 authorize-security-group-ingress \
  --group-id sg-vpce123 \
  --protocol tcp \
  --port 443 \
  --cidr 10.0.2.0/24 \
  --region us-east-1
```

## Layer 2 — retrieve the endpoint policy

```bash
# Get the endpoint policy (URL-encoded JSON)
aws ec2 describe-vpc-endpoints \
  --vpc-endpoint-ids vpce-aaa111222 \
  --query 'VpcEndpoints[0].PolicyDocument' \
  --output text --region us-east-1 | jq -r 'URL DECODE'

# Or use --query to decode automatically
aws ec2 describe-vpc-endpoints \
  --vpc-endpoint-ids vpce-aaa111222 \
  --query 'VpcEndpoints[0].PolicyDocument' \
  --output text --region us-east-1
```

## Layer 2 — verify the endpoint policy allows the requested action

```bash
# Check if the policy allows s3:GetObject (example)
aws ec2 describe-vpc-endpoints \
  --vpc-endpoint-ids vpce-aaa111222 \
  --query 'VpcEndpoints[0].PolicyDocument' \
  --output text --region us-east-1 | python3 -c "
import sys, json, urllib.parse
policy = json.loads(urllib.parse.unquote(sys.stdin.read()))
for stmt in policy.get('Statement', []):
    if stmt.get('Effect') == 'Allow':
        actions = stmt.get('Action', [])
        if isinstance(actions, str):
            actions = [actions]
        print(f'Allowed actions: {actions}')
        print(f'Principal: {stmt.get(\"Principal\")}')
        print(f'Resource: {stmt.get(\"Resource\")}')
"
```

## Layer 2 — fix: update the endpoint policy

```bash
aws ec2 modify-vpc-endpoint \
  --vpc-endpoint-id vpce-aaa111222 \
  --policy-document file://updated-policy.json \
  --region us-east-1
```

## Layer 3 — verify private DNS is enabled

```bash
aws ec2 describe-vpc-endpoints \
  --vpc-endpoint-ids vpce-aaa111222 \
  --query 'VpcEndpoints[0].PrivateDnsEnabled' \
  --output text --region us-east-1
# Expected: true (for AWS services with private DNS)
```

## Layer 3 — verify DNS resolution from a client instance

```bash
# From a client EC2 instance in the VPC
dig vpce-aaa111222-xxx.service-region.vpce.amazonaws.com
# Should return the ENI's private IP (e.g., 10.0.1.10)

# For AWS services with private DNS enabled
dig ec2.us-east-1.amazonaws.com
# Should return the endpoint ENI's private IP, NOT the public IP

# If it returns a public IP or NXDOMAIN → DNS is not routing through endpoint
```

## Layer 3 — enable private DNS

```bash
aws ec2 modify-vpc-endpoint \
  --vpc-endpoint-id vpce-aaa111222 \
  --private-dns-enabled \
  --region us-east-1
```

## Layer 4 — verify the Gateway endpoint is in the route table

```bash
# List Gateway endpoints and their route tables
aws ec2 describe-vpc-endpoints \
  --filters Name=vpc-endpoint-type,Values=Gateway \
  --query 'VpcEndpoints[*].{Id:VpcEndpointId,Service:ServiceName,Routes:RouteTableIds}' \
  --output table --region us-east-1

# Check if the affected subnet's route table has the endpoint
aws ec2 describe-route-tables \
  --route-table-ids rtb-abc123 \
  --query 'RouteTables[0].Routes[?VpcEndpointId!=`null`].{Dest:DestinationCidrBlock,PrefixList:DestinationPrefixListId,Endpoint:VpcEndpointId}' \
  --output table --region us-east-1
```

## Layer 4 — add a Gateway endpoint to a route table

```bash
aws ec2 modify-vpc-endpoint \
  --vpc-endpoint-id vpce-s3gateway123 \
  --add-route-table-ids rtb-private-1 rtb-private-2 \
  --region us-east-1
```

## Layer 5 — verify the endpoint service allows the consumer account

```bash
# Provider account: check who is allowed to connect
aws ec2 describe-vpc-endpoint-service-permissions \
  --service-name com.amazonaws.vpce.us-east-1.vpce-svc-xxx \
  --query 'AllowedPrincipals[*].Principal' \
  --output table --region us-east-1

# If the consumer account is not listed, add it
aws ec2 modify-vpc-endpoint-service-permissions \
  --service-name com.amazonaws.vpce.us-east-1.vpce-svc-xxx \
  --add-allowed-principals arn:aws:iam::123456789012:root \
  --region us-east-1
```

## Layer 6 — verify the endpoint service configuration

```bash
# Check the endpoint service
aws ec2 describe-vpc-endpoint-services \
  --service-names com.amazonaws.vpce.us-east-1.vpce-svc-xxx \
  --query 'ServiceDetails[0].{ServiceName:ServiceName,AvailabilityZones:AvailabilityZones,PrivateDnsName:PrivateDnsName}' \
  --output table --region us-east-1

# Check NLB target health (from the provider account)
aws elbv2 describe-target-health \
  --target-group-arn arn:aws:elasticloadbalancing:us-east-1:999999999999:targetgroup/tg-xxx/xxx \
  --query 'TargetHealthDescriptions[*].{Target:Target.Id,Port:Target.Port,State:TargetHealth.State,Reason:TargetHealth.Reason}' \
  --output table --region us-east-1
```

## Layer 6 — provider accepts the endpoint connection

```bash
# Provider account: accept pending endpoint connections
aws ec2 accept-vpc-endpoint-connections \
  --service-id vpce-svc-xxx \
  --vpc-endpoint-ids vpce-aaa111222 \
  --region us-east-1
```

## Layer 7 — timeout diagnosis three-test decision tree

```text
Timeout diagnosis:
  Test 1: Can the client reach the endpoint ENI IP?
    telnet 10.0.1.10 443
    ├── TIMEOUT → Layer 1 (security group blocking)
    └── CONNECTED → Layer 1 is OK, proceed to Layer 6

  Test 2: Is the NLB target healthy?
    aws elbv2 describe-target-health (from provider account)
    ├── unhealthy → Layer 6 (NLB/backend issue)
    └── healthy → Layer 6 is OK, check endpoint policy (Layer 2)

  Test 3: Does the endpoint policy allow the action?
    (HTTP 403 → endpoint policy, NOT timeout)
    (HTTP 200 → everything works, issue was transient)
```

## Layer 8 — validate the endpoint policy JSON before applying

```bash
# Validate JSON syntax
echo '{"Statement":[{"Effect":"Allow","Principal":"*","Action":"*","Resource":"*"}]}' | python3 -m json.tool

# Common errors:
# - Trailing comma: {"Action":["s3:GetObject",]} ← remove trailing comma
# - Missing bracket: {"Statement":[{"Effect":"Allow"} ← close all brackets
# - Invalid principal: {"Principal":{"AWS":"account-id"}} ← must be ARN or "*"
# - String not quoted: {"Effect": Allow} ← quote the value: {"Effect": "Allow"}
```

## Layer 8 — policy with syntax error fails on modify

```bash
aws ec2 modify-vpc-endpoint \
  --vpc-endpoint-id vpce-aaa111222 \
  --policy-document file://broken-policy.json
# Error: InvalidPolicyDocument — policy document is malformed
```

## Layer 9 — verify the endpoint service is available

```bash
# Check the endpoint service state
aws ec2 describe-vpc-endpoint-services \
  --service-names com.amazonaws.vpce.us-east-1.vpce-svc-xxx \
  --query 'ServiceDetails[0].{ServiceName:ServiceName,Owner:Owner,BaseEndpointDnsNames:BaseEndpointDnsNames}' \
  --output table --region us-east-1

# If the service is not found, it may have been deleted by the provider
# Check the endpoint's service name
aws ec2 describe-vpc-endpoints \
  --vpc-endpoint-ids vpce-aaa111222 \
  --query 'VpcEndpoints[0].{ServiceName:ServiceName,State:State}' \
  --output table --region us-east-1
```
