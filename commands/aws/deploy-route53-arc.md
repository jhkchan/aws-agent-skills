---
description: Provision Route 53 Application Recovery Controller (ARC) with production-grade defaults (recovery cluster, routing controls, safety rules, readiness checks, resource sets, cells, control panels). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "route 53 arc"
  - "application recovery controller"
  - "routing control"
  - "safety rule arc"
  - "readiness check"
  - "recovery cluster"
  - "control panel"
  - "cell failover"
  - "resource set"
  - "readiness scope"
  - "arc failover"
routes_to: route53-application-recovery-controller-deployer
---

# /aws:deploy-route53-arc

Activate the `route53-application-recovery-controller-deployer` skill
and provision Route 53 ARC with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Recovery cluster architecture (five-cluster quorum data plane)
2. Cells and resource sets (type mapping, cell scoping)
3. Control panels and routing controls (boolean ON/OFF toggle)
4. Safety rules (AND/OR types, prevent unsafe failover)
5. Readiness checks (per-resource-set validation)
6. Cross-region readiness assessment (aggregate cell readiness)
7. Routing control state and CloudWatch monitoring
8. Failover execution patterns (active-standby, active-active)
9. Route 53 health check integration
10. Recent features (new resource types, multi-account readiness)

## When to use

- You need to create routing controls for application failover.
- You are building an active-active or active-standby multi-region setup.
- You need safety rules to prevent unsafe failover.
- You need readiness checks to validate cells before failover.
- You need cells and resource sets for multi-region readiness.
- You need Route 53 health checks backed by routing control state.

## When NOT to use

- **Route 53 health checks only** — use health-check skills for simple
  endpoint monitoring.
- **Route 53 DNS failover (non-ARC)** — use DNS failover skills for
  standard weighted/latency-based failover.
- **Elastic Disaster Recovery** — use DRS skills for OS-level DR.
- **Auto Scaling group failover** — use ASG skills for capacity-based
  failover within a region.

## How to invoke

### Slash command

```
/aws:deploy-route53-arc
```

Then provide: cell definitions (regions, resource ARNs), resource types
(CloudFormation types), topology (active-active or active-standby),
safety rule requirements, cluster name, tags.

### Natural language

Any of these routes to the same skill:

- "create route 53 arc routing controls"
- "set up application recovery controller"
- "configure safety rules for failover"
- "create readiness checks for my multi-region app"
- "deploy arc control panel with routing controls"

### CLI routing

```bash
node cli/bin/cli.js route "create route 53 arc"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create ARC
failover infrastructure. The output checklist feeds into verification
pipelines and downstream audit skills.

## Example

```
You: /aws:deploy-route53-arc

     Create ARC for my app. Cell-A in us-east-1, Cell-B in
     us-west-2. Active-standby. NLB and ASG resource sets.
     Safety rule to prevent total outage.

Skill:
  ARC: app-recovery-cluster
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Recovery cluster: ACTIVE
    [✓] Routing controls: cell-a-traffic, cell-b-traffic
    [✓] Safety rule: prevent-total-outage (OR, threshold 1)
    [✓] Readiness checks: app-nlb-check, app-asg-check
    [✓] Topology: Active-Standby
  VERIFICATION_COMMANDS:
    aws route53-recovery-cluster get-routing-control-state --routing-control-arn <arn>
```

## References

- Skill definition: `skills/route53-application-recovery-controller-deployer/SKILL.md`
- Routing controls guide: `skills/route53-application-recovery-controller-deployer/references/routing-controls-and-safety.md`
- Readiness guide: `skills/route53-application-recovery-controller-deployer/references/readiness-and-resource-sets.md`
- Eval suite: `skills/route53-application-recovery-controller-deployer/evals/evals.json`
