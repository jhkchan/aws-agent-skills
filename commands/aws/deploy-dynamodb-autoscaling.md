---
description: Provision DynamoDB auto-scaling with production-grade defaults (target tracking for table RCU/WCU, GSI RCU/WCU, application-autoscaling SLR, on-demand vs provisioned decision, throttle monitoring). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "dynamodb autoscaling"
  - "dynamodb target tracking"
  - "dynamodb capacity auto-scaling"
  - "gsi autoscaling"
  - "provisioned capacity autoscaling"
  - "dynamodb throttling"
  - "application autoscaling dynamodb"
  - "dynamodb on-demand vs provisioned"
  - "dynamodb scaling policy"
  - "dynamodb cooldown"
  - "dynamodb read capacity units"
  - "dynamodb write capacity units"
  - "target utilization dynamodb"
routes_to: dynamodb-autoscaling-deployer
---

# /aws:deploy-dynamodb-autoscaling

Activate the `dynamodb-autoscaling-deployer` skill and provision
DynamoDB auto-scaling with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. On-demand vs provisioned with auto-scaling (capacity mode decision)
2. Application auto-scaling role (SLR setup)
3. Table target tracking (read/write capacity)
4. GSI target tracking (read/write capacity)
5. Scaling policy parameters (utilization, cooldowns)
6. Throttle metrics and monitoring
7. Recent features (capacity mode auto-switching)

## When to use

- You need to configure DynamoDB auto-scaling for a table or GSI.
- You are choosing between on-demand and provisioned capacity mode.
- You need to set up target tracking scaling policies.
- You want to tune target utilization and cooldowns.
- You need to monitor throttle metrics with CloudWatch alarms.

## When NOT to use

- **Creating a DynamoDB table from scratch** — use
  `deploy-dynamodb-table`.
- **Auditing table configuration** — use a DynamoDB auditor.
- **DynamoDB Global Tables** (multi-region replication) — separate
  feature, not auto-scaling.

## How to invoke

### Slash command

```
/aws:deploy-dynamodb-autoscaling
```

Then provide: table name/ARN, capacity mode (PROVISIONED or
ON-DEMAND), GSI names, target utilization, Min/Max capacity,
cooldowns, throttle alarm SNS ARN.

### Natural language

Any of these routes to the same skill:

- "configure dynamodb autoscaling for orders-table"
- "set up target tracking for my gsi"
- "switch my table to provisioned and enable auto-scaling"
- "create a throttle alarm for dynamodb"

### CLI routing

```bash
node cli/bin/cli.js route "configure dynamodb autoscaling"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to configure or
update DynamoDB capacity auto-scaling. The output checklist feeds
into verification pipelines and downstream monitoring skills.

## Example

```
You: /aws:deploy-dynamodb-autoscaling

     Configure auto-scaling for orders-table (PROVISIONED mode).
     Table RCU/WCU: Min=10, Max=40000, Target=70%.
     GSI status-index RCU/WCU: Min=5, Max=20000, Target=70%.
     Throttle alarm to SNS alerts. Account: 111111111111.

Skill:
  DYNAMODB_AUTOSCALING: orders-table
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Capacity mode: PROVISIONED
    [✓] Table read scaling: Min=10, Max=40000, Target=70%
    [✓] Table write scaling: Min=10, Max=40000, Target=70%
    [✓] GSI status-index read scaling: Min=5, Max=20000, Target=70%
    [✓] GSI status-index write scaling: Min=5, Max=20000, Target=70%
    [✓] Throttle alarm: ThrottledRequests > 0 → SNS
  VERIFICATION_COMMANDS:
    aws application-autoscaling describe-scaling-policies --service-namespace dynamodb --resource-id table/orders-table
    aws cloudwatch describe-alarms --namespace AWS/DynamoDB
```

## References

- Skill definition: `skills/dynamodb-autoscaling-deployer/SKILL.md`
- Target tracking and cooldowns: `skills/dynamodb-autoscaling-deployer/references/target-tracking-and-cooldowns.md`
- Capacity modes and throttling: `skills/dynamodb-autoscaling-deployer/references/capacity-modes-and-throttling.md`
- Eval suite: `skills/dynamodb-autoscaling-deployer/evals/evals.json`
