---
name: vpc-endpoint-policy-troubleshooter
description: >-
  Diagnoses Amazon VPC endpoint policy and connectivity failures across
  interface endpoints (PrivateLink), Gateway endpoints (S3/DynamoDB),
  and endpoint services (NLB-backed). Covers endpoint policy evaluation
  (default full access vs custom policy), security group on interface
  endpoint ENIs (inbound from client subnet on service port), DNS
  resolution (private hosted zone for endpoint DNS name, interface
  endpoint private DNS), cross-account endpoint access (resource policy
  plus IAM), Gateway endpoint routing (must be in route table), endpoint
  service connection timeouts (health check from endpoint service),
  endpoint DNS name resolution failures, endpoint policy JSON syntax
  errors, and PrivateLink endpoint service availability. Emits a
  ROOT_CAUSE_IDENTIFIED diagnosis with specific evidence citations and
  remediation commands, or INSUFFICIENT_DATA when more diagnostics are
  needed. Use when troubleshooting VPC endpoint connection failures,
  PrivateLink connection timeouts, endpoint policy access denied, S3 or
  DynamoDB Gateway endpoint routing, endpoint DNS resolution, or
  cross-account PrivateLink access. Triggers - vpc endpoint connection
  failure, privatelink timeout, endpoint policy denied, gateway endpoint
  route table, endpoint dns resolution, cross-account endpoint, nlb
  endpoint service, endpoint security group.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). For live diagnosis - AWS CLI v2 with ec2, sts, and
  route53 access. Works with Terraform aws_vpc_endpoint /
  aws_vpc_endpoint_policy / aws_security_group resources and
  CloudFormation AWS::EC2::VPCEndpoint templates.
keywords:
  - aws
  - vpc endpoint
  - vpc endpoint policy
  - privatelink
  - gateway endpoint
  - cloudops
  - troubleshoot
  - diagnose
  - interface endpoint
  - endpoint service
  - nlb
  - security group
  - route table
  - dns resolution
  - cross-account
  - s3 endpoint
  - dynamodb endpoint
tags:
  - aws
  - vpc-endpoint
  - privatelink
  - gateway-endpoint
  - cloudops
  - troubleshoot
  - networking
  - diagnose
  - endpoint-policy
  - security-group
  - route-table
  - dns-resolution
  - cross-account
dependencies:
  - aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: Networking
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA"
  version: 0.1.0
  author: "Jacky Chan — AWS Community Builder"
  tags:
    - aws
    - vpc-endpoint
    - privatelink
    - gateway-endpoint
    - cloudops
    - troubleshoot
    - networking
    - diagnose
    - endpoint-policy
    - security-group
    - route-table
    - dns-resolution
    - cross-account
  dependencies:
    - aws-orchestrator
  keywords:
    - vpc endpoint connection failure
    - privatelink timeout
    - endpoint policy denied
    - gateway endpoint route table
    - endpoint dns resolution
    - cross-account endpoint
    - nlb endpoint service
    - endpoint security group
  when_to_use: >-
    Invoke when the user wants to troubleshoot VPC endpoint connectivity
    failures, endpoint policy access denied errors, interface endpoint
    (PrivateLink) connection timeouts, Gateway endpoint (S3/DynamoDB)
    routing issues, endpoint DNS name resolution failures, cross-account
    endpoint access, or endpoint service (NLB-backed) availability. Do
    NOT invoke for VPC peering connectivity, Transit Gateway routing, or
    VPN/Direct Connect troubleshooting.
---

# VPC Endpoint Policy Troubleshooter

An AWS CloudOps agent skill that diagnoses VPC endpoint policy and
connectivity failures with methodical root-cause analysis. The skill
walks the operator through the three-layer endpoint model (IAM policy,
endpoint policy, security group), interface endpoint (PrivateLink)
connectivity, Gateway endpoint (S3/DynamoDB) routing, DNS resolution,
cross-account access, and endpoint service health, captures diagnostic
evidence at each layer, explains why each layer matters, and emits a
ROOT_CAUSE_IDENTIFIED diagnosis with copy-pasteable remediation commands
or INSUFFICIENT_DATA when more diagnostics are required.

## Activation keywords

VPC endpoint connection failure, PrivateLink timeout, endpoint policy
denied, Gateway endpoint route table, endpoint DNS resolution, cross-
account endpoint, NLB endpoint service, endpoint security group.

## STRICT output contract

When this skill is invoked with a VPC-endpoint-troubleshooting request
(endpoint connection failure, access denied, timeout, DNS resolution
issue, policy evaluation, or a partial diagnostic), the agent MUST
respond with the ROOT_CAUSE_IDENTIFIED diagnosis block defined in the
"Output format" section using the literal all-caps labels
`VPC_ENDPOINT:`, `VERDICT:`, `DIAGNOSIS:`, `EVIDENCE:`, and
`REMEDIATION_COMMANDS:`. Do NOT preface the diagnosis with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
diagnostic pipelines rely on; deviating from the literal labels breaks
automation silently.

If insufficient diagnostic data is available, the verdict is
`INSUFFICIENT_DATA` with specific evidence gaps cited in the diagnosis
(marked `[?]`), and `ROOT_CAUSE_IDENTIFIED` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Diagnostic prerequisites | Always — gather before diagnosing |
| Layer model overview | Understand the three-layer evaluation |
| Layer 1 — Security group (interface endpoint ENI) | Most common failure |
| Layer 2 — Endpoint policy (separate IAM layer) | Policy evaluation |
| Layer 3 — DNS resolution (interface endpoint DNS) | DNS failures |
| Layer 4 — Route table (Gateway endpoint) | S3/DynamoDB routing |
| Layer 5 — Cross-account endpoint access | Resource policy + IAM |
| Layer 6 — Endpoint service (NLB-backed) health | Service-side failures |
| Layer 7 — Connection timeout (health check) | Timeout root cause |
| Layer 8 — Endpoint policy JSON syntax | Syntax errors |
| Layer 9 — PrivateLink endpoint service availability | Outage diagnostics |
| NEVER do these things | Review before signing off |
| Output format | The literal diagnosis template |
| references/endpoint-policy-and-sg.md | Policy + SG detail |
| references/gateway-endpoint-and-dns.md | Gateway endpoint + DNS detail |

## Mindset

**One-line takeaway:** A VPC endpoint connection succeeds only if ALL
three layers pass: the security group on the interface endpoint ENI
allows inbound traffic from the client subnet on the service port, the
endpoint policy permits the requested action, and DNS resolves the
endpoint name to the private ENI IP. For Gateway endpoints, the route
table must explicitly include the endpoint. The endpoint policy is a
SEPARATE IAM layer evaluated AFTER the IAM policy — a request can pass
IAM but fail the endpoint policy.

Three misconceptions dominate VPC endpoint troubleshooting failures:

- **"The endpoint policy is the same as IAM."** It is NOT. The endpoint
  policy is an ADDITIONAL IAM layer attached to the endpoint itself.
  Evaluation order is: IAM policy (caller identity) THEN endpoint policy
  (attached to the VPC endpoint). A request can pass the caller's IAM
  policy but be denied by the endpoint policy. The default endpoint
  policy allows full access; a custom policy can restrict it. Missing
  this dual-layer evaluation is the #1 cause of "access denied" mysteries
  on endpoints.

- **"The security group on the interface endpoint does not matter."** It
  DOES. An interface endpoint creates ENIs in the specified subnets with
  attached security groups. The client sends traffic to the ENI's private
  IP. If the endpoint's security group does not allow inbound on the
  service port (e.g., 443 for most PrivateLink services) from the client
  subnet, the connection times out. This is the #1 cause of "endpoint
  connection timeout" tickets.

- **"Gateway endpoints work automatically once created."** They do NOT.
  A Gateway endpoint (S3/DynamoDB) must be explicitly added to the route
  table(s) for the affected subnets. Without the route table entry,
  traffic to S3/DynamoDB goes via the NAT Gateway (incurring cost) or
  fails entirely. The route table entry is added automatically only for
  the VPC's main route table; custom route tables need manual addition.

## Configuration dependency graph (novel heuristic)

VPC endpoint configurations are layered. Security group, endpoint
policy, DNS, route table, and endpoint service health are evaluated in
sequence. Use this graph to isolate the failing layer.

| Layer | Hard failure (connection drops) | Silent failure / misconfig | Diagnostic signal |
|---|---|---|---|
| Security group (interface endpoint ENI) | Connection timeout (SYN dropped) | SG allows wrong port or source | Connection hangs, no response |
| Endpoint policy (custom) | Access denied (403) | Policy allows principals but not actions, or vice versa | HTTP 403 from endpoint |
| DNS resolution (interface endpoint) | DNS name does not resolve | Private DNS not enabled, PHZ not associated | NXDOMAIN or wrong IP |
| Route table (Gateway endpoint) | Traffic goes via NAT (cost) | Gateway endpoint not in route table | S3 traffic not using endpoint prefix |
| Cross-account (resource policy) | Access denied across accounts | Endpoint service resource policy missing consumer account | 403 from endpoint service |
| Endpoint service (NLB) health | Connection refused or timeout | NLB target unhealthy, listener misconfigured | Intermittent failures, health check failures |
| Endpoint policy JSON syntax | Endpoint creation or update fails | Trailing comma, missing bracket, invalid principal | API error on modify |

**The security group row is the one a baseline model misses.** The
endpoint's own SG must allow inbound traffic from the client subnet.
This is the #1 cause of interface endpoint connection timeouts. The
endpoint policy row is the #2 most missed — the policy is a separate
IAM layer from the caller's IAM permissions.

**Cross-dependency gotchas:**
- The endpoint policy is evaluated AFTER the IAM policy. Passing IAM is
  necessary but not sufficient — the endpoint policy must also allow the
  action.
- Interface endpoint DNS resolution requires private DNS to be enabled
  (for AWS services) or a private hosted zone to be associated (for non-
  AWS services). Without this, the endpoint DNS name resolves to the
  wrong IP or does not resolve at all.
- Gateway endpoints do NOT use security groups or DNS. They route via
  the route table. An S3 Gateway endpoint without a route table entry
  sends traffic via the NAT Gateway instead.
- Cross-account PrivateLink requires BOTH the consumer's IAM/endpoint
  policy AND the service provider's endpoint service resource policy to
  allow access. Either side can block access.
- The endpoint service (NLB-backed) health check determines whether the
  NLB forwards traffic. Unhealthy targets cause connection failures that
  look like endpoint policy issues.

## Expert heuristic: the three-layer evaluation model

A baseline model checks "is the endpoint created?" The correct heuristic
recognizes that an endpoint connection passes through three independent
evaluation layers, each of which can block traffic independently.

```text
Client (10.0.1.5) → DNS resolve endpoint name → ENI IP (10.0.1.10)

Layer 1 - Security Group (ENI):
  Does the endpoint's SG allow inbound from client subnet on service port?
  ├── YES → traffic reaches endpoint ENI
  └── NO  → connection TIMEOUT (SYN dropped silently)

Layer 2 - Endpoint Policy:
  Does the endpoint policy allow this action/principal?
  ├── YES → request forwarded to service
  └── NO  → HTTP 403 ACCESS DENIED

Layer 3 - DNS Resolution:
  Does the endpoint DNS name resolve to the ENI's private IP?
  ├── YES → client connects to the right IP
  └── NO  → NXDOMAIN or resolves to public IP (bypasses endpoint)

For Gateway endpoints (S3/DynamoDB), the model differs:
  Layer 1 - Route Table:
    Is the Gateway endpoint in the subnet's route table?
    ├── YES → S3/DynamoDB traffic uses the endpoint
    └── NO  → traffic goes via NAT Gateway (cost, latency)
  (No SG, no DNS, no endpoint policy for Gateway endpoints)
```

**Key implication:** the #1 cause of "endpoint connection timeout" is a
missing security group rule on the endpoint ENI. The #1 cause of
"endpoint access denied" is a restrictive endpoint policy. These are
different layers with different symptoms — the diagnosis must test each
layer independently.

## Expert heuristic: interface vs Gateway endpoint differences

Interface endpoints (PrivateLink) and Gateway endpoints (S3/DynamoDB)
have fundamentally different architectures. Confusing them leads to
wrong diagnoses.

| Feature | Interface endpoint | Gateway endpoint |
|---|---|---|
| Service type | PrivateLink (any supported service) | S3, DynamoDB only |
| Connectivity | ENI in your VPC (private IP) | Route table entry (prefix list) |
| Security group | Required (on the ENI) | Not applicable |
| DNS | Private DNS or PHZ required | Not applicable (uses route table) |
| Endpoint policy | Supported (custom JSON) | Supported (custom JSON) |
| Cost | Per-endpoint hourly + per-GB data | Free (no hourly, no per-GB) |
| Cross-VPC | Supported (peering, TGW) | Not supported (single VPC) |
| Health check | NLB target health (for endpoint services) | N/A |

```text
Diagnosis decision tree:
  Is the endpoint for S3 or DynamoDB?
  ├── YES → Gateway endpoint
  │     Check: route table entry? prefix list? endpoint policy?
  │     SKIP: security group, DNS, ENI
  └── NO  → Interface endpoint (PrivateLink)
        Check: security group on ENI? private DNS? endpoint policy?
        SKIP: route table (interface endpoints do not use route tables)
```

**Key implication:** the most common diagnostic error is checking
security groups on a Gateway endpoint (which does not use them) or
checking route tables on an interface endpoint (which does not use them
for endpoint traffic). Identify the endpoint type first.

## Expert heuristic: endpoint policy as a separate IAM layer

The endpoint policy is NOT the caller's IAM policy. It is a separate
policy document attached to the VPC endpoint that controls which AWS
service actions can be performed through the endpoint.

```text
Request evaluation order:
  1. IAM policy (caller identity)
       Does the caller's IAM policy allow ec2:DescribeInstances?
       ├── NO → IAM denies (before the endpoint is involved)
       └── YES → continue to endpoint policy

  2. Endpoint policy (attached to VPC endpoint)
       Does the endpoint policy allow ec2:DescribeInstances for this principal?
       ├── NO → endpoint denies (HTTP 403 from endpoint)
       └── YES → request reaches the AWS service

  BOTH must allow the action. Either can deny.
```

Default endpoint policy (full access):

```json
{
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": "*",
      "Action": "*",
      "Resource": "*"
    }
  ]
}
```

A restrictive endpoint policy may limit actions, principals, or
resources:

```json
{
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::123456789012:role/MyAppRole"
      },
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::my-bucket",
        "arn:aws:s3:::my-bucket/*"
      ]
    }
  ]
}
```

**Key implication:** when a request passes IAM but gets a 403 from the
endpoint, the endpoint policy is the likely cause. Compare the endpoint
policy with the requested action and principal.

## Diagnostic prerequisites (gather before diagnosing)

Before emitting a diagnosis, gather these prerequisites. If critical
data is missing, the verdict is **INSUFFICIENT_DATA**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Endpoint ID | Identifies the endpoint to diagnose | `aws ec2 describe-vpc-endpoints` |
| Endpoint type (interface or gateway) | Determines which layers to check | `describe-vpc-endpoints --query 'VpcEndpoints[0].VpcEndpointType'` |
| Service name | Identifies the AWS or PrivateLink service | `describe-vpc-endpoints --query 'VpcEndpoints[0].ServiceName'` |
| Endpoint state | Pending/available/failed determines baseline | `describe-vpc-endpoints --query 'VpcEndpoints[0].State'` |
| Security group IDs (interface) | Must allow inbound on service port from client | `describe-network-interfaces` for endpoint ENIs |
| Endpoint policy JSON | Must allow the requested action/principal | `describe-vpc-endpoints --query 'VpcEndpoints[0].PolicyDocument'` |
| Route table (gateway) | Must include the gateway endpoint | `describe-route-tables` for affected subnets |
| DNS configuration | Private DNS enabled? PHZ associated? | `describe-vpc-endpoints --query 'VpcEndpoints[0].PrivateDnsEnabled'` |
| Client subnet CIDR | SG inbound must allow this source | `describe-subnets` |
| Error symptom | Timeout vs 403 vs NXDOMAIN narrows the layer | Ask the operator or check logs |

If any critical prerequisite is missing, output
`VERDICT: INSUFFICIENT_DATA` and cite the specific data gap.

## Layer 1 — Security group (interface endpoint ENI)

An interface endpoint creates ENIs in the specified subnets. Each ENI
has a security group. The client sends traffic to the ENI's private IP
address. If the SG does not allow inbound on the service port from the
client subnet, the connection times out.

**This is the #1 cause of interface endpoint connection timeouts.**

**Verify the endpoint's security group:**

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

**Common SG failure:**

```text
Endpoint SG inbound rules:
  Port 443 (TCP)  Source 10.0.0.0/16  ← allows VPC-wide
  Port 443 (TCP)  Source 10.0.1.0/24  ← allows only subnet-1

Client is in subnet-2 (10.0.2.0/24) → TIMEOUT (no matching inbound rule)
```

**Fix: add inbound rule from client subnet:**

```bash
aws ec2 authorize-security-group-ingress \
  --group-id sg-vpce123 \
  --protocol tcp \
  --port 443 \
  --cidr 10.0.2.0/24 \
  --region us-east-1
```

**Critical:** the SG must allow inbound on the SERVICE PORT. For most
PrivateLink services this is TCP 443. For some services (e.g., a custom
endpoint service behind an NLB) it may be a different port (e.g., 8080).
Check the service's documentation or the NLB listener configuration.

## Layer 2 — Endpoint policy (separate IAM layer)

The endpoint policy is a separate IAM policy attached to the VPC
endpoint. It is evaluated AFTER the caller's IAM policy. A request can
pass IAM but fail the endpoint policy.

**Retrieve the endpoint policy:**

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

**Verify the endpoint policy allows the requested action:**

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

**Default policy (full access):** if `PolicyDocument` is empty or null,
the endpoint uses the default policy (full access). In that case, the
endpoint policy is NOT the blocker.

**Custom policy failure:**

```text
Endpoint policy:
  Allow: s3:GetObject on arn:aws:s3:::bucket-a/*

Request: s3:PutObject on arn:aws:s3:::bucket-a/
→ ENDPOINT POLICY DENIES (action not in allowed list)
→ HTTP 403 Access Denied
```

**Fix: update the endpoint policy to include the action:**

```bash
aws ec2 modify-vpc-endpoint \
  --vpc-endpoint-id vpce-aaa111222 \
  --policy-document file://updated-policy.json \
  --region us-east-1
```

**Critical:** the endpoint policy is a SEPARATE IAM layer from the
caller's IAM policy. Both must allow the action. When diagnosing a 403,
check BOTH layers.

## Layer 3 — DNS resolution (interface endpoint DNS)

For interface endpoints, the endpoint DNS name must resolve to the
ENI's private IP. Two DNS modes exist:

1. **Private DNS enabled (for AWS services):** the service's default DNS
   name (e.g., `ec2.us-east-1.amazonaws.com`) resolves to the endpoint
   ENI's private IP. Must be enabled at creation or modified later.

2. **Private hosted zone (for non-AWS/PrivateLink services):** a Route
   53 private hosted zone must be associated with the VPC and configured
   to resolve the endpoint DNS name.

**Verify private DNS is enabled:**

```bash
aws ec2 describe-vpc-endpoints \
  --vpc-endpoint-ids vpce-aaa111222 \
  --query 'VpcEndpoints[0].PrivateDnsEnabled' \
  --output text --region us-east-1
# Expected: true (for AWS services with private DNS)
```

**Verify DNS resolution from a client instance:**

```bash
# From a client EC2 instance in the VPC
dig vpce-aaa111222-xxx.service-region.vpce.amazonaws.com
# Should return the ENI's private IP (e.g., 10.0.1.10)

# For AWS services with private DNS enabled
dig ec2.us-east-1.amazonaws.com
# Should return the endpoint ENI's private IP, NOT the public IP

# If it returns a public IP or NXDOMAIN → DNS is not routing through endpoint
```

**Common DNS failures:**

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

**Enable private DNS:**

```bash
aws ec2 modify-vpc-endpoint \
  --vpc-endpoint-id vpce-aaa111222 \
  --private-dns-enabled \
  --region us-east-1
```

## Layer 4 — Route table (Gateway endpoint)

Gateway endpoints (S3/DynamoDB) route traffic via a route table entry.
The endpoint must be explicitly added to each route table that should
use it. Traffic to the service prefix list (e.g., `pl-68a54001` for S3)
is routed through the endpoint.

**Verify the Gateway endpoint is in the route table:**

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

**Common Gateway endpoint routing failure:**

```text
Subnet route table (rtb-private-1):
  10.0.0.0/16 → local
  0.0.0.0/0   → nat-xxx
  (NO Gateway endpoint entry for S3 prefix list pl-68a54001)

Result: S3 traffic goes via NAT Gateway (costs money, not using endpoint)
Fix: add the Gateway endpoint to the route table
```

**Add a Gateway endpoint to a route table:**

```bash
aws ec2 modify-vpc-endpoint \
  --vpc-endpoint-id vpce-s3gateway123 \
  --add-route-table-ids rtb-private-1 rtb-private-2 \
  --region us-east-1
```

**Critical:** Gateway endpoints do NOT use security groups or DNS. They
route via the route table. If S3 or DynamoDB traffic is going via the
NAT Gateway instead of the endpoint, the route table is the issue.

## Layer 5 — Cross-account endpoint access (resource policy + IAM)

For cross-account PrivateLink access, BOTH the consumer's IAM/endpoint
policy AND the service provider's endpoint service resource policy must
allow access. Either side can block.

```text
Cross-account endpoint flow:
  Consumer account → Interface endpoint → Endpoint service (provider account)
                                                        ↓
                                           NLB → backend instances

  Access control (two independent layers):
    1. Consumer side: IAM policy + endpoint policy
       - Does the consumer's IAM policy allow the action?
       - Does the consumer's endpoint policy allow the action?
    2. Provider side: endpoint service resource policy
       - Does the endpoint service allow the consumer's account?

  Either layer can block access (403).
```

**Verify the endpoint service allows the consumer account:**

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

**Common cross-account failure:**

```text
Consumer account: 123456789012
Provider endpoint service: com.amazonaws.vpce.us-east-1.vpce-svc-xxx

Provider service allowed principals:
  arn:aws:iam::111111111111:root  ← only account A is allowed

Consumer account 123456789012 is NOT in the allowed list → 403

Fix: provider adds consumer account to allowed principals
```

## Layer 6 — Endpoint service (NLB-backed) connection failures

For custom endpoint services (your own PrivateLink service behind an
NLB), the NLB and its targets must be healthy for the endpoint to work.

**Verify the endpoint service configuration:**

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

**Common endpoint service failures:**

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

**Provider accepts the endpoint connection:**

```bash
# Provider account: accept pending endpoint connections
aws ec2 accept-vpc-endpoint-connections \
  --service-id vpce-svc-xxx \
  --vpc-endpoint-ids vpce-aaa111222 \
  --region us-east-1
```

## Layer 7 — Connection timeout (health check from endpoint service)

When a client connects to an interface endpoint and the connection times
out (no response, SYN dropped), the failure is at Layer 1 (security
group) or Layer 6 (endpoint service health). Distinguish between them:

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

## Layer 8 — Endpoint policy JSON syntax errors

A malformed endpoint policy JSON causes endpoint creation or update
failures. Common syntax errors include trailing commas, missing brackets,
and invalid principal values.

**Validate the endpoint policy JSON before applying:**

```bash
# Validate JSON syntax
echo '{"Statement":[{"Effect":"Allow","Principal":"*","Action":"*","Resource":"*"}]}' | python3 -m json.tool

# Common errors:
# - Trailing comma: {"Action":["s3:GetObject",]} ← remove trailing comma
# - Missing bracket: {"Statement":[{"Effect":"Allow"} ← close all brackets
# - Invalid principal: {"Principal":{"AWS":"account-id"}} ← must be ARN or "*"
# - String not quoted: {"Effect": Allow} ← quote the value: {"Effect": "Allow"}
```

**Policy with syntax error fails on modify:**

```bash
aws ec2 modify-vpc-endpoint \
  --vpc-endpoint-id vpce-aaa111222 \
  --policy-document file://broken-policy.json
# Error: InvalidPolicyDocument — policy document is malformed
```

## Layer 9 — PrivateLink endpoint service availability

If the endpoint service is unavailable (provider NLB deleted, backend
instances terminated), the endpoint will show failures.

**Verify the endpoint service is available:**

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

**Endpoint states indicating service issues:**

| State | Meaning | Action |
|---|---|---|
| `pending-waiting` | Provider has not accepted | Provider must accept |
| `pending-acceptance` | Waiting for provider acceptance | Provider must accept |
| `deleted` | Endpoint was deleted | Recreate |
| `failed` | Creation failed | Check error, recreate |
| `available` | Endpoint is up | Issue is NOT the endpoint state |

## NEVER do these things

1. **NEVER conflate the endpoint policy with the IAM policy.** They are
   separate layers. The endpoint policy is evaluated AFTER IAM. A request
   can pass IAM but fail the endpoint policy. Always check BOTH when
   diagnosing a 403.

2. **NEVER skip the security group check on interface endpoints.** The
   endpoint's own SG must allow inbound on the service port from the
   client subnet. This is the #1 cause of connection timeouts. Check the
   SG on the endpoint ENI, not just the client's SG.

3. **NEVER check route tables for interface endpoints.** Interface
   endpoints route traffic via the ENI's private IP, not the route
   table. Route table checks are only for Gateway endpoints (S3/DynamoDB).

4. **NEVER check security groups for Gateway endpoints.** Gateway
   endpoints route via the route table. They do NOT use ENIs or security
   groups. Confusing interface and Gateway endpoints leads to wrong
   diagnoses.

5. **NEVER assume private DNS is enabled by default.** For AWS services
   with interface endpoints, private DNS must be explicitly enabled
   (either at creation or modified later). Without it, the service DNS
   name resolves to the public IP, bypassing the endpoint.

6. **NEVER forget the cross-account resource policy.** For cross-account
   PrivateLink, the service provider's endpoint service resource policy
   must allow the consumer account. This is independent of the consumer's
   IAM and endpoint policy. Either side can block.

7. **NEVER diagnose a 403 as a network timeout.** A 403 is an HTTP
   response, meaning the network path works. The issue is policy (IAM or
   endpoint policy), not connectivity. A timeout (no response) is a
   network issue (SG or service health).

8. **NEVER apply an endpoint policy without validating JSON syntax.**
   Trailing commas, missing brackets, and invalid principal values cause
   the policy update to fail. Always validate the JSON before applying.

9. **NEVER assume the endpoint service (NLB-backed) is healthy.** For
   custom endpoint services, check the NLB target health from the
   provider account. Unhealthy targets cause intermittent or persistent
   connection failures.

10. **NEVER forget to check the endpoint state.** A `pending-waiting`
    endpoint has not been accepted by the provider. A `failed` endpoint
    had a creation error. Always check the endpoint state before diving
    into SG, policy, or DNS diagnostics.

## Output format

```text
VPC_ENDPOINT: <endpoint-id> (<endpoint-type> — <service-name>)
VERDICT: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
DIAGNOSIS:
  ROOT CAUSE: <layer name> — <specific failure description>
  FAILURE LAYER: Security Group | Endpoint Policy | DNS Resolution | Route Table | Cross-Account | Endpoint Service | JSON Syntax
  IMPACT: <what breaks for the client>
EVIDENCE:
  [✓|✗|?] Security group (interface): <SG-id> allows inbound on port <port> from <client-cidr> | MISSING inbound rule for <client-cidr>
  [✓|✗|?] Endpoint policy: default (full access) | custom policy denies <action> for <principal>
  [✓|✗|?] DNS resolution: private DNS enabled | private DNS disabled | PHZ not associated
  [✓|✗|?] Route table (gateway): endpoint <vpce-id> in route table <rtb-id> | endpoint NOT in route table
  [✓|✗|?] Cross-account: consumer account allowed in resource policy | consumer account NOT allowed
  [✓|✗|?] Endpoint service health: NLB targets healthy | NLB targets unhealthy (<reason>)
  [✓|✗|?] Endpoint state: available | <state>
  [✓|✗|?] Policy JSON syntax: valid | invalid (<error>)
REMEDIATION_COMMANDS:
  <copy-pasteable command to fix the identified root cause>
  <verification command>
```

### Worked example — interface endpoint SG missing inbound rule

```text
VPC_ENDPOINT: vpce-aaa111222 (Interface — com.amazonaws.us-east-1.ssm)
VERDICT: ROOT_CAUSE_IDENTIFIED
DIAGNOSIS:
  ROOT CAUSE: Security group sg-vpce123 does not allow inbound on port 443 from client subnet 10.0.2.0/24
  FAILURE LAYER: Security Group
  IMPACT: Clients in subnet 10.0.2.0/24 get connection timeout when accessing SSM via the endpoint
EVIDENCE:
  [✗] Security group (interface): sg-vpce123 allows inbound on port 443 from 10.0.0.0/16 and 10.0.1.0/24 only; MISSING inbound rule for 10.0.2.0/24
  [✓] Endpoint policy: default (full access)
  [✓] DNS resolution: private DNS enabled
  [N/A] Route table (gateway): not applicable (interface endpoint)
  [N/A] Cross-account: not applicable (same account)
  [✓] Endpoint service health: AWS service (SSM) — healthy
  [✓] Endpoint state: available
  [✓] Policy JSON syntax: valid (default policy)
REMEDIATION_COMMANDS:
  aws ec2 authorize-security-group-ingress --group-id sg-vpce123 --protocol tcp --port 443 --cidr 10.0.2.0/24 --region us-east-1
  # Verify: from a client in 10.0.2.0/24, run: telnet <eni-private-ip> 443
```

### Worked example — Gateway endpoint not in route table

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

## Error handling

### Connection timeout (no response from endpoint)
- Layer 1: Check the endpoint's security group for inbound rules from
  the client subnet on the service port. This is the #1 cause.
- Layer 6: If SG is correct, check the NLB target health (for custom
  endpoint services). Unhealthy targets cause timeouts.
- Layer 9: Verify the endpoint state is `available` (not
  `pending-waiting` or `failed`).

### HTTP 403 Access Denied from endpoint
- Layer 2: Check the endpoint policy. It may deny the requested action
  or principal. The policy is a SEPARATE layer from IAM.
- IAM: Verify the caller's IAM policy also allows the action. Both IAM
  and endpoint policy must allow.
- Layer 5: For cross-account, check the provider's endpoint service
  resource policy. The consumer account must be in the allowed
  principals.

### DNS does not resolve endpoint name
- Layer 3: Check if private DNS is enabled for the endpoint (AWS
  services). If not, enable it.
- Layer 3: For non-AWS services, check if a Route 53 private hosted zone
  is associated with the VPC.
- Verify the VPC has `enableDnsSupport` and `enableDnsHostnames` set to
  true.

### S3/DynamoDB traffic not using Gateway endpoint
- Layer 4: Check if the Gateway endpoint is in the route table for the
  affected subnet(s). Add it if missing.
- Verify the endpoint state is `available`.

### Endpoint policy update fails
- Layer 8: Validate the JSON syntax. Common errors are trailing commas,
  missing brackets, and invalid principal values.
- Use `python3 -m json.tool` or `jq` to validate before applying.

## Domain

AWS CloudOps / Amazon VPC Endpoint Policy & PrivateLink Connectivity
Diagnostics.

## AWS documentation

- **VPC endpoints overview** — https://docs.aws.amazon.com/vpc/latest/privatelink/concepts.html
- **Interface endpoints** — https://docs.aws.amazon.com/vpc/latest/privatelink/create-interface-endpoint.html
- **Gateway endpoints** — https://docs.aws.amazon.com/vpc/latest/endpoint/gateway-endpoints.html
- **Endpoint policies** — https://docs.aws.amazon.com/vpc/latest/privatelink/vpc-endpoints-policies.html
- **PrivateLink services** — https://docs.aws.amazon.com/vpc/latest/privatelink/privatelink-share-your-services.html
- **Security groups for endpoints** — https://docs.aws.amazon.com/vpc/latest/privatelink/create-interface-endpoint.html#interface-endpoint-security-groups
- **DNS for endpoints** — https://docs.aws.amazon.com/vpc/latest/privatelink/privatelink-interface-endpoints.html#private-dns
- **Cross-account access** — https://docs.aws.amazon.com/vpc/latest/privatelink/access-control-overview.html
- **Endpoint service permissions** — https://docs.aws.amazon.com/vpc/latest/privatelink/manage-endpoint-service.html#add-remove-permissions
