---
description: Provision a production-grade AWS Global Accelerator with anycast IPs, listener, endpoint groups, client IP preservation, flow logs, and optional cross-account or custom routing.
nl_triggers:
  - "create a Global Accelerator"
  - "provision an accelerator with static IPs"
  - "multi-region active-active accelerator"
  - "BYOIP advertise through Global Accelerator"
  - "client IP preservation for NLB"
  - "cross-account endpoint share"
  - "custom routing accelerator"
  - "Global Accelerator endpoint group"
  - "traffic dial multi-region"
  - "Global Accelerator flow logs"
  - "dual-stack IPv6 accelerator"
  - "anycast IPs for my ALB"
  - "Global Accelerator with NLB endpoint"
  - "centralized edge accelerator"
routes_to: globalaccelerator-deployer
---

# /aws:deploy-globalaccelerator

Activate the `globalaccelerator-deployer` skill and produce a
deployment plan for a production-grade AWS Global Accelerator with
secure defaults.

## What it does

Reads a deployment specification (endpoint types, regions, listener
protocol and port range, traffic steering model, BYOIP requirement,
client IP preservation requirement, flow log destination, and
cross-account requirement) and produces an ordered deployment plan
with:

1. Pre-flight specification gate — validates endpoint ARNs resolve
   in the target region, endpoint types are homogeneous within each
   group, listener protocol and port range valid, BYOIP CIDR is
   `PROVISIONED` in Route 53, cross-account RAM share is `ACTIVE`,
   flow log destination permission verified. Blocks deployment
   (PREREQUISITES_MISSING) on missing fields or invalid config.
2. Accelerator creation — Amazon pool (2 anycast IPs, default) or
   BYOIP (requires ROA + Route 53 provisioning + `PROVISIONED` state).
   Optional dual-stack IPv4+IPv6 (accelerator created Nov 2023+).
3. Listener — protocol (`TCP`, `UDP`, or `TCP_UDP`), port ranges
   (1-65535, up to 10 ranges), client affinity (`NONE` default or
   `SOURCE_IP` for stateful workloads).
4. Endpoint group — one per AWS region per listener. Traffic dial
   (0-100, per-region). Health check (interval 10 or 30 sec,
   threshold, protocol TCP/HTTP/HTTPS, path, port).
5. Endpoints — ALB, NLB, EC2 instance, or Elastic IP. Homogeneous
   per group (mixed types rejected by API). Endpoint weight (0-999,
   relative within group; 0 = graceful drain).
6. Client IP preservation — ALB always via `X-Forwarded-For`.
   NLB and EC2 configurable via `PreserveClientIpEnabled`. Determines
   origin security group posture (GA prefix pool vs client CIDRs).
7. Flow logs — CloudWatch Logs group (service-linked role permission)
   or S3 bucket (bucket policy grant to
   `flowlogs.globalaccelerator.amazonaws.com`).
8. Cross-account endpoints (2024+) — RAM resource share `ACTIVE`
   before `add-endpoints`. Centralized edge platform pattern.
9. Custom routing accelerator (optional) — deterministic
   port-to-endpoint mapping for gaming, VoIP, media workloads.

Emits a deterministic deployment plan per accelerator:

```text
ACCELERATOR: <name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
TARGET: <name>
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. CONFIRM: About to <operation> accelerator <name> in account <account>. Estimated monthly cost: <$X>. Proceed? (yes/no)
  2. <exact CLI command — no placeholders>
POST_VERIFY:
  - [PASS] <verification description>
IP_SOURCE: Amazon pool | BYOIP <CIDR>
LISTENER: <protocol> <port-range> affinity <NONE|SOURCE_IP>
ENDPOINT_GROUPS: <count> regions <list>
ENDPOINTS: <count> type <ALB|NLB|EC2|EIP> preservation <enabled|disabled|X-Forwarded-For>
FLOW_LOGS: <CloudWatch group | S3 bucket | none>
NOTES: <traffic steering model, failover behavior, cost posture>
```

## When to invoke

Provide a deployment spec and ask any of:

- "provision a multi-region active-active Global Accelerator"
- "create a Global Accelerator with BYOIP"
- "client IP preservation for my NLB endpoint"
- "cross-account endpoint in another AWS account"
- "custom routing accelerator for my game servers"
- "flow logs from Global Accelerator to S3"
- "dual-stack IPv4+IPv6 accelerator"

A bare endpoint + protocol + "deploy accelerator" also routes here
via the orchestrator.

## Inputs

- **Required:** endpoint_type (ALB, NLB, EC2, or Elastic IP),
  region(s) for endpoint groups, listener_protocol (TCP, UDP, or
  TCP_UDP), listener_port_range(s), traffic_steering_model
  (single-region, multi-region active-active, active-passive).
- **Optional:** ip_source (Amazon pool or BYOIP CIDR), ip_version
  (IPv4 or dual-stack), client_affinity (NONE or SOURCE_IP),
  preserve_client_ip_enabled (NLB/EC2 only),
  flow_log_destination (CloudWatch group or S3 bucket),
  cross_account_ram_share_arn, custom_routing (true/false).

## Outputs

- One VERDICT block per accelerator (READY_TO_DEPLOY or
  PREREQUISITES_MISSING).
- PRE_CHECKS with all dimensions validated (anycast IP source,
  endpoint homogeneity, region matching, health check, flow log
  permission, IAM, RAM share for cross-account).
- STEPS with ordered `aws globalaccelerator create-*` and
  `add-endpoints` commands, starting with the CONFIRM gate.
- POST_VERIFY with verification steps (describe-accelerator returns
  DEPLOYED, flow log objects appear within 5 minutes of test
  traffic).
- NOTES with traffic steering model, failover behavior, and cost
  posture.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 1 Deploy specialist for Global Accelerator edge
  networking).
- `/aws:audit-cloudfront-distribution` for edge CDN security
  auditing (CloudFront complements GA for HTTP content caching).
- `/aws:audit-direct-connect-topology` for dedicated-network
  auditing (Direct Connect complements GA for private connectivity).
