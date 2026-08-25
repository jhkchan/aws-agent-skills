# Worked Examples — VPC Endpoint Policy Troubleshooter

Secondary worked examples and common-failure illustrations moved out of the SKILL.md body. Loaded on demand.

## Layer 1 — common SG failure illustration

```text
Endpoint SG inbound rules:
  Port 443 (TCP)  Source 10.0.0.0/16  ← allows VPC-wide
  Port 443 (TCP)  Source 10.0.1.0/24  ← allows only subnet-1

Client is in subnet-2 (10.0.2.0/24) → TIMEOUT (no matching inbound rule)
```

## Layer 2 — custom policy failure illustration

```text
Endpoint policy:
  Allow: s3:GetObject on arn:aws:s3:::bucket-a/*

Request: s3:PutObject on arn:aws:s3:::bucket-a/
→ ENDPOINT POLICY DENIES (action not in allowed list)
→ HTTP 403 Access Denied
```

## Layer 3 — common DNS failures illustration

```text
Failure 1: Private DNS not enabled
  dig ssm.us-east-1.amazonaws.com → returns public IP
  Fix: enable private DNS on the endpoint

Failure 2: PHZ not associated with VPC
  dig my-service.custom.example.com → NXDOMAIN
  Fix: associate the Route 53 PHZ with the VPC

Failure 3: DNS resolution conflict
  Client VPC has enableDnsSupport=false
  Fix: enable DNS support on the VPC
```

## Layer 4 — common Gateway endpoint routing failure illustration

```text
Subnet route table (rtb-private-1):
  10.0.0.0/16 → local
  0.0.0.0/0   → nat-xxx
  (NO Gateway endpoint entry for S3 prefix list pl-68a54001)

Result: S3 traffic goes via NAT Gateway (costs money, not using endpoint)
Fix: add the Gateway endpoint to the route table
```

## Layer 5 — common cross-account failure illustration

```text
Consumer account: 123456789012
Provider endpoint service: com.amazonaws.vpce.us-east-1.vpce-svc-xxx

Provider service allowed principals:
  arn:aws:iam::111111111111:root  ← only account A is allowed

Consumer account 123456789012 is NOT in the allowed list → 403

Fix: provider adds consumer account to allowed principals
```

## Layer 6 — common endpoint service failures illustration

```text
Failure 1: NLB target unhealthy
  Target state: unhealthy
  Reason: Target.Timeout or Target.FailedHealthChecks
  Result: endpoint connection times out intermittently or always

Failure 2: NLB listener misconfigured
  Listener port does not match the endpoint service port
  Result: connection refused

Failure 3: Endpoint service acceptance required
  Endpoint is in pending-waiting state
  Provider has not accepted the endpoint connection request
  Fix: provider accepts the endpoint connection
```

## Worked example — Gateway endpoint not in route table

```text
VPC_ENDPOINT: vpce-s3gateway123 (Gateway — com.amazonaws.us-east-1.s3)
VERDICT: ROOT_CAUSE_IDENTIFIED
DIAGNOSIS:
  ROOT CAUSE: Gateway endpoint vpce-s3gateway123 is NOT in route table rtb-private-2; S3 traffic from subnet-private-2 goes via NAT Gateway
  FAILURE LAYER: Route Table
  IMPACT: S3 traffic from subnet-private-2 incurs NAT Gateway data processing charges instead of using the free Gateway endpoint
EVIDENCE:
  [N/A] Security group (interface): not applicable (gateway endpoint)
  [✓] Endpoint policy: default (full access)
  [N/A] DNS resolution: not applicable (gateway endpoint)
  [✗] Route table (gateway): endpoint vpce-s3gateway123 NOT in route table rtb-private-2; only in rtb-private-1
  [N/A] Cross-account: not applicable (same account)
  [N/A] Endpoint service health: not applicable (gateway endpoint)
  [✓] Endpoint state: available
  [✓] Policy JSON syntax: valid (default policy)
REMEDIATION_COMMANDS:
  aws ec2 modify-vpc-endpoint --vpc-endpoint-id vpce-s3gateway123 --add-route-table-ids rtb-private-2 --region us-east-1
  # Verify: aws ec2 describe-route-tables --route-table-ids rtb-private-2 --query 'RouteTables[0].Routes[?VpcEndpointId==`vpce-s3gateway123`]' --region us-east-1
```
