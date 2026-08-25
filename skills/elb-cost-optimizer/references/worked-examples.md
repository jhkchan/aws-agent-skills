# ELB Cost Optimizer — worked examples (load on demand)

Secondary worked examples, moved verbatim from SKILL.md.

## NEED_MORE_INFO output block (Step 0: missing LB data / metrics) (moved verbatim from SKILL.md lines 169-181)

```text
TARGET: <load balancer or account>
VERDICT: NEED_MORE_INFO
REASON: Cannot optimize ELB cost without LCU metrics and LB inventory.
MISSING:
  - Load balancer ARN or name
  - CloudWatch ConsumedLCUs (14+ days)
  - CloudWatch per-dimension metrics: NewConnectionCount,
    ActiveConnectionCount, ProcessedBytes, RuleEvaluations
  - Listener and target group configuration
  - Monthly ELB spend (from Cost Explorer)
```

