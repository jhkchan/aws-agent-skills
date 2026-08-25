---
name: globalaccelerator-deployer
description: 'Provisions production-grade AWS Global Accelerator deployments with secure defaults: anycast static IP allocation (Amazon pool or BYOIP), TCP/UDP listeners with port ranges and client affinity, regional endpoint groups with traffic dials and health checks, ALB/NLB/EC2/EIP endpoint types, client IP preservation for NLB/EC2 origins, flow logs to CloudWatch or S3, cross-account endpoints via RAM resource share, and custom routing accelerators for deterministic port-to-endpoint mapping. Emits a deployment plan with a READY_TO_DEPLOY checklist. Use when provisioning a new accelerator, planning multi-region active-active traffic steering, configuring client IP preservation for NLB origins, advertising BYOIP ranges, sharing endpoints across AWS accounts, or building a custom routing accelerator for gaming/VoIP workloads.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline architecture planning. Live deployment uses aws globalaccelerator create-accelerator, create-listener, create-endpoint-group, add-endpoints, update-endpoint-group, advertise-byoip-cidr, aws ram create-resource-share, aws ec2 describe-addresses, and aws logs create-log-group (AWS CLI v2, SSO or key-based credentials).
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
  when_to_use: Provisioning a new Global Accelerator for production, planning multi-region active-active traffic steering, configuring client IP preservation for NLB or EC2 endpoints, advertising BYOIP CIDR blocks, sharing endpoint groups across AWS accounts via RAM, deploying a custom routing accelerator for gaming or VoIP workloads, or configuring flow logs to CloudWatch or S3.
  activation_triggers: create a Global Accelerator, provision an accelerator with static IPs, multi-region active-active accelerator, BYOIP advertise through Global Accelerator, client IP preservation for NLB, cross-account endpoint share, custom routing accelerator, Global Accelerator endpoint group, traffic dial multi-region, Global Accelerator flow logs, dual-stack IPv6 accelerator
  invocation_schema: 'Input shape (one of): (a) a deployment specification including endpoint type (ALB/NLB/EC2/EIP), regions, listener protocol and port range, traffic steering model, BYOIP requirement, client IP preservation requirement, flow log destination, and cross-account requirement; (b) a partial spec for interactive refinement (e.g., "Global Accelerator in front of two regional ALBs with active-active"); (c) an existing accelerator ARN for architecture review against the well-architected checklist. Output shape: { ACCELERATOR_SPEC, VERDICT, ARCHITECTURE, CHECKLIST[], FINDINGS[], DEPLOY_COMMANDS } where VERDICT ∈ { READY_TO_DEPLOY, PREREQUISITES_MISSING }.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Global Accelerator, accelerator deploy, anycast IP, static IP, BYOIP, listener, endpoint group, traffic dial, health check, ALB endpoint, NLB endpoint, EC2 endpoint, Elastic IP endpoint, client IP preservation, PreserveClientIpEnabled, flow logs, cross-account endpoints, RAM resource share, custom routing accelerator, dual-stack, IPv6, client affinity, multi-region active-active
  tags: globalaccelerator, networking, deploy, anycast, byoip, endpoint-group, traffic-dial, client-ip-preservation, cross-account, custom-routing
---

# Global Accelerator Deployer

## What this skill does

Provisions production-grade AWS Global Accelerator deployments with secure
defaults: anycast static IP allocation (Amazon pool or BYOIP), TCP/UDP
listeners, regional endpoint groups with traffic dials and health checks,
ALB/NLB/EC2/EIP endpoint types, client IP preservation for NLB and EC2
origins, flow logs to CloudWatch or S3, cross-account endpoints via RAM,
and custom routing accelerators. Emits a deployment plan with a
READY_TO_DEPLOY checklist.

## Mindset

**One-line takeaway:** Global Accelerator is **not** "an ALB at the edge"
— it is an **anycast network plane** that routes user traffic from the
nearest AWS edge location into the AWS backbone, bypassing internet
congestion for the transit segment. The static IPs are anycast (advertised
from every edge globally); the endpoint selection is regional (per
endpoint-group traffic dial); and the origin's view of "client IP" depends
on endpoint type and PreserveClientIpEnabled.

Three facts make Global Accelerator provisioning different from "give me
two static IPs":

- **The two static IPs are anycast — they are NOT region-bound.** The
  same pair of IPs is advertised from every AWS edge location worldwide.
  A user in Tokyo and a user in Frankfurt hit the same IPs but are
  routed to different endpoint groups. The "region" of an accelerator
  only controls where the control-plane metadata lives (and the
  fixed-fee billing region) — it does not affect traffic routing.

- **Endpoint types within one endpoint group MUST be homogeneous.** A
  group can contain ALB OR NLB OR EC2 OR Elastic IP endpoints — mixing
  types in the same group is rejected by the API. This is an AWS hard
  constraint. Multi-type designs require separate endpoint groups
  (each in a different region, by definition).

- **Client IP preservation changes the origin's security posture.** For
  ALB endpoints, the client IP always reaches the origin via
  `X-Forwarded-For` (the L4 source IP at the ALB is an internal GA IP).
  For NLB and EC2 endpoints, `PreserveClientIpEnabled: true` causes the
  origin to see the real client IP — security groups and WAF rules at
  the origin MUST allow client IP ranges. Disabling hides clients behind
  AWS IPs and breaks IP-based rate limiting and geo-blocking at origin.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **Quick reference** | Verdict thresholds + checklist matrix + GA limits | Before any operation |
| **Pre-flight** | Accelerator metadata gate — endpoints, regions, BYOIP, IAM, RAM | Before executing any CLI |
| **Process** | Per-step planning: accelerator, listener, endpoint group, endpoints, IP preservation, flow logs, cross-account, custom routing | When choosing each step |
| **Common patterns** | Multi-region ALB active-active / single-region NLB / custom routing gaming | Boilerplate lookup |
| **STRICT output contract** | Required ACCELERATOR/VERDICT/PRE_CHECKS/STEPS/POST_VERIFY block | Formatting the response |
| **NEVER (top 5)** | Hard rules preventing common insecure patterns | Review before deploy |
| **Expert heuristic** | When client IP preservation is correct per endpoint type | Choosing IP preservation |

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `PREREQUISITES_MISSING` | Any pre-check failed (BYOIP CIDR not provisioned in Route 53 / not in `PROVISIONED` state, mixed endpoint types in one group, endpoint ARN unresolvable, endpoint region != endpoint-group region, accelerator in unsupported region, IAM permission missing, cross-account RAM share not accepted, flow log destination inaccessible, IPv6 requested on accelerator created before dual-stack support without migration) | List failures, do NOT execute |
| `READY_TO_DEPLOY` | All pre-checks passed; awaiting CONFIRM gate | Emit exact CLI sequence with full accelerator config, wait for operator yes |

**Deployment checklist (every dimension must pass):**

| Dimension | Requirement | Step |
|---|---|---|
| Static IP source | Amazon pool (default, 2 anycast IPs) or BYOIP (`PROVISIONED` + advertised) | Step 1 |
| IP version | IPv4-only (default) or dual-stack IPv4+IPv6 (accelerator created 2023+) | Step 1 |
| Accelerator region | Any region where GA is available (control-plane only; traffic is global) | Step 1 |
| Listener protocol | `TCP`, `UDP`, or `TCP_UDP` (both) | Step 2 |
| Listener port range | One or more port ranges; each range 1-65535 | Step 2 |
| Client affinity | `NONE` (default, sticky on flow) or `SOURCE_IP` (sticky on source IP / 30s) | Step 2 |
| Endpoint group region | One group per AWS region per listener | Step 3 |
| Traffic dial | 0-100 (percentage). 0 drops all traffic to the group; 100 is full | Step 3 |
| Health check | Interval 10 or 30 sec, threshold 1-10, protocol TCP/HTTP/HTTPS, path (HTTP/HTTPS) | Step 3 |
| Endpoint type | ALB, NLB, EC2 instance, or Elastic IP — homogeneous per group | Step 4 |
| Endpoint weight | 0-999 (relative weight within group). 0 = drained | Step 4 |
| Client IP preservation | ALB: always via X-Forwarded-For. NLB/EC2: `PreserveClientIpEnabled` | Step 5 |
| Flow logs | CloudWatch Logs group OR S3 bucket with GA service principal grant | Step 6 |
| Cross-account endpoints | RAM resource share accepted in target account; endpoint ARN in peer account | Step 7 |
| Custom routing | Deterministic port-to-endpoint mapping (gaming, VoIP, media) | Step 8 |

**Global Accelerator limits (2026):**

- Accelerators per account (default): 100 (soft limit).
- Endpoint groups per listener: 1 per region (max ~20 groups, one per region).
- Endpoints per endpoint group: 100 (soft limit).
- Listeners per accelerator: 100.
- Port ranges per listener: 10.
- BYOIP IPv4 CIDR: /24 minimum (Amazon must approve ROA).
- Traffic dial granularity: integer 0-100.
- Endpoint weight granularity: integer 0-999.
- Health check interval: 10 or 30 seconds only.
- Dual-stack: requires accelerator created after Nov 2023 (or migrated).

## Pre-flight: deployment specification gate (run before architecture output)

Before producing the deployment plan, validate the input specification.
Several requirements **block deployment** — proceeding with an invalid
spec produces a non-functional or insecure accelerator.

Moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md) — load on demand.
Covers: Live-account pre-flight checks (IAM, endpoint ARN/region, BYOIP state, RAM share, flow-log destinations). See the "References (load on demand)" section.

| Attribute | Value | Effect on plan |
|---|---|---|
| Endpoint type | ALB | Client IP via X-Forwarded-For. Health check via ALB target group. |
| Endpoint type | NLB | PreserveClientIpEnabled controls origin visibility of client IP. |
| Endpoint type | EC2 instance | PreserveClientIpEnabled controls origin visibility of client IP. Single-AZ — pair with health check. |
| Endpoint type | Elastic IP | Static origin IP; client IP preserved by definition (EIP is the endpoint). |
| BYOIP | true | CIDR MUST be `PROVISIONED` in Route 53, advertised via GA. |
| Cross-account | true | RAM share `ACTIVE`; endpoint ARN belongs to peer account. |
| Custom routing | true | Listener port range maps deterministically to endpoint ports. |
| Dual-stack | true | Accelerator receives IPv4 and IPv6 anycast IPs. Requires accelerator created 2023+. |

**If the deployment spec is incomplete** (missing endpoint ARNs, region,
or listener protocol), output:

```text
ACCELERATOR_SPEC: <name-or-unknown>
VERDICT: PREREQUISITES_MISSING
REASON: Deployment specification is missing required fields (<list>).
Cannot produce an accelerator plan without <field> — the resulting
deployment would be non-functional or insecure.
REQUIRED:
  - endpoint_type (ALB, NLB, EC2, or Elastic IP)
  - region(s) for endpoint groups
  - listener_protocol (TCP, UDP, or TCP_UDP)
  - listener_port_range(s)
  - traffic_steering_model (single-region, multi-region active-active, active-passive)
  - flow_log_destination (CloudWatch or S3, optional but recommended)
```

## Process — Architecture planning (apply in order, produce deployment plan)

### Step 0: Expert knowledge — non-obvious Global Accelerator behaviors that change the plan

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — load on demand.
Covers: Step 0: Expert knowledge — non-obvious Global Accelerator behaviors that change the plan. See the "References (load on demand)" section.

### Step 1: Accelerator creation — IP source and IP version

```bash
aws globalaccelerator create-accelerator \
  --name prod-ga \
  --ip-addresses "IPV4" \
  --idempotency-token "$(uuidgen)"
```

**BYOIP variant:**

```bash
# 1. Provision in Route 53 (one-time per CIDR)
aws ec2 provision-byoip-cidr \
  --cidr "203.0.113.0/24" \
  --cidr-authorization-context Message="$(cat signed-message.txt)",MessageSignature="..."

# 2. Wait for PROVISIONED
aws ec2 describe-byoip-cidrs --max-results 10

# 3. Create accelerator advertising the BYOIP CIDR
aws globalaccelerator create-accelerator \
  --name prod-ga-byoip \
  --ip-addresses "IPV4" \
  --byoip-cidrs "203.0.113.0/24" \
  --idempotency-token "$(uuidgen)"
```

| IP source | Use case | Notes |
|---|---|---|
| Amazon pool (default) | New accelerator, no IP reputation constraints | 2 anycast IPs allocated permanently. |
| BYOIP | Existing IP reputation, allowlist-enforced partners, predictable CIDR | Requires /24 minimum, ROA + Route 53 provisioning, `PROVISIONED` state. |
| Dual-stack (Amazon pool) | IPv6-native clients (mobile, IoT) | IPv4 + IPv6 anycast IPs. Requires accelerator created Nov 2023+. |
| BYOIP dual-stack | Existing IPv4 + IPv6 ranges | Both CIDRs must be PROVISIONED. |

### Step 2: Listener — protocol, port range, client affinity

```bash
aws globalaccelerator create-listener \
  --accelerator-arn <arn> \
  --protocol "TCP" \
  --port-ranges "FromPort=443,ToPort=443" \
  --client-affinity "NONE" \
  --region us-west-2
```

| Protocol | When to use |
|---|---|
| `TCP` | HTTPS, HTTP/2, HTTP/3 (TCP), SSH, custom TCP protocols |
| `UDP` | QUIC, VoIP (RTP/UDP), gaming (UDP), DNS-over-UDP |
| `TCP_UDP` | Same port on both protocols (e.g., DNS service on 53) |

| Client affinity | When to use |
|---|---|
| `NONE` (default) | Stateless endpoints (HTTP, API). GA load-balances per-flow. |
| `SOURCE_IP` | Stateful endpoints (gaming sessions, long-lived streams). Sticky for the source IP. |

**Anti-pattern:** NEVER set `SOURCE_IP` for stateless HTTP workloads — it
defeats load balancing and pins one user to one endpoint, creating hot
shards when a CDN or NAT sits in front of many users.

### Step 3: Endpoint group — region, traffic dial, health check

```bash
aws globalaccelerator create-endpoint-group \
  --listener-arn <arn> \
  --endpoint-group-region "us-east-1" \
  --traffic-dial 100.0 \
  --health-check-interval-seconds 30 \
  --health-check-path "/" \
  --health-check-port 443 \
  --health-check-protocol "HTTPS" \
  --threshold-count 3 \
  --region us-west-2
```

| Traffic dial | Behavior |
|---|---|
| 100 | Full traffic to this region's endpoints (active-active peer: also 100). |
| 50 | Half-weight relative to peer regions (canary, blue-green). |
| 5 | Minimal traffic (drain candidate — leave at 5 until connections close, then 0). |
| 0 | Hard cut. All new flows go to peer regions. Existing flows may be dropped. |

| Health check interval | Use case |
|---|---|
| 10 seconds | Real-time / latency-sensitive workloads. Higher GA cost. |
| 30 seconds (default) | General-purpose. Lower cost, slower failover. |

**Threshold count:** number of consecutive failed health checks before
GA marks the endpoint unhealthy. Default 3. Lower for faster failover
(at the cost of more flapping).

### Step 4: Endpoints — type, ARN, weight, homogeneity rule

```bash
aws globalaccelerator add-endpoints \
  --endpoint-group-arn <arn> \
  --endpoint-configurations \
    '[{"EndpointId":"arn:aws:elasticloadbalancing:us-east-1:111111111111:loadbalancer/app/prod-alb/abc","Weight":128,"ClientIPReservationEnabled":false}]' \
  --region us-west-2
```

| Endpoint type | ARN shape | Notes |
|---|---|---|
| ALB | `arn:aws:elasticloadbalancing:<region>:<acct>:loadbalancer/app/<name>/<id>` | Client IP via X-Forwarded-For. Health check via target group. |
| NLB | `arn:aws:elasticloadbalancing:<region>:<acct>:loadbalancer/net/<name>/<id>` | PreserveClientIpEnabled controls L4 source IP. |
| EC2 | `i-0123456789abcdef0` (instance ID, not ARN) | Single-AZ. PreserveClientIpEnabled controls L4 source IP. |
| Elastic IP | `eipalloc-0123456789abcdef0` (allocation ID) | Static L4 endpoint. Client IP preserved by definition. |

**Homogeneity rule:** within a single endpoint group, all endpoints MUST
be the same type. Mixing types returns `ValidationError`. Multi-type
designs require separate endpoint groups (in different regions).

**Weight:** relative within the group. If endpoint A has weight 128 and
endpoint B has weight 64, A gets 2/3 of the group's traffic and B gets
1/3. Weight 0 = graceful drain (no new connections, existing stay).

### Step 5: Client IP preservation — origin visibility decision

| Endpoint type | PreserveClientIpEnabled default | Effect |
|---|---|---|
| ALB | N/A (always via X-Forwarded-For) | ALB sees AWS GA IP at L4; reads client IP from X-Forwarded-For. Origin security group can scope to GA prefix pool. |
| NLB | `false` (recommended default) | NLB sees AWS GA IP at L4. Origin SG scopes to GA prefix pool. WAF at NLB sees client IP via the listener policy if enabled. |
| NLB | `true` | NLB sees real client IP at L4. Origin SG MUST allow client IP ranges. IP-based rate limiting and geo-blocking work at origin. |
| EC2 | `false` (recommended default) | EC2 sees AWS GA IP. SG scopes to GA prefix pool. |
| EC2 | `true` | EC2 sees real client IP. SG MUST allow client IP ranges. Application logs reflect real client IP. |
| Elastic IP | N/A (EIP is the endpoint) | EIP receives traffic directly; client IP is preserved by definition. |

**GA prefix pool (2026):** `51.224.0.0/14` (IPv4). When
PreserveClientIpEnabled is false, origins see source IPs from this
pool. Add this CIDR to security group inbound rules.

### Step 6: Flow logs — CloudWatch Logs or S3

Moved verbatim to [references/ip-preservation-and-flowlogs-guide.md](references/ip-preservation-and-flowlogs-guide.md) — load on demand.
Covers: Step 6: Flow logs — CloudWatch Logs or S3. See the "References (load on demand)" section.

### Step 7: Cross-account endpoints (2024+) — RAM resource share

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — load on demand.
Covers: Step 7: Cross-account endpoints (2024+) — RAM resource share. See the "References (load on demand)" section.

### Step 8: Custom routing accelerator — deterministic port mapping

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — load on demand.
Covers: Step 8: Custom routing accelerator — deterministic port mapping. See the "References (load on demand)" section.

## Common patterns

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — load on demand.
Covers: Common patterns. See the "References (load on demand)" section.

## Output format

```text
ACCELERATOR_SPEC: <name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
ARCHITECTURE:
  IP source: <Amazon pool | BYOIP 203.0.113.0/24>
  IP version: <IPv4 | dual-stack IPv4+IPv6>
  Accelerator region: <us-west-2 (control-plane only)>
  Listener: <protocol> ports <range> affinity <NONE|SOURCE_IP>
  Endpoint groups: <count> regions <list>
  Endpoints: <count> type <ALB|NLB|EC2|EIP> weights <list>
  Client IP preservation: <ALB: X-Forwarded-For | NLB: enabled | NLB: disabled | EC2: enabled>
  Flow logs: <CloudWatch group | S3 bucket | none>
  Cross-account: <count> endpoints via RAM share
  Custom routing: <yes | no>
CHECKLIST:
  [x] Accelerator region valid (control-plane only; traffic is global)
  [x] IP source verified (Amazon pool or BYOIP PROVISIONED)
  [x] Listener protocol + port range valid
  [x] Client affinity NONE for stateless, SOURCE_IP for stateful
  [x] Endpoint groups one-per-region
  [x] Endpoint types homogeneous within each group
  [x] Endpoint ARNs resolve in target region
  [x] Traffic dial 0-100 per group; endpoint weight 0-999 per endpoint
  [x] Health check protocol matches endpoint type
  [x] Client IP preservation matches origin SG posture
  [x] Flow log destination permission verified
  [x] Cross-account RAM share ACTIVE (if applicable)
  [x] Custom routing destination configs valid (if applicable)
FINDINGS:
  - [INFO] Estimated monthly cost: $0.025/hr fixed + $0.02/GB ingress forwarding
  - [WARN] Traffic dial 0 on us-west-2 — hard cut, no graceful drain
DEPLOY_COMMANDS:
  <ordered list of aws globalaccelerator create-* commands>
```

## STRICT output contract

### Required output structure

Every response MUST begin with this block — no preamble, no
conversational opening:

```text
ACCELERATOR: <accelerator-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
TARGET: <accelerator-name> (accelerator-arn: <arn> for updates)
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. CONFIRM: About to <operation> accelerator <name> in account <account>. This will <consequence>. Estimated monthly cost: <$X>. Proceed? (yes/no)
  2. <exact CLI command — no placeholders>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
IP_SOURCE: Amazon pool (2 anycast IPs) | BYOIP <CIDR>
LISTENER: <protocol> <port-range> affinity <NONE|SOURCE_IP>
ENDPOINT_GROUPS: <count> regions <list>
ENDPOINTS: <count> type <ALB|NLB|EC2|EIP> preservation <enabled|disabled|X-Forwarded-For>
FLOW_LOGS: <CloudWatch group | S3 bucket | none>
NOTES: <traffic steering model, failover behavior, cost posture>
```

### FORBIDDEN output patterns

- NEVER start with "Let me analyze…" or "I'll create…" — the VERDICT
  block is the FIRST line, always. No conversational preamble.
- NEVER use lowercase verdict values — emit `READY_TO_DEPLOY` or
  `PREREQUISITES_MISSING` (not `ready`, `prerequisites`).
- NEVER omit PRE_CHECKS — every pre-check run must appear with `[PASS]`
  or `[FAIL]` and a specific reason for each failure. An empty
  PRE_CHECKS block is non-compliant.
- NEVER emit a plan with placeholder values (e.g., `<accelerator-arn>`,
  `<account-id>`) in a READY_TO_DEPLOY plan — every field must be
  populated with actual values from the input.
- NEVER omit the CONFIRM gate as the first STEPS entry for any
  state-changing operation.
- NEVER claim success without verifying the accelerator is `DEPLOYED`
  via `describe-accelerator` — a partial CLI sequence with missing
  listener or endpoint group is non-compliant.
- NEVER silently allow mixed endpoint types in one group — block it
  explicitly with a [FAIL] pre-check row naming the validation error.
- NEVER claim BYOIP is ready without verifying `PROVISIONED` state in
  Route 53 (not `PENDING_PROVISIONING`, not `FAILED_PROVISIONING`).

### Perfect example output

```text
ACCELERATOR: prod-ga-multi-region
VERDICT: READY_TO_DEPLOY
TARGET: prod-ga-multi-region
PRE_CHECKS:
  - [PASS] Accelerator region us-west-2 valid (control-plane only)
  - [PASS] Amazon pool IP source (no BYOIP provisioning required)
  - [PASS] Listener TCP 443 affinity NONE (stateless HTTPS)
  - [PASS] Endpoint group us-east-1 region matches ALB ARN region
  - [PASS] Endpoint group eu-west-1 region matches ALB ARN region
  - [PASS] Endpoint types homogeneous within each group (ALB only)
  - [PASS] ALB arn:aws:elasticloadbalancing:us-east-1:111111111111:loadbalancer/app/prod-use1/abc resolves state=active
  - [PASS] ALB arn:aws:elasticloadbalancing:eu-west-1:111111111111:loadbalancer/app/prod-euw1/def resolves state=active
  - [PASS] Traffic dial 100 in both regions (active-active)
  - [PASS] Health check HTTPS / 30s / threshold 3 matches ALB target group
  - [PASS] Flow log S3 bucket policy grants s3:PutObject to flowlogs.globalaccelerator.amazonaws.com
  - [PASS] IAM principal holds globalaccelerator:CreateAccelerator, CreateListener, CreateEndpointGroup, AddEndpoints
STEPS:
  1. CONFIRM: About to create-accelerator prod-ga-multi-region in account 111111111111. Allocates 2 anycast IPs, TCP/443 listener, 2 endpoint groups (us-east-1 + eu-west-1), 2 ALB endpoints, S3 flow logs. Estimated cost: $18/mo fixed + $0.02/GB ingress. Proceed? (yes/no)
  2. aws globalaccelerator create-accelerator --name prod-ga-multi-region --ip-addresses IPV4 --idempotency-token "$(uuidgen)"
  3. aws globalaccelerator create-listener --accelerator-arn <arn> --protocol TCP --port-ranges FromPort=443,ToPort=443 --client-affinity NONE --region us-west-2
  4. aws globalaccelerator create-endpoint-group --listener-arn <arn> --endpoint-group-region us-east-1 --traffic-dial 100.0 --health-check-interval-seconds 30 --health-check-path / --health-check-port 443 --health-check-protocol HTTPS --threshold-count 3 --region us-west-2
  5. aws globalaccelerator add-endpoints --endpoint-group-arn <arn> --endpoint-configurations '[{"EndpointId":"arn:aws:elasticloadbalancing:us-east-1:111111111111:loadbalancer/app/prod-use1/abc","Weight":128}]' --region us-west-2
  6. aws globalaccelerator create-endpoint-group --listener-arn <arn> --endpoint-group-region eu-west-1 --traffic-dial 100.0 --health-check-interval-seconds 30 --health-check-path / --health-check-port 443 --health-check-protocol HTTPS --threshold-count 3 --region us-west-2
  7. aws globalaccelerator add-endpoints --endpoint-group-arn <arn> --endpoint-configurations '[{"EndpointId":"arn:aws:elasticloadbalancing:eu-west-1:111111111111:loadbalancer/app/prod-euw1/def","Weight":128}]' --region us-west-2
  8. aws globalaccelerator update-accelerator-attributes --accelerator-arn <arn> --flow-logs-s3-bucket prod-ga-flowlogs --region us-west-2
POST_VERIFY:
  - (pending execution)
  - describe-accelerator returns Status=DEPLOYED
  - list-endpoint-groups returns 2 groups (us-east-1 + eu-west-1), both traffic-dial=100
  - S3 bucket prod-ga-flowlogs receives flow log objects within 5 minutes of test traffic
IP_SOURCE: Amazon pool (2 anycast IPs)
LISTENER: TCP 443-443 affinity NONE
ENDPOINT_GROUPS: 2 regions us-east-1, eu-west-1
ENDPOINTS: 2 type ALB preservation X-Forwarded-For
FLOW_LOGS: S3 bucket prod-ga-flowlogs
NOTES:
  - Active-active: each user routes to the closest region. Per-endpoint health check fails over within 30 sec.
  - Client IP at origin: ALB reads X-Forwarded-For (not the L4 socket source).
  - Cost: ~$18/mo fixed + $0.02/GB. 1 TB/mo ingress ~= $38/month.
  - DNS: map app.example.com A+AAAA to the 2 anycast IPs returned by describe-accelerator.
```

## NEVER (top 5)

These are the highest-impact, most-frequent failure modes in Global
Accelerator deployments. Violating any one of these is a correctness
or security regression.

1. **NEVER mix endpoint types within a single endpoint group.** The
   `AddEndpoints` API returns `ValidationError`. Multi-type designs
   require separate endpoint groups, each in a different region (by
   the model's definition). Pre-check this before emitting any CLI.

2. **NEVER set traffic dial to 0 for graceful drain.** Traffic dial 0
   is a hard cut — new flows stop immediately, existing flows may be
   dropped. For graceful drain, reduce to 5, wait for connections to
   close (verify via flow logs), then go to 0. Endpoint weight 0
   within a group IS graceful drain.

3. **NEVER advertise a BYOIP CIDR that is not `PROVISIONED` in
   Route 53.** GA cannot advertise a CIDR that is not provisioned in
   your account. Verify `describe-byoip-cidrs` returns `PROVISIONED`
   (not `PENDING_PROVISIONING`, not `FAILED_PROVISIONING`). The ROA
   must also be published with your RIR before provisioning.

4. **NEVER assume PreserveClientIpEnabled is "just a toggle."** When
   enabled for NLB or EC2, the origin's security group MUST allow
   client IP ranges (not just the GA prefix pool). When disabled, the
   origin sees AWS GA IPs and IP-based rate limiting / geo-blocking
   at the origin silently breaks. State the SG posture in the
   PRE_CHECKS row.

5. **NEVER configure flow logs without verifying the destination
   permission.** GA silently drops logs on permission errors. For
   CloudWatch, verify the service-linked role has `logs:PutLogEvents`.
   For S3, verify the bucket policy grants `s3:PutObject` to
   `flowlogs.globalaccelerator.amazonaws.com`. Send test traffic and
   confirm log entries appear within 5 minutes.

## Expert heuristic: choosing client IP preservation per endpoint type

Moved verbatim to [references/ip-preservation-and-flowlogs-guide.md](references/ip-preservation-and-flowlogs-guide.md) — load on demand.
Covers: Expert heuristic: choosing client IP preservation per endpoint type. See the "References (load on demand)" section.

## Recent AWS features (2024-2026)

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — load on demand.
Covers: Recent AWS features (2024-2026). See the "References (load on demand)" section.

## AWS documentation

- **AWS Global Accelerator Developer Guide** — https://docs.aws.amazon.com/global-accelerator/latest/dg/what-is-global-accelerator.html
- **Global Accelerator endpoints** — https://docs.aws.amazon.com/global-accelerator/latest/dg/about-endpoints.html
- **Client IP preservation** — https://docs.aws.amazon.com/global-accelerator/latest/dg/preserve-client-ip-address.html
- **BYOIP in Global Accelerator** — https://docs.aws.amazon.com/global-accelerator/latest/dg/using-byoip-in-global-accelerator.html
- **Custom routing accelerators** — https://docs.aws.amazon.com/global-accelerator/latest/dg/about-custom-routing-accelerators.html
- **Cross-account endpoints** — https://docs.aws.amazon.com/global-accelerator/latest/dg/cross-account-resources.html
- **Flow logs** — https://docs.aws.amazon.com/global-accelerator/latest/dg/monitoring-global-accelerator.flow-logs.html
- **Global Accelerator API Reference** — https://docs.aws.amazon.com/global-accelerator/latest/api/Welcome.html
- **AWS RAM Developer Guide** — https://docs.aws.amazon.com/ram/latest/userguide/what-is.html

## References (load on demand)

- [references/endpoint-and-listener-guide.md](references/endpoint-and-listener-guide.md) — endpoint types, listener protocols, and endpoint-group topology (existing)
- [references/ip-preservation-and-flowlogs-guide.md](references/ip-preservation-and-flowlogs-guide.md) — client IP preservation and flow log destinations (existing); now also the Step 6 flow-log CLI and the client-IP-preservation decision heuristic
- [references/advanced-patterns.md](references/advanced-patterns.md) — Step 0 expert-knowledge deep dive, cross-account RAM endpoints (Step 7), custom routing accelerators (Step 8), common patterns, and recent AWS features
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — live-account pre-flight check commands (IAM, endpoint ARN/region, BYOIP state, RAM share, flow-log destinations)
