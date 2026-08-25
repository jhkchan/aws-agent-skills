---
name: vpc-endpoint-policy-troubleshooter
description: Diagnoses Amazon VPC endpoint policy and connectivity failures across interface endpoints (PrivateLink), Gateway endpoints (S3/DynamoDB), and endpoint services (NLB-backed). Covers endpoint policy evaluation (default vs custom), security group on interface endpoint ENIs (inbound from client subnet on service port), DNS resolution (private DNS, private hosted zone), cross-account access (resource policy plus IAM), Gateway endpoint routing (must be in route table), endpoint service timeouts, and policy JSON syntax errors. Emits ROOT_CAUSE_IDENTIFIED with remediation commands, or INSUFFICIENT_DATA when more diagnostics are needed. Use when troubleshooting endpoint connection failures, PrivateLink timeouts, endpoint policy access denied, S3 or DynamoDB Gateway routing, endpoint DNS resolution, or cross-account PrivateLink. Triggers - vpc endpoint failure, privatelink timeout, endpoint policy denied, gateway endpoint route, endpoint dns, cross-account endpoint, nlb endpoint service.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live diagnosis - AWS CLI v2 with ec2, sts, and route53 access. Works with Terraform aws_vpc_endpoint / aws_vpc_endpoint_policy / aws_security_group resources and CloudFormation AWS::EC2::VPCEndpoint templates.
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Networking
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, vpc-endpoint, privatelink, gateway-endpoint, cloudops, troubleshoot, networking, diagnose, endpoint-policy, security-group, route-table, dns-resolution, cross-account
  dependencies: aws-orchestrator
  keywords: aws, vpc endpoint, vpc endpoint policy, privatelink, gateway endpoint, cloudops, troubleshoot, diagnose, interface endpoint, endpoint service, nlb, security group, route table, dns resolution, cross-account, s3 endpoint, dynamodb endpoint
  when_to_use: Invoke when the user wants to troubleshoot VPC endpoint connectivity failures, endpoint policy access denied errors, interface endpoint (PrivateLink) connection timeouts, Gateway endpoint (S3/DynamoDB) routing issues, endpoint DNS name resolution failures, cross-account endpoint access, or endpoint service (NLB-backed) availability. Do NOT invoke for VPC peering connectivity, Transit Gateway routing, or VPN/Direct Connect troubleshooting.
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

The three misconception deep-dives (endpoint policy vs IAM, the endpoint's own SG, Gateway endpoint route-table entries) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when the operator asserts one of them.

## Configuration dependency graph (novel heuristic)

The dependency graph table (hard vs silent failure per layer, diagnostic signals) plus cross-dependency gotchas moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand to map a failure signal to its layer.

## Expert heuristic: the three-layer evaluation model

The three-layer evaluation tree (SG on the ENI, endpoint policy, DNS — plus the Gateway endpoint route-table variant) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand for the per-layer YES/NO walkthrough.

## Expert heuristic: interface vs Gateway endpoint differences

The interface-vs-Gateway comparison table and the endpoint-type diagnosis decision tree moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when the endpoint type is unclear.

## Expert heuristic: endpoint policy as a separate IAM layer

The IAM-then-endpoint-policy evaluation order, the default full-access policy JSON, and the restrictive policy example moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand on any endpoint 403.

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

Layer 1 ENI and SG probe commands moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand to run the probe or apply the fix.

**Common SG failure:**

Common-failure illustration moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when interpreting the probe output.

**Fix: add inbound rule from client subnet:**

Layer 1 fix command (authorize-security-group-ingress) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand to run the probe or apply the fix.

**Critical:** the SG must allow inbound on the SERVICE PORT. For most
PrivateLink services this is TCP 443. For some services (e.g., a custom
endpoint service behind an NLB) it may be a different port (e.g., 8080).
Check the service's documentation or the NLB listener configuration.

## Layer 2 — Endpoint policy (separate IAM layer)

The endpoint policy is a separate IAM policy attached to the VPC
endpoint. It is evaluated AFTER the caller's IAM policy. A request can
pass IAM but fail the endpoint policy.

**Retrieve the endpoint policy:**

Layer 2 policy-retrieval commands moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand to run the probe or apply the fix.

**Verify the endpoint policy allows the requested action:**

Layer 2 policy-decoding verification commands moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand to run the probe or apply the fix.

**Default policy (full access):** if `PolicyDocument` is empty or null,
the endpoint uses the default policy (full access). In that case, the
endpoint policy is NOT the blocker.

**Custom policy failure:**

Common-failure illustration moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when interpreting the probe output.

**Fix: update the endpoint policy to include the action:**

Layer 2 fix command (modify-vpc-endpoint) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand to run the probe or apply the fix.

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

Layer 3 private-DNS verification command moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand to run the probe or apply the fix.

**Verify DNS resolution from a client instance:**

Layer 3 dig-based DNS verification commands moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand to run the probe or apply the fix.

**Common DNS failures:**

Common-failure illustration moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when interpreting the probe output.

**Enable private DNS:**

Layer 3 fix command (modify-vpc-endpoint --private-dns-enabled) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand to run the probe or apply the fix.

## Layer 4 — Route table (Gateway endpoint)

Gateway endpoints (S3/DynamoDB) route traffic via a route table entry.
The endpoint must be explicitly added to each route table that should
use it. Traffic to the service prefix list (e.g., `pl-68a54001` for S3)
is routed through the endpoint.

**Verify the Gateway endpoint is in the route table:**

Layer 4 Gateway endpoint route-table verification commands moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand to run the probe or apply the fix.

**Common Gateway endpoint routing failure:**

Common-failure illustration moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when interpreting the probe output.

**Add a Gateway endpoint to a route table:**

Layer 4 fix command (modify-vpc-endpoint --add-route-table-ids) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand to run the probe or apply the fix.

**Critical:** Gateway endpoints do NOT use security groups or DNS. They
route via the route table. If S3 or DynamoDB traffic is going via the
NAT Gateway instead of the endpoint, the route table is the issue.

## Layer 5 — Cross-account endpoint access (resource policy + IAM)

For cross-account PrivateLink access, BOTH the consumer's IAM/endpoint
policy AND the service provider's endpoint service resource policy must
allow access. Either side can block.

The cross-account endpoint flow diagram (consumer IAM/endpoint policy vs provider resource policy) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand for the two-sided access-control model.

**Verify the endpoint service allows the consumer account:**

Layer 5 allowed-principals verification and fix commands moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand to run the probe or apply the fix.

**Common cross-account failure:**

Common-failure illustration moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when interpreting the probe output.

## Layer 6 — Endpoint service (NLB-backed) connection failures

For custom endpoint services (your own PrivateLink service behind an
NLB), the NLB and its targets must be healthy for the endpoint to work.

**Verify the endpoint service configuration:**

Layer 6 endpoint service and NLB target-health probe commands moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand to run the probe or apply the fix.

**Common endpoint service failures:**

Common-failure illustration moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when interpreting the probe output.

**Provider accepts the endpoint connection:**

Layer 6 accept-vpc-endpoint-connections command moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand to run the probe or apply the fix.

## Layer 7 — Connection timeout (health check from endpoint service)

When a client connects to an interface endpoint and the connection times
out (no response, SYN dropped), the failure is at Layer 1 (security
group) or Layer 6 (endpoint service health). Distinguish between them:

The three-test timeout decision tree (telnet to the ENI IP, NLB target health, endpoint policy) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when the endpoint connection times out.

## Layer 8 — Endpoint policy JSON syntax errors

A malformed endpoint policy JSON causes endpoint creation or update
failures. Common syntax errors include trailing commas, missing brackets,
and invalid principal values.

**Validate the endpoint policy JSON before applying:**

Layer 8 JSON validation command and common syntax errors moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand to run the probe or apply the fix.

**Policy with syntax error fails on modify:**

Layer 8 broken-policy modify example moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand to run the probe or apply the fix.

## Layer 9 — PrivateLink endpoint service availability

If the endpoint service is unavailable (provider NLB deleted, backend
instances terminated), the endpoint will show failures.

**Verify the endpoint service is available:**

Layer 9 endpoint service availability probe commands moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand to run the probe or apply the fix.

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

Moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when formatting a Route Table verdict.

## Error handling

The symptom-to-layer error-handling playbook (timeout, 403, DNS, S3/DynamoDB NAT bypass, policy-update failures) moved verbatim to [references/error-handling.md](references/error-handling.md).
Load on demand when mapping a symptom to its layer.

## References (load on demand)

- [Advanced patterns](references/advanced-patterns.md) — mindset misconceptions, the configuration dependency graph, the three-layer evaluation model, interface vs Gateway differences, endpoint policy as a separate IAM layer, cross-account flow
- [Diagnostic commands](references/diagnostic-commands.md) — per-layer probe and fix command listings (Layers 1-4, 5, 6, 8, 9) plus the Layer 7 timeout decision tree
- [Worked examples](references/worked-examples.md) — secondary worked example (Gateway endpoint not in route table) and per-layer common-failure illustrations
- [Error handling](references/error-handling.md) — symptom-to-layer error-handling playbook
- [Endpoint policy and SG](references/endpoint-policy-and-sg.md) — endpoint policy evaluation, SG configuration for endpoint ENIs, policy JSON validation
- [Gateway endpoint and DNS](references/gateway-endpoint-and-dns.md) — Gateway endpoint routing, DNS resolution for interface endpoints, endpoint service health

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
