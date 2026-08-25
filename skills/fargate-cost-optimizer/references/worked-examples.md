# Fargate Cost Optimizer — worked examples (moved from SKILL.md)

Loaded on demand — content moved verbatim from SKILL.md (progressive disclosure; nothing deleted).

## NEED_MORE_INFO re-prompt template (moved from SKILL.md)

```text
TARGET: <task-definition or service>
VERDICT: NEED_MORE_INFO
REASON: Cannot optimize without CPU/memory utilization data.
MISSING:
  - Task definition ARN or name:revision
  - CloudWatch CPUUtilization and MemoryUtilization (14+ days)
  - Current capacity provider strategy (if any)
  - Monthly Fargate spend (from Cost Explorer)
```
