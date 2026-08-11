---
description: Provision an AWS Global Accelerator with production-grade defaults (two static anycast IPs, TCP/UDP listeners, endpoint groups with traffic dial and health checks, endpoint types ALB/NLB/EC2/EIP with weights, client IP preservation, BYOIP integration, flow logs, failover). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create global accelerator"
  - "deploy global accelerator"
  - "global accelerator anycast"
  - "anycast ip addresses"
  - "traffic dial"
  - "endpoint group"
  - "endpoint weight"
  - "global accelerator listener"
  - "client ip preservation"
  - "global accelerator failover"
  - "byoip accelerator"
  - "accelerator flow logs"
  - "multi-region accelerator"
routes_to: global-accelerator-endpoint-deployer
---

# /aws:deploy-global-accelerator-endpoint

Activate the `global-accelerator-endpoint-deployer` skill and provision
an AWS Global Accelerator with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Accelerator creation (two static anycast IPs pinned at creation)
2. Listener (TCP/UDP ports, client affinity)
3. Endpoint group (region, traffic dial, health checks)
4. Endpoint types and weights (ALB, NLB, EC2, EIP)
5. Client IP address preservation
6. Cross-region routing and DNS naming
7. BYOIP integration
8. Flow logs and CloudWatch metrics
9. Endpoint group failover (active-passive, active-active)
10. Recent features (dual-stack, cross-account, custom routing)

## When to use

- You need to create a Global Accelerator with static anycast IPs.
- You are setting up multi-region endpoints with traffic dial.
- You need regional canary deployment via traffic dial.
- You need within-region distribution via endpoint weights.
- You need BYOIP integration.
- You need endpoint group failover.
- You need flow logs or CloudWatch metrics.

## When NOT to use

- **CloudFront** — CDN/edge caching is different from Layer 4 anycast.
- **Route 53** — DNS routing policies are a different layer.
- **Elastic Load Balancing v2 directly** — without Global Accelerator.
- **Transit Gateway** — VPC connectivity, not global anycast routing.

## How to invoke

### Slash command

```
/aws:deploy-global-accelerator-endpoint
```

Then provide: accelerator name, anycast IP type (IPV4/DUAL_STACK),
BYOIP pool (if applicable), listener protocol and ports, endpoint
group regions, traffic dial values, endpoint IDs and weights, health
check parameters, client IP preservation, flow log destination, tags.

### Natural language

Any of these routes to the same skill:

- "create a global accelerator with two anycast IPs"
- "set up multi-region failover with Global Accelerator"
- "configure traffic dial for regional canary"
- "add endpoints to my Global Accelerator"
- "enable BYOIP for my accelerator"

### CLI routing

```bash
node cli/bin/cli.js route "create a global accelerator"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create Global
Accelerator resources. The output checklist feeds into verification
pipelines and downstream audit skills.

## Example

```
You: /aws:deploy-global-accelerator-endpoint

     Create a Global Accelerator with active-passive failover.
     Primary us-east-1 traffic dial 1.0, DR us-west-2 traffic
     dial 0.0. ALB endpoints in each region. Listener TCP 443.

Skill:
  GLOBAL_ACCELERATOR: prod-accelerator
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Anycast IPs: 192.0.2.1, 192.0.2.2 — PINNED at creation
    [✓] Listener: TCP port 443
    [✓] Endpoint group (us-east-1): traffic dial 1.0
    [✓] Endpoint group (us-west-2): traffic dial 0.0
    [✓] Failover strategy: Active-passive
  VERIFICATION_COMMANDS:
    aws globalaccelerator describe-accelerator --accelerator-arn <arn>
    aws globalaccelerator list-endpoint-groups --listener-arn <arn>
```

## References

- Skill definition: `skills/global-accelerator-endpoint-deployer/SKILL.md`
- Anycast and traffic dial guide: `skills/global-accelerator-endpoint-deployer/references/anycast-and-traffic-dial.md`
- Endpoint types and failover guide: `skills/global-accelerator-endpoint-deployer/references/endpoint-types-and-failover.md`
- Eval suite: `skills/global-accelerator-endpoint-deployer/evals/evals.json`
