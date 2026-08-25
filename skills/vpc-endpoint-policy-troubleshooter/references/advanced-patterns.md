# Advanced Patterns — VPC Endpoint Policy Troubleshooter

Expert-heuristic deep dives, misconception catalogs, and evaluation-model detail moved out of the SKILL.md body. Loaded on demand.

## Mindset — the three misconceptions

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

## Cross-account endpoint flow diagram (from Layer 5)

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
