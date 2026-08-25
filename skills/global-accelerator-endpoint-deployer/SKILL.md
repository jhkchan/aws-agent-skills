---
name: global-accelerator-endpoint-deployer
description: 'Provisions AWS Global Accelerator with production defaults: accelerator creation with two static anycast IP addresses, listeners (TCP/UDP port ranges), endpoint groups (region, traffic dial percentage, health check interval/threshold), endpoint types (ALB, NLB, EC2 IP, EIP), endpoint weights for within-region distribution, client IP address preservation, BYOIP integration, flow logs, CloudWatch metrics, cross-region routing, DNS naming, and endpoint group failover. Emits a READY_TO_DEPLOY checklist with verification commands. Use when creating a Global Accelerator, configuring anycast IPs, setting up multi-region endpoints, adjusting traffic dial for regional canary, configuring endpoint weights, enabling client IP preservation, or managing endpoint group failover. Triggers: create global accelerator, anycast ip addresses, traffic dial, endpoint group, endpoint weight, listener ports, client ip preservation, global accelerator failover, byoip accelerator, accelerator flow logs.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with globalaccelerator access. Works with Terraform aws_globalaccelerator_accelerator / aws_globalaccelerator_listener / aws_globalaccelerator_endpoint_group resources and CloudFormation AWS::GlobalAccelerator::Accelerator / Listener / EndpointGroup templates.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Networking
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, global-accelerator, anycast, cloudops, deploy, networking, provisioning, traffic-dial, endpoint-group, cross-region, failover, byoip
  dependencies: aws-orchestrator
  keywords: aws, global accelerator, anycast, cloudops, deploy, provisioning, traffic dial, endpoint group, endpoint weight, listener, cross-region, failover, byoip, flow logs, client ip preservation
  when_to_use: Invoke when the user wants to create an AWS Global Accelerator with static anycast IP addresses, configure listeners with TCP/UDP ports, set up endpoint groups across regions with traffic dial percentages, add endpoints (ALB, NLB, EC2, EIP) with weights, enable client IP preservation, integrate BYOIP, configure flow logs, or manage endpoint group failover. Do NOT invoke for CloudFront (CDN/edge), Route 53 (DNS routing), Elastic Load Balancing v2 directly, or Transit Gateway.
---

# Global Accelerator Endpoint Deployer

An AWS CloudOps agent skill that provisions AWS Global Accelerator with
correct defaults. The skill walks the operator through accelerator
creation (two static anycast IPs pinned at creation), listener
configuration (TCP/UDP port ranges), endpoint groups (per-region with
traffic dial and health checks), endpoint types (ALB, NLB, EC2 IP, EIP)
with weights, client IP address preservation, BYOIP integration, flow
logs, CloudWatch metrics, cross-region routing, DNS naming, and
endpoint group failover, captures routing and health check decisions,
explains why each default matters, and emits a READY_TO_DEPLOY checklist
with copy-pasteable verification commands.

## Activation keywords

create global accelerator, anycast IP addresses, traffic dial, endpoint
group, endpoint weight, listener ports, client IP preservation, Global
Accelerator failover, BYOIP accelerator, accelerator flow logs.

## STRICT output contract

When this skill is invoked with a Global-Accelerator-provisioning
request (create an accelerator, configure anycast IPs, set up
multi-region endpoints, adjust traffic dial, configure endpoint weights,
enable client IP preservation, set up failover, or a partial
configuration), the agent MUST respond with the READY_TO_DEPLOY checklist
defined in the "Output format" section using the literal all-caps labels
`GLOBAL_ACCELERATOR:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels breaks
automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Accelerator and anycast IPs | Core accelerator model |
| Step 2 — Listener (TCP/UDP ports) | Port configuration |
| Step 3 — Endpoint group (region, traffic dial) | Regional routing |
| Step 4 — Endpoint types and weights | Within-region distribution |
| Step 5 — Client IP address preservation | Source IP behavior |
| Step 6 — Cross-region routing and DNS | Global DNS |
| Step 7 — BYOIP integration | Custom IP pools |
| Step 8 — Flow logs and metrics | Observability |
| Step 9 — Endpoint group failover | Failover strategy |
| Step 10 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/anycast-and-traffic-dial.md | Anycast IP + traffic dial detail |
| references/endpoint-types-and-failover.md | Endpoint types + failover detail |

## Mindset

**One-line takeaway:** AWS Global Accelerator gives you two static
anycast IP addresses that route traffic over the AWS global backbone to
endpoints in one or more AWS regions. The anycast IPs are assigned at
accelerator creation and cannot be changed without recreating the
accelerator. Traffic dial controls regional weight (0-100 percent),
and endpoint weight controls within-region distribution.

Three misconceptions dominate Global Accelerator misdesign at
provisioning time:

- **"The anycast IPs can be swapped after creation."** They cannot.
  The two static anycast IP addresses are allocated when the accelerator
  is created. To change them, you must create a new accelerator and
  update DNS. If you need BYOIP addresses, they must be provisioned
  BEFORE accelerator creation.

- **"Traffic dial is a simple weight."** Traffic dial (0.0 to 1.0) is
  a percentage applied per endpoint group (i.e., per region). A dial of
  1.0 means "send full traffic to this region." A dial of 0.0 means
  "drain this region." The dials across endpoint groups are normalized.
  This is fundamentally different from endpoint weights, which distribute
  traffic WITHIN a single endpoint group.

- **"Health checks are the same as ALB/NLB health checks."** Global
  Accelerator health checks are independent from target group health
  checks. An endpoint can be healthy at the target group level but
  unhealthy at the Global Accelerator level (or vice versa). The
  threshold and interval are configured separately and affect failover
  timing.

## Configuration dependency graph (novel heuristic)

Global Accelerator configurations are NOT independent. The anycast IPs
are pinned at accelerator creation. Listeners must reference the
accelerator. Endpoint groups must reference a listener and specify a
region. Endpoints must reference existing ALB/NLB/EC2/EIP resources.
Use this graph to sequence provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Accelerator (anycast IPs) | None for standard; BYOIP pool first for BYOIP | Anycast IPs PINNED at creation — cannot swap; BYOIP requires pre-provisioned pool | listener creation |
| Listener | Accelerator exists | Port ranges cannot overlap between listeners on same accelerator | endpoint group |
| Endpoint group | Listener exists; region specified | One group per region per listener; traffic dial defaults 1.0 | endpoints |
| Endpoint (ALB/NLB) | LB exists in same region as endpoint group | ALB/NLB must be in-region | traffic routing |
| Endpoint (EC2 IP/EIP) | EC2/EIP exists | Must have correct region | traffic routing |
| Endpoint weight | Endpoint group exists | Weight 0-255; default 128; 0 drains endpoint | within-region distribution |
| Client IP preservation | Endpoint type supports it | ON by default for ALB/NLB; disabled for NLB with TLS | source IP visibility |
| BYOIP | IP pool provisioned in IPAM (READY state) | Cannot add BYOIP after creation | custom anycast IPs |
| Flow logs | Accelerator exists; CW Logs group or S3 | Require IAM permissions | observability |

**The anycast-IPs-pinned-at-creation row is the one a baseline model
misses.** Unlike Elastic IPs (which can be allocated and associated
dynamically), Global Accelerator anycast IPs are assigned at creation
time and cannot be changed. If BYOIP is needed, the IP pool must be
provisioned BEFORE the accelerator is created.

**Cross-dependency gotchas:**
- Listeners with overlapping port ranges cause creation errors.
- Traffic dial is a percentage, NOT a weight. It is normalized across
  all endpoint groups.
- Endpoint weight (0-255) operates WITHIN a group, independent of
  traffic dial which operates ACROSS groups.
- Health check interval and threshold affect failover timing. A shorter
  interval means faster failover but more health check traffic.

## Expert heuristic: anycast IPs pinned at creation + traffic dial for regional canary + endpoint weight for within-region distribution

Moved verbatim to [references/anycast-and-traffic-dial.md](references/anycast-and-traffic-dial.md) — load on demand.
Covers: Expert heuristic: anycast IPs pinned at creation + traffic dial for regional canary + endpoint weight for within-region distribution. See the "References (load on demand)" section.

## Expert heuristic: health check customization drives failover timing

Moved verbatim to [references/endpoint-types-and-failover.md](references/endpoint-types-and-failover.md) — load on demand.
Covers: Expert heuristic: health check customization drives failover timing. See the "References (load on demand)" section.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Target resources exist | Endpoints reference existing ALB/NLB/EC2/EIP | `aws elbv2 describe-load-balancers` |
| Endpoint regions identified | Endpoint groups are per-region | Confirm region for each endpoint |
| BYOIP pool in READY state (if applicable) | BYOIP must precede accelerator creation | `aws ec2 describe-byoipcidrs` |
| Traffic dial strategy decided | Controls regional weight (0.0-1.0) | Assess canary/failover strategy |
| Endpoint weight strategy decided | Controls within-region distribution (0-255) | Assess per-endpoint distribution |
| Listener port ranges defined | Non-overlapping between listeners | List all TCP/UDP port ranges |
| Health check parameters decided | Interval/threshold affect failover timing | Assess failover sensitivity |
| Client IP preservation decision | Controls source IP visibility | Assess need for source IP |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Accelerator and anycast IPs

The accelerator is the top-level resource. It provides two static
anycast IP addresses that route traffic over the AWS global backbone.

| Property | Value | Notes |
|---|---|---|
| Name | Accelerator name | Unique within account |
| IP address type | IPV4 or DUAL_STACK | DUAL_STACK gives IPv4 + IPv6 anycast |
| Anycast IPs | Two static IPs (auto-assigned or BYOIP) | PINNED at creation — cannot change |

**Create an accelerator (auto-assigned anycast IPs):**

```bash
ACCEL_ARN=$(aws globalaccelerator create-accelerator \
  --name "my-accelerator" \
  --ip-address-type IPV4 \
  --enabled \
  --query 'Accelerator.AcceleratorArn' --output text)

echo "Accelerator ARN: $ACCEL_ARN"
```

**Create an accelerator with BYOIP (pool must be READY):**

```bash
aws globalaccelerator create-accelerator \
  --name "byoip-accelerator" \
  --ip-address-type IPV4 \
  --ip-addresses Cidr=203.0.113.0/24 \
  --enabled
```

**Critical:** the anycast IPs are assigned at creation. To change them,
you must create a NEW accelerator and update DNS.

## Step 2 — Listener (TCP/UDP ports)

The listener defines the protocol (TCP or UDP) and port ranges that the
accelerator accepts. Port ranges must NOT overlap between listeners.

| Property | Value | Notes |
|---|---|---|
| Protocol | TCP or UDP | One protocol per listener |
| Port ranges | 1-65535 | Non-overlapping between listeners |
| Client affinity | NONE or SOURCE_IP | SOURCE_IP pins sessions to endpoints |

**Create a TCP listener (ports 80 and 443):**

```bash
LISTENER_ARN=$(aws globalaccelerator create-listener \
  --accelerator-arn "$ACCEL_ARN" \
  --protocol TCP \
  --port-ranges FromPort=80,ToPort=80 FromPort=443,ToPort=443 \
  --client-affinity NONE \
  --query 'Listener.ListenerArn' --output text)
```

## Step 3 — Endpoint group (region, traffic dial, health check)

The endpoint group is a regional grouping of endpoints within a listener.
Each endpoint group targets one AWS region. The traffic dial percentage
controls how much traffic flows to that region.

| Property | Value | Notes |
|---|---|---|
| Region | Target AWS region | One group per region per listener |
| Traffic dial | 0.0 to 1.0 | Percentage of traffic (normalized) |
| Health check interval | 10 or 30 seconds | Affects failover speed |
| Health check path | HTTP path | e.g., /health |
| Threshold count | Integer (default 3) | Consecutive successes/failures |

**Create endpoint groups (active-passive):**

```bash
# Primary region — 100% traffic
EG_PRIMARY=$(aws globalaccelerator create-endpoint-group \
  --listener-arn "$LISTENER_ARN" \
  --endpoint-group-region us-east-1 \
  --traffic-dial 1.0 \
  --health-check-interval-seconds 10 \
  --health-check-path /health \
  --health-check-port 443 \
  --health-check-protocol HTTPS \
  --threshold-count 3 \
  --query 'EndpointGroup.EndpointGroupArn' --output text)

# DR region — 0% traffic (failover target)
EG_DR=$(aws globalaccelerator create-endpoint-group \
  --listener-arn "$LISTENER_ARN" \
  --endpoint-group-region us-west-2 \
  --traffic-dial 0.0 \
  --health-check-interval-seconds 10 \
  --health-check-path /health \
  --health-check-port 443 \
  --health-check-protocol HTTPS \
  --threshold-count 3 \
  --query 'EndpointGroup.EndpointGroupArn' --output text)
```

**Adjust traffic dial for regional canary (10% to DR):**

```bash
aws globalaccelerator update-endpoint-group \
  --endpoint-group-arn "$EG_DR" \
  --traffic-dial 0.1
```

## Step 4 — Endpoint types and weights

Endpoints are the actual targets within an endpoint group. Four types
are supported:

| Endpoint type | Identifier | Notes |
|---|---|---|
| ALB | ARN of ALB | Same region as endpoint group |
| NLB | ARN of NLB | Same region as endpoint group |
| EC2 | Instance IP | Any EC2 instance IP |
| EIP | Allocation ID | Any AZ |

Each endpoint has a weight (0-255) controlling traffic distribution
WITHIN the endpoint group. Weight 0 = drain. Default = 128.

**Add an ALB endpoint with weight 128:**

```bash
aws globalaccelerator update-endpoint-group \
  --endpoint-group-arn "$EG_PRIMARY" \
  --endpoint-configurations \
    EndpointId=arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/my-alb/50dc6c495c0c9188,Weight=128
```

**Common mistake:** confusing traffic dial (across regions, 0.0-1.0)
with endpoint weight (within a region, 0-255).

## Step 5 — Client IP address preservation

By default, Global Accelerator preserves the client's source IP address
for ALB, NLB, EC2, and EIP endpoints. The backend sees the real client
IP, not a proxy IP.

| Endpoint type | Client IP preservation | Default |
|---|---|---|
| ALB | Supported | Enabled by default |
| NLB | Supported | Enabled (disabled if TLS termination on NLB) |
| EC2 IP | Supported | Enabled by default |
| EIP | Supported | Enabled by default |

**Critical:** if the endpoint is an NLB with TLS termination, client IP
preservation may be implicitly disabled. Verify the NLB configuration.

## Step 6 — Cross-region routing and DNS naming

Global Accelerator routes traffic over the AWS global backbone, providing
lower latency than the public internet for cross-region traffic.

**Accelerator DNS name:**

```bash
ACCEL_DNS=$(aws globalaccelerator describe-accelerator \
  --accelerator-arn "$ACCEL_ARN" \
  --query 'Accelerator.DnsName' --output text)
# Example: a1b2c3d4e5f6g7h8i9.a1b2c3d4e5f6g7h8i9.awsglobalaccelerator.com
```

**Custom DNS (Route 53 alias record):**

```bash
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1DEXAMPLE \
  --change-batch '{
    "Changes": [{
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "app.example.com",
        "Type": "A",
        "AliasTarget": {
          "HostedZoneId": "Z2BJ6XQCAUYQ5E",
          "DNSName": "'"$ACCEL_DNS"'",
          "EvaluateTargetHealth": true
        }
      }
    }]
  }'
```

## Step 7 — BYOIP integration

Moved verbatim to [references/anycast-and-traffic-dial.md](references/anycast-and-traffic-dial.md) — load on demand.
Covers: Step 7 — BYOIP integration. See the "References (load on demand)" section.

## Step 8 — Flow logs and CloudWatch metrics

Moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md) — load on demand.
Covers: Step 8 — Flow logs and CloudWatch metrics. See the "References (load on demand)" section.

## Step 9 — Endpoint group failover

Moved verbatim to [references/endpoint-types-and-failover.md](references/endpoint-types-and-failover.md) — load on demand.
Covers: Step 9 — Endpoint group failover. See the "References (load on demand)" section.

## Step 10 — Recent features

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — load on demand.
Covers: Step 10 — Recent features. See the "References (load on demand)" section.

## NEVER do these things

1. **NEVER assume anycast IPs can be changed after accelerator creation.**
   The two static anycast IPs are assigned at creation and cannot be
   swapped. To change them, create a new accelerator and update DNS.

2. **NEVER add BYOIP to an existing accelerator.** BYOIP must be
   provisioned and advertised BEFORE the accelerator is created. The IP
   pool must be in READY state.

3. **NEVER confuse traffic dial with endpoint weight.** Traffic dial
   (0.0-1.0) controls regional weight ACROSS endpoint groups. Endpoint
   weight (0-255) controls distribution WITHIN a group.

4. **NEVER create listeners with overlapping port ranges.** Each
   listener on the same accelerator must have non-overlapping port
   ranges.

5. **NEVER assume Global Accelerator health checks equal target group
   health checks.** Global Accelerator performs its own health checks
   independently. An endpoint can be healthy at one level but unhealthy
   at the other.

6. **NEVER forget to set traffic dial for failover regions.** If using
   active-passive, the DR region should have traffic dial 0.0 (not
   removed). Removing the endpoint group eliminates the failover target.

7. **NEVER use Global Accelerator for CDN/edge caching.** It is a Layer
   4 anycast accelerator, not a CDN. For content caching, use CloudFront.

8. **NEVER create an endpoint in a different region than its endpoint
   group.** Endpoints (ALB, NLB, EC2, EIP) must be in the same region
   as the endpoint group.

9. **NEVER ignore client IP preservation behavior with NLB TLS.** If
   the endpoint is an NLB with TLS termination, client IP preservation
   may be implicitly disabled.

10. **NEVER skip health check configuration.** The default 30-second
    interval may be too slow for latency-sensitive workloads. Use
    10-second intervals for faster failover.

## Output format

```text
GLOBAL_ACCELERATOR: <accelerator-name> (<accelerator-arn>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Accelerator: <name> — ENABLED
  [✓|✗] Anycast IPs: <ip1>, <ip2> — PINNED at creation
  [✓|✗] IP address type: IPV4 | DUAL_STACK
  [✓|✗] BYOIP: <cidr> (pool READY) | Not applicable (auto-assigned)
  [✓|✗] Listener: <protocol> ports <ranges> — client affinity <NONE|SOURCE_IP>
  [✓|✗] Endpoint group (region 1): <region> — traffic dial <0.0-1.0>, health <interval>s/<proto>/<path>
  [✓|✗] Endpoint group (region 2): <region> — traffic dial <0.0-1.0>, health <interval>s/<proto>/<path>
  [✓|✗] Endpoints: <type> <id> weight <0-255> | <type> <id> weight <0-255>
  [✓|✗] Client IP preservation: ENABLED | DISABLED
  [✓|✗] Flow logs: <destination> | Disabled
  [✓|✗] Failover strategy: Active-passive | Active-active
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws globalaccelerator describe-accelerator --accelerator-arn <arn>
  aws globalaccelerator list-listeners --accelerator-arn <arn>
  aws globalaccelerator list-endpoint-groups --listener-arn <arn>
```

### Worked example — multi-region ALB with failover

```text
GLOBAL_ACCELERATOR: prod-accelerator (arn:aws:globalaccelerator::123456789012:accelerator/abcd1234)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Accelerator: prod-accelerator — ENABLED
  [✓] Anycast IPs: 192.0.2.1, 192.0.2.2 — PINNED at creation
  [✓] IP address type: IPV4
  [✓] BYOIP: Not applicable (auto-assigned)
  [✓] Listener: TCP ports 80, 443 — client affinity NONE
  [✓] Endpoint group (region 1): us-east-1 — traffic dial 1.0, health 10s/HTTPS//health
  [✓] Endpoint group (region 2): us-west-2 — traffic dial 0.0, health 10s/HTTPS//health
  [✓] Endpoints: ALB arn:...:loadbalancer/app/prod-alb-us-east weight 128
  [✓] Endpoints: ALB arn:...:loadbalancer/app/prod-alb-us-west weight 128
  [✓] Client IP preservation: ENABLED
  [✓] Flow logs: arn:aws:logs:us-west-2:123456789012:log-group:/aws/globalaccelerator/prod
  [✓] Failover strategy: Active-passive (us-east-1 primary, us-west-2 DR)
  [✓] Tags: Environment=production, Project=web-app
VERIFICATION_COMMANDS:
  aws globalaccelerator describe-accelerator --accelerator-arn arn:aws:globalaccelerator::123456789012:accelerator/abcd1234
  aws globalaccelerator list-listeners --accelerator-arn arn:aws:globalaccelerator::123456789012:accelerator/abcd1234
  aws globalaccelerator list-endpoint-groups --listener-arn arn:aws:globalaccelerator::123456789012:accelerator/abcd1234/listener/efgh5678
```

## Error handling

Moved verbatim to [references/error-handling.md](references/error-handling.md) — load on demand.
Covers: Error handling. See the "References (load on demand)" section.

## References (load on demand)

- [references/anycast-and-traffic-dial.md](references/anycast-and-traffic-dial.md) — anycast IP and traffic dial detail (existing); now also the three-layer traffic-control heuristic and the BYOIP CLI walkthrough (Step 7)
- [references/endpoint-types-and-failover.md](references/endpoint-types-and-failover.md) — endpoint types, weights, and failover detail (existing); now also the health-check timing heuristic and the failover playbook (Step 9)
- [references/advanced-patterns.md](references/advanced-patterns.md) — recent AWS features (Step 10)
- [references/error-handling.md](references/error-handling.md) — error-handling deep dives: endpoints always unhealthy, traffic not reaching failover region, BYOIP creation failure
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — flow-log configuration and CloudWatch metrics commands (Step 8)

## Domain

AWS CloudOps / AWS Global Accelerator Provisioning & Global Network
Routing.

## AWS documentation

- **Global Accelerator Guide** — https://docs.aws.amazon.com/global-accelerator/latest/dg/what-is-global-accelerator.html
- **Listeners** — https://docs.aws.amazon.com/global-accelerator/latest/dg/about-listeners.html
- **Endpoint groups** — https://docs.aws.amazon.com/global-accelerator/latest/dg/about-endpoint-groups.html
- **Client IP preservation** — https://docs.aws.amazon.com/global-accelerator/latest/dg/preserve-client-ip-address.html
- **BYOIP** — https://docs.aws.amazon.com/global-accelerator/latest/dg/using-byoip.html
- **Flow logs** — https://docs.aws.amazon.com/global-accelerator/latest/dg/monitoring-global-accelerator.flow-logs.html
