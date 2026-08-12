---
name: vpclattice-service-deployer
description: >-
  Provisions Amazon VPC Lattice services with production defaults:
  service network creation (top-level routing plane), service (HTTP/gRPC),
  target group (instance/IP/Lambda/ALB), listener rules (path-based,
  header-based, method-based routing), IAM auth policy (service-level not
  rule-level), resource-based service policy, target group health checks
  (determines routing eligibility), cross-account service access, custom
  domain name mapping, service network VPC association, traffic splitting
  for canary deployments, access log delivery to CloudWatch/S3, and
  pricing per GB processed. Emits a READY_TO_DEPLOY checklist with
  verification commands. Use when creating a VPC Lattice service network,
  configuring Lattice services, setting up target groups, defining
  listener rules, applying IAM auth policies, enabling access logs, or
  configuring canary traffic splitting. Triggers: create vpc lattice
  service network, vpc lattice target group, vpc lattice listener rule,
  vpc lattice auth policy, vpc lattice traffic splitting, vpc lattice
  custom domain, vpc lattice service network vpc association, vpc lattice
  cross-account access, vpc lattice access logs, vpc lattice health check.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). For live deployment: AWS CLI v2 with vpc-lattice
  access. Works with Terraform aws_vpclattice_service_network /
  aws_vpclattice_service / aws_vpclattice_target_group /
  aws_vpclattice_listener resources and CloudFormation
  AWS::VpcLattice::ServiceNetwork / Service / TargetGroup templates.
keywords:
  - aws
  - vpc lattice
  - service network
  - lattice service
  - target group
  - listener rule
  - cloudops
  - deploy
  - provisioning
  - auth policy
  - traffic splitting
  - canary
  - custom domain
  - health check
  - access logs
  - cross-account
tags:
  - aws
  - vpc-lattice
  - service-network
  - cloudops
  - deploy
  - networking
  - provisioning
  - auth-policy
  - traffic-splitting
  - canary
  - health-check
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
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  version: 0.1.0
  author: "Jacky Chan — AWS Community Builder"
  tags:
    - aws
    - vpc-lattice
    - service-network
    - cloudops
    - deploy
    - networking
    - provisioning
    - auth-policy
    - traffic-splitting
    - canary
    - health-check
  dependencies:
    - aws-orchestrator
  keywords:
    - create vpc lattice service network
    - vpc lattice target group
    - vpc lattice listener rule
    - vpc lattice auth policy
    - vpc lattice traffic splitting
    - vpc lattice custom domain
    - vpc lattice service network vpc association
    - vpc lattice cross-account access
    - vpc lattice access logs
    - vpc lattice health check
  when_to_use: >-
    Invoke when the user wants to create an Amazon VPC Lattice service
    network, provision Lattice services (HTTP or gRPC), configure target
    groups (instance/IP/Lambda/ALB), define listener rules (path-based,
    header-based, method-based routing), apply IAM auth policies at the
    service level, set up resource-based service policies, configure
    target group health checks, enable cross-account service access, map
    custom domain names, associate VPCs with a service network, configure
    traffic splitting for canary deployments, or deliver access logs to
    CloudWatch/S3. Do NOT invoke for AWS Transit Gateway, VPC peering,
    ALB/NLB provisioning, or API Gateway (HTTP API).
---

# VPC Lattice Service Deployer

An AWS CloudOps agent skill that provisions Amazon VPC Lattice services
with correct defaults. The skill walks the operator through service
network creation, service and target group provisioning, listener rule
configuration, IAM auth policy at the service level, health check setup,
cross-account access, custom domain mapping, VPC association, traffic
splitting, and access log delivery. It captures topology and routing
decisions, explains why each default matters, and emits a
READY_TO_DEPLOY checklist with copy-pasteable verification commands.

## Activation keywords

create VPC Lattice service network, VPC Lattice target group, VPC
Lattice listener rule, VPC Lattice auth policy, VPC Lattice traffic
splitting, VPC Lattice custom domain, VPC Lattice service network VPC
association, VPC Lattice cross-account access, VPC Lattice access logs,
VPC Lattice health check.

## STRICT output contract

When this skill is invoked with a VPC Lattice provisioning request
(create a service network, configure a service, set up target groups,
define listener rules, apply auth policy, configure traffic splitting,
enable access logs, or a partial configuration), the agent MUST respond
with the READY_TO_DEPLOY checklist defined in the "Output format"
section using the literal all-caps labels `VPC_LATTICE:`, `VERDICT:`,
`CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT preface the checklist
with prose, headings, or disclaimers — emit the block as the first lines
of the response. This contract is what assertion-based evals and
downstream provisioning pipelines rely on; deviating from the literal
labels breaks automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Service network (top-level routing plane) | Core Lattice model |
| Step 2 — Target group (type selection + health checks) | Routing eligibility |
| Step 3 — Service (HTTP/gRPC) | Service provisioning |
| Step 4 — Listener rules (path/header/method routing) | Traffic routing |
| Step 5 — IAM auth policy (service level, NOT rule level) | Auth model |
| Step 6 — Resource-based service policy | Access control |
| Step 7 — Service network VPC association | VPC enablement |
| Step 8 — Cross-account service access | Multi-account topology |
| Step 9 — Custom domain name mapping | DNS + TLS |
| Step 10 — Traffic splitting (canary) | Weighted routing |
| Step 11 — Access log delivery | Observability |
| Step 12 — Pricing (per GB processed) | Cost model |
| Step 13 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/auth-policy-and-access.md | Auth + policy detail |
| references/listener-rules-and-health.md | Routing + health detail |

## Mindset

**One-line takeaway:** VPC Lattice is an application networking service
that connects, secures, and monitors communications across VPCs and
accounts. The service network is the top-level routing plane (typically
1 per account). Target group health check status determines whether a
target receives traffic. The IAM auth policy applies at the SERVICE
level — NOT at the individual listener rule level.

Three misconceptions dominate VPC Lattice misdesign at provisioning
time:

- **"Auth policies can be scoped per listener rule."** They CANNOT. The
  IAM auth policy attaches to the SERVICE resource, not individual
  listener rules. If you need different auth semantics per path, you
  need separate services — not separate rules within one service. A
  baseline model may try to attach an auth policy to a specific rule;
  this does not exist in the API.

- **"Unhealthy targets still receive traffic."** They do NOT. VPC
  Lattice only routes to targets whose health check is passing. If ALL
  targets in a target group are unhealthy, Lattice returns 503 (no
  healthy targets). Health check configuration determines routing
  eligibility, not an optional monitoring feature.

- **"The service network is per VPC."** It is NOT. The service network
  is an account-level construct (up to 1 per account in the default
  limit). VPCs are ASSOCIATED with a service network via VPC
  association. Multiple VPCs (and cross-account VPCs) can be associated
  with the same service network.

## Configuration dependency graph (novel heuristic)

VPC Lattice configurations are NOT independent. The service network
must exist before services. Target groups must exist before listener
rules reference them. Health check status determines routing. IAM auth
policies apply at the service level. Use this graph to sequence
provisioning.

| Configuration | Hard dependencies | Silent failure | Enables downstream |
|---|---|---|---|
| Service network | none (top-level construct) | 1 per account typical; VPCs must be associated | service + VPC association |
| Target group | VPC (instance/IP/ALB) or Lambda (function exists) | health check config determines routing — unhealthy targets receive NO traffic | listener rule + traffic splitting |
| Service | service network exists; protocol chosen | service DNS name auto-assigned; auth policy attaches at service level | listener + auth policy |
| Listener rule | service + listener + target group exist | rules evaluated in priority order; first match wins; default rule is fallback | routing decision per request |
| IAM auth policy | service exists | attaches to SERVICE, not rules; must be explicitly put | auth enforcement for ALL paths |
| Service policy (resource-based) | service exists | IAM resource policy controls who can invoke | cross-account invocation |
| VPC association | service network + VPC exist | VPCs NOT associated cannot use Lattice DNS | in-VPC service reachability |
| Cross-account association | service network + RAM share | other account must accept RAM share; then associate VPC | cross-account service access |
| Custom domain | service + ACM cert in us-east-1 + DNS zone | cert must be in us-east-1 regardless of service region | custom URL for the service |
| Traffic splitting | listener rule with weighted forwarding | weights are per TG within a rule; sum need not be 100 | canary / blue-green routing |
| Access logs | service network or service exists | delivery is async; first logs within minutes | observability / audit trail |

**The service-network-before-everything row is the one a baseline model
misses.** A service cannot exist without a service network. A VPC cannot
use Lattice routing without association. The auth policy cannot be
applied without a service.

**Cross-dependency gotchas:**
- The IAM auth policy attaches at the SERVICE level and governs ALL
  listener rules and ALL paths. You CANNOT scope auth to a specific
  path or rule.
- Target group health check status determines routing eligibility. If
  the health check fails, Lattice routes ZERO traffic to that target.
  If all targets are unhealthy, clients see 503.
- VPC association is required for the VPC to resolve Lattice service DNS
  names. Without association, instances in the VPC cannot reach the
  service via its auto-assigned DNS name.
- Cross-account access requires BOTH a RAM resource share (sharing the
  service network) AND a resource-based service policy (allowing the
  other account to invoke the service).
- Custom domain names require an ACM certificate in us-east-1 (the
  Lattice-managed TLS region), regardless of the service's region.

## Expert heuristic: the three-tier Lattice model

A baseline model says "create a service." The correct heuristic
recognizes the three-tier hierarchy: service network (top) -> service
(middle) -> target group + listener rules (bottom).

```text
Account
  └── Service Network (top-level routing plane, 1 per account typical)
        ├── VPC Associations (which VPCs can use this network)
        │     ├── VPC-A (vpc-aaa11122)
        │     └── VPC-B (vpc-bbb22233)
        ├── Service: payments-svc (HTTP)
        │     ├── Auth Policy (IAM, at SERVICE level — covers ALL rules)
        │     ├── Service Policy (resource-based, for cross-account)
        │     ├── Listener (port 80, HTTP)
        │     │     ├── Rule 1 (priority 10): path /v2/* → TG-canary 20 + TG-stable 80
        │     │     └── Rule 2 (default): path * → TG-stable 100
        │     ├── Target Group: TG-stable (INSTANCE, port 8080, health /health)
        │     └── Target Group: TG-canary (INSTANCE, port 8080, health /health)
        └── Service: inventory-svc (gRPC)
              └── ...
```

**Key implication:** every resource hangs off the service network. The
service network is the first thing to create, and its VPC associations
determine which VPCs can reach the services.

## Expert heuristic: health check determines routing eligibility

A baseline model treats health checks as monitoring. In VPC Lattice,
health checks are a routing input — not just observability.

```text
Request → Listener → Rule match → Target Group
                                    ├── Target 1: HEALTHY   → receives traffic ✓
                                    ├── Target 2: HEALTHY   → receives traffic ✓
                                    └── Target 3: UNHEALTHY → receives ZERO   ✗

If ALL targets in TG are unhealthy → Lattice returns 503 to client.
If SOME targets healthy → traffic distributed among healthy only.
```

Health check parameters: **path** (e.g., `/health`, must return 200),
**interval** (default 30s, range 5-300), **timeout** (default 5s),
**healthy threshold** (default 2, range 2-10), **unhealthy threshold**
(default 2, range 2-10), **matcher** (HTTP code(s), default 200).

**Key implication:** misconfigured health checks cause 503s that look
like "service down." Always verify health check status BEFORE expecting
traffic to flow. This is the #1 cause of "my Lattice service returns
503" tickets.

## Expert heuristic: auth policy scope (service, not rule)

A baseline model assumes auth can be scoped per path. The correct
heuristic recognizes the auth policy boundary.

```text
WRONG (impossible in VPC Lattice):
  Service: payments-svc
    ├── Rule 1: /public/* → no auth
    └── Rule 2: /admin/*  → IAM auth required

CORRECT:
  Service: payments-public-svc (no auth policy)
    └── Rule 1: /public/* → TG-public
  Service: payments-admin-svc (IAM auth policy attached)
    └── Rule 1: /admin/*  → TG-admin

Auth policy attaches to the SERVICE, not to individual rules.
Need different auth per path? Create separate services.
```

**Key implication:** if your design requires different auth semantics
per path, you MUST split into separate services. One auth policy per
service — no exceptions.

## Prerequisites (verify before provisioning)

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| AWS account + region | Lattice is regional | `aws sts get-caller-identity` |
| VPC exists (instance/IP/ALB TG) | Target groups reference VPC resources | `aws ec2 describe-vpcs --vpc-ids <vpc-id>` |
| Lambda function exists (Lambda TG) | Lambda TG references function ARN | `aws lambda get-function --function-name <name>` |
| ALB exists (ALB TG) | ALB TG references ALB ARN | `aws elbv2 describe-load-balancers` |
| ACM cert in us-east-1 (custom domain) | Lattice custom domains require us-east-1 cert | `aws acm list-certificates --region us-east-1` |
| Route53 zone (custom domain DNS) | Domain mapping needs a DNS zone | `aws route53 list-hosted-zones` |
| IAM perms for auth policy | Auth policy requires `vpc-lattice:PutAuthPolicy` | Verify IAM policy |
| Cross-account: RAM share configured | Cross-account needs RAM resource share | `aws ram list-resources` |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Service network (top-level routing plane)

The service network is the top-level routing plane. It is an account-
level construct — NOT a VPC-level construct. Typically one per account.

```bash
SN_ID=$(aws vpc-lattice create-service-network \
  --name my-service-network \
  --auth-type AWS_IAM \
  --tags source=skill-deploy \
  --query 'id' --output text)
echo "Service Network: $SN_ID"
```

**Auth type:** `AWS_IAM` enforces IAM auth by default (the auth policy
still needs PUT on each service). `NONE` means no IAM auth enforcement
at the network level. **Limits:** 1 service network per account (soft),
50 VPC associations per network, 1,000 services per network.

## Step 2 — Target group (type selection + health checks)

The target group type must be chosen at creation and CANNOT be changed.

| Type | Target | VPC required | Use case |
|---|---|---|---|
| INSTANCE | EC2 instance ID | Yes | EC2-based services |
| IP | IP address | Yes | ECS awsvpc, ENI-attached |
| LAMBDA | Lambda function ARN | No | Serverless functions |
| ALB | ALB ARN | Yes | ALB with Lattice upstream |

**Instance target group with health check:**

```bash
TG_ID=$(aws vpc-lattice create-target-group \
  --name tg-stable --type INSTANCE \
  --config '{"port":8080,"protocol":"HTTP","vpcIdentifier":"vpc-aaa11122","healthCheck":{"enabled":true,"path":"/health","protocol":"HTTP","intervalSeconds":30,"timeoutSeconds":5,"healthyThresholdCount":2,"unhealthyThresholdCount":2,"matcher":{"httpCode":"200"}}}' \
  --query 'id' --output text)

aws vpc-lattice register-targets \
  --target-group-identifier "$TG_ID" \
  --targets '[{"id":"i-aaa111222333444","port":8080}]'
```

**Lambda target group:**

```bash
TG_LAMBDA_ID=$(aws vpc-lattice create-target-group \
  --name tg-lambda-processor --type LAMBDA \
  --config '{"lambdaEventStructureVersion":"2.0"}' \
  --query 'id' --output text)

aws vpc-lattice register-targets \
  --target-group-identifier "$TG_LAMBDA_ID" \
  --targets '[{"id":"arn:aws:lambda:us-east-1:123456789012:function:processor"}]'
```

**Critical:** health check status determines routing eligibility. Verify:

```bash
aws vpc-lattice list-targets \
  --target-group-identifier "$TG_ID" \
  --query 'items[*].{Target:id,Status:status}' --output table
```

## Step 3 — Service (HTTP/gRPC)

A service is a runnable unit within a service network. It gets an
auto-assigned DNS name.

```bash
SVC_ID=$(aws vpc-lattice create-service \
  --name payments-svc \
  --query 'id' --output text)

echo "Service: $SVC_ID"
echo "Service DNS: $(aws vpc-lattice get-service \
  --service-identifier "$SVC_ID" \
  --query 'dnsEntry.domainName' --output text)"
```

**Protocol:** HTTP and gRPC are supported. Set when creating the
listener (not the service). A service can have one listener per
protocol.

## Step 4 — Listener rules (path/header/method routing)

Listeners receive traffic for a service. Rules define routing based on
path, header, and HTTP method. Rules are evaluated in priority order;
first match wins.

**Create a listener with default action:**

```bash
LISTENER_ID=$(aws vpc-lattice create-listener \
  --service-identifier "$SVC_ID" \
  --default-action '{"forward":{"targetGroups":[{"targetGroupIdentifier":"'$TG_ID'","weight":100}]}}' \
  --protocol HTTP --port 80 --name payments-listener \
  --query 'id' --output text)
```

**Path-based routing rule (weighted canary split):**

```bash
aws vpc-lattice create-rule \
  --service-identifier "$SVC_ID" \
  --listener-identifier "$LISTENER_ID" \
  --name canary-rule --priority 10 \
  --match '{"httpMatch":{"path":{"prefix":"/api"},"method":"GET"}}' \
  --actions '[{"type":"FORWARD","forward":{"targetGroups":[{"targetGroupIdentifier":"'$TG_CANARY_ID'","weight":20},{"targetGroupIdentifier":"'$TG_ID'","weight":80}]}}]'
```

**Header-based routing rule:**

```bash
aws vpc-lattice create-rule \
  --service-identifier "$SVC_ID" \
  --listener-identifier "$LISTENER_ID" \
  --name beta-header-rule --priority 20 \
  --match '{"httpMatch":{"headerMatches":[{"name":"x-env","match":{"exact":"beta"}}]}}' \
  --actions '[{"type":"FORWARD","forward":{"targetGroups":[{"targetGroupIdentifier":"'$TG_CANARY_ID'","weight":100}]}}]'
```

## Step 5 — IAM auth policy (service level, NOT rule level)

The IAM auth policy enforces IAM-based authentication on the SERVICE.
It applies to ALL listener rules and ALL paths — you CANNOT scope auth
to a specific rule.

```bash
# Set service auth type
aws vpc-lattice update-service \
  --service-identifier "$SVC_ID" \
  --body '{"authType":"AWS_IAM"}'

# Put the auth policy on the service
aws vpc-lattice put-auth-policy \
  --resource-identifier "$SVC_ID" \
  --policy '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"AWS":"arn:aws:iam::123456789012:role/PaymentsCaller"},"Action":"vpc-lattice-svcs:Invoke","Resource":"*"}]}'
```

**Critical:** the auth policy is at the SERVICE level. If you need
different auth per path, split into separate services with separate
auth policies.

## Step 6 — Resource-based service policy

The resource-based service policy controls who can INVOKE the service
(cross-account access). Separate from the IAM auth policy (which
controls request-level auth).

```bash
aws vpc-lattice put-service-policy \
  --service-identifier "$SVC_ID" \
  --policy '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"AWS":"arn:aws:iam::999999999999:root"},"Action":"vpc-lattice-svcs:Invoke","Resource":"*"}]}'
```

Combined with RAM sharing, this enables full cross-account service
access.

## Step 7 — Service network VPC association

VPCs must be ASSOCIATED with the service network to use Lattice DNS
resolution and reach services. Without association, instances in the VPC
cannot resolve Lattice service DNS names.

```bash
aws vpc-lattice create-service-network-vpc-association \
  --service-network-identifier "$SN_ID" \
  --vpc-identifier vpc-aaa11122

# Verify association status
aws vpc-lattice list-service-network-vpc-associations \
  --service-network-identifier "$SN_ID" \
  --query 'items[*].{VPC:vpcId,Status:status}' --output table
# Expected: ACTIVE
```

## Step 8 — Cross-account service access

Cross-account access requires RAM share + service policy.

```bash
# 1. Create RAM resource share (shares service network with other account)
aws ram create-resource-share \
  --name lattice-cross-account-share \
  --resource-arns "arn:aws:vpc-lattice:us-east-1:123456789012:servicenetwork/$SN_ID" \
  --principals 999999999999

# 2. In the consumer account (999999999999): accept the RAM invitation
aws ram accept-resource-share-invitation \
  --resource-share-invitation-arn <invitation-arn>

# 3. In the consumer account: associate their VPC with the shared network
aws vpc-lattice create-service-network-vpc-association \
  --service-network-identifier "$SN_ID" \
  --vpc-identifier vpc-cross-acct-222

# 4. Put the service policy allowing cross-account invocation (Step 6)
```

**Missing any of the four steps results in AccessDenied.**

## Step 9 — Custom domain name mapping

Custom domains map a user-facing DNS name to a Lattice service. The ACM
certificate MUST be in us-east-1 regardless of the service's region.

```bash
# Associate custom domain with the service
aws vpc-lattice associate-custom-domain \
  --service-identifier "$SVC_ID" \
  --domain-name payments.internal.example.com \
  --certificate-arn arn:aws:acm:us-east-1:123456789012:certificate/aaa-bbb-ccc

# Create Route 53 CNAME pointing to the service DNS
SERVICE_DNS=$(aws vpc-lattice get-service \
  --service-identifier "$SVC_ID" \
  --query 'dnsEntry.domainName' --output text)

aws route53 change-resource-record-sets \
  --hosted-zone-id "$ZONE_ID" \
  --change-batch '{"Changes":[{"Action":"CREATE","ResourceRecordSet":{"Name":"payments.internal.example.com","Type":"CNAME","TTL":60,"ResourceRecords":[{"Value":"'$SERVICE_DNS'"}]}}]}'
```

**Critical:** ACM cert must be in us-east-1, and the cert's domain name
must match the custom domain.

## Step 10 — Traffic splitting (canary)

Traffic splitting routes a percentage of traffic to a canary target
group via weighted forwarding in a listener rule. Weights are relative
(not percentage); weights 1 and 4 produce the same 20/80 split as 20
and 80.

```bash
# Create canary target group (same health check as stable)
TG_CANARY_ID=$(aws vpc-lattice create-target-group \
  --name tg-canary --type INSTANCE \
  --config '{"port":8080,"protocol":"HTTP","vpcIdentifier":"vpc-aaa11122","healthCheck":{"enabled":true,"path":"/health","protocol":"HTTP","intervalSeconds":30,"healthyThresholdCount":2}}' \
  --query 'id' --output text)

aws vpc-lattice register-targets \
  --target-group-identifier "$TG_CANARY_ID" \
  --targets '[{"id":"i-canary111222","port":8080}]'

# Rule: 20% canary, 80% stable
aws vpc-lattice create-rule \
  --service-identifier "$SVC_ID" \
  --listener-identifier "$LISTENER_ID" \
  --name canary-split --priority 10 \
  --match '{"httpMatch":{"path":{"prefix":"/api"}}}' \
  --actions '[{"type":"FORWARD","forward":{"targetGroups":[{"targetGroupIdentifier":"'$TG_CANARY_ID'","weight":20},{"targetGroupIdentifier":"'$TG_ID'","weight":80}]}}]'
```

**Progressive canary (20 -> 50 -> 100%):** update rule weights with
`update-rule` to shift traffic gradually.

## Step 11 — Access log delivery

Access logs capture Lattice request details for observability and audit.
Delivery is async; first logs appear within 5-10 minutes.

```bash
# Deliver to CloudWatch Logs
aws vpc-lattice put-access-log-subscription \
  --resource-identifier "$SN_ID" \
  --service-network-log-type SERVICE \
  --log-destination '{"provider":"cloudwatch","destinationArn":"arn:aws:logs:us-east-1:123456789012:log-group:/aws/vpc-lattice"}'

# Or deliver to S3
aws vpc-lattice put-access-log-subscription \
  --resource-identifier "$SN_ID" \
  --service-network-log-type SERVICE \
  --log-destination '{"provider":"s3","destinationArn":"arn:aws:s3:::my-lattice-logs","prefix":"lattice/"}'
```

## Step 12 — Pricing (per GB processed)

| Component | Pricing |
|---|---|
| GB processed | ~$0.025-0.10 per GB (varies by region) |
| Service-hour | ~$0.015 per hour per service |
| Target group, service network, custom domain | Free |
| Access logs | CloudWatch/S3 standard charges |

**Key implication:** GB processed is the dominant cost driver. For
high-traffic services, estimate monthly GB and multiply. The per-service
hourly charge is minor for a small number of services.

## Step 13 — Recent features

- **VPC Lattice GA (2023):** Service networks, services, target groups,
  listener rules, and IAM auth policies.
- **gRPC support (2023-2024):** Full gRPC protocol for services,
  including gRPC health checks and gRPC-specific listener rules.
- **Lambda TG event structure 2.0 (2023-2024):** Lambda target groups
  use an improved event structure with Lattice metadata.
- **Cross-account via RAM (2023-2024):** RAM resource shares enable
  cross-account VPC association with a shared service network.
- **Custom domain with ACM TLS (2023-2024):** ACM-managed TLS certs
  (us-east-1) for user-facing custom domain names.
- **Access log subscription (2024-2025):** Structured access log
  delivery to CloudWatch Logs or S3.
- **Weighted traffic splitting (2024-2025):** Listener rules support
  weighted forwarding to multiple target groups for canary/blue-green.
- **Header-based routing (2024-2025):** Listener rules support header
  matching in addition to path-based and method-based routing.
- **Tiered pricing (2025-2026):** Reduced per-GB cost above monthly
  thresholds for high-volume workloads.

## NEVER do these things

1. **NEVER assume auth policy can be scoped per listener rule.** The
   IAM auth policy attaches to the SERVICE, not individual rules. It
   governs ALL paths on the service. Need different auth per path?
   Create separate services.

2. **NEVER assume unhealthy targets receive traffic.** VPC Lattice
   routes ZERO traffic to targets failing health checks. If all targets
   in a TG are unhealthy, clients see 503. Always verify health check
   status before expecting traffic.

3. **NEVER skip VPC association with the service network.** VPCs NOT
   associated cannot resolve Lattice service DNS names and cannot reach
   services. Association is a prerequisite for in-VPC service access.

4. **NEVER assume the service network is per VPC.** It is an account-
   level construct (1 per account typical). Multiple VPCs are
   ASSOCIATED with the same service network.

5. **NEVER attempt cross-account access without RAM + service policy.**
   Cross-account requires BOTH a RAM resource share AND a resource-based
   service policy. Missing either results in AccessDenied.

6. **NEVER request a custom domain ACM certificate outside us-east-1.**
   Lattice custom domains require the ACM cert in us-east-1 regardless
   of the service's region.

7. **NEVER change the target group type after creation.** The type
   (INSTANCE, IP, LAMBDA, ALB) is immutable. To change type, create a
   new target group and update listener rules.

8. **NEVER assume traffic splitting weights must sum to 100.** Weights
   are relative. Weights 1 and 4 produce the same 20/80 split as 20 and
   80. Lattice normalizes.

9. **NEVER forget the listener default action.** The default action is
   the fallback when no rule matches. Without it, unmatched requests
   fail.

10. **NEVER assume access logs are real-time.** Log delivery is async;
    first logs appear within 5-10 minutes.

## Output format

```text
VPC_LATTICE: <service-network-id> → <service-id> (<service-dns-name>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Service network: <sn-id> (auth type: AWS_IAM | NONE)
  [✓|✗] Target group: <tg-id> (type: INSTANCE | IP | LAMBDA | ALB, port: <port>)
  [✓|✗] Health check: path <path>, interval <n>s — targets <n>/<n> healthy
  [✓|✗] Service: <svc-id> (protocol: HTTP | gRPC, DNS: <dns-name>)
  [✓|✗] Listener: <listener-id> (port <port>, protocol HTTP | gRPC)
  [✓|✗] Listener rules: <n> rule(s) (path/header/method match)
  [✓|✗] Auth policy: IAM auth at SERVICE level (covers ALL rules) | None
  [✓|✗] Service policy: resource-based policy (cross-account) | Same-account
  [✓|✗] VPC association: <vpc-id> associated with <sn-id> — ACTIVE
  [✓|✗] Cross-account: RAM share to <account-id> | Same-account
  [✓|✗] Custom domain: <domain> → <service-dns> (ACM us-east-1) | Not configured
  [✓|✗] Traffic splitting: canary <n>% / stable <n>% | Single TG
  [✓|✗] Access logs: CloudWatch | S3 | Disabled
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws vpc-lattice get-service-network --service-network-identifier <sn-id>
  aws vpc-lattice get-service --service-identifier <svc-id>
  aws vpc-lattice list-targets --target-group-identifier <tg-id>
  aws vpc-lattice list-listeners --service-identifier <svc-id>
  aws vpc-lattice list-rules --service-identifier <svc-id> --listener-identifier <listener-id>
  aws vpc-lattice list-service-network-vpc-associations --service-network-identifier <sn-id>
```

### Worked example — HTTP service with canary traffic splitting

```text
VPC_LATTICE: sni-aaa111 → svc-bbb222 (payments-svc-aaa.example.com)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Service network: sni-aaa111 (auth type: AWS_IAM)
  [✓] Target group: tgc-stable (type: INSTANCE, port: 8080)
  [✓] Health check: path /health, interval 30s — targets 3/3 healthy
  [✓] Service: svc-bbb222 (protocol: HTTP, DNS: payments-svc-aaa.example.com)
  [✓] Listener: lstn-ccc333 (port 80, protocol HTTP)
  [✓] Listener rules: 2 rules (path /v2/* → canary split, default → stable)
  [✓] Auth policy: IAM auth at SERVICE level (covers ALL rules)
  [✓] Service policy: resource-based policy (cross-account for 999999999999)
  [✓] VPC association: vpc-aaa11122 associated with sni-aaa111 — ACTIVE
  [✓] Cross-account: RAM share to 999999999999
  [✓] Custom domain: payments.internal.example.com → payments-svc-aaa.example.com (ACM us-east-1)
  [✓] Traffic splitting: canary 20% / stable 80%
  [✓] Access logs: CloudWatch (/aws/vpc-lattice)
  [✓] Tags: Environment=production, Topology=canary
VERIFICATION_COMMANDS:
  aws vpc-lattice get-service-network --service-network-identifier sni-aaa111
  aws vpc-lattice get-service --service-identifier svc-bbb222
  aws vpc-lattice list-targets --target-group-identifier tgc-stable
  aws vpc-lattice list-rules --service-identifier svc-bbb222 --listener-identifier lstn-ccc333
  aws vpc-lattice list-service-network-vpc-associations --service-network-identifier sni-aaa111
```

## Error handling

### Service returns 503 (no healthy targets)
- All targets in the target group are failing health checks. Verify
  health check path, port, and matcher. Check that targets are running
  and responding on the health check path. Use `list-targets` to see
  health status and reasons.

### Cross-account invocation fails with AccessDenied
- Either the RAM resource share was not accepted, the VPC association
  was not created in the consumer account, or the resource-based service
  policy does not include the consumer account principal. Verify all
  three: RAM, association, service policy.

### Custom domain does not resolve
- The Route 53 record may not point to the service DNS name. Or the ACM
  certificate is not in us-east-1. Verify the cert ARN region and DNS
  record target.

### VPC instances cannot reach the Lattice service
- The VPC may not be associated with the service network. Verify the VPC
  association status is ACTIVE. Without association, Lattice DNS names
  do not resolve within the VPC.

### Auth policy not enforcing
- The service auth type may not be set to AWS_IAM. The auth policy only
  takes effect when the service auth type is AWS_IAM. Use
  `update-service --body '{"authType":"AWS_IAM"}'` to set it.

## Domain

AWS CloudOps / Amazon VPC Lattice Service Networking Provisioning &
Application-Layer Routing.

## AWS documentation

- **VPC Lattice Guide** — https://docs.aws.amazon.com/vpc-lattice/latest/ug/what-is-vpc-lattice.html
- **Service networks** — https://docs.aws.amazon.com/vpc-lattice/latest/ug/service-networks.html
- **Target groups** — https://docs.aws.amazon.com/vpc-lattice/latest/ug/target-groups.html
- **Listener rules** — https://docs.aws.amazon.com/vpc-lattice/latest/ug/listeners.html
- **Auth policies** — https://docs.aws.amazon.com/vpc-lattice/latest/ug/auth-policies.html
- **Custom domains** — https://docs.aws.amazon.com/vpc-lattice/latest/ug/custom-domains.html
- **Access logs** — https://docs.aws.amazon.com/vpc-lattice/latest/ug/access-logs.html
- **Cross-account access** — https://docs.aws.amazon.com/vpc-lattice/latest/ug/cross-account.html
- **VPC Lattice pricing** — https://aws.amazon.com/vpc/lattice/pricing/
