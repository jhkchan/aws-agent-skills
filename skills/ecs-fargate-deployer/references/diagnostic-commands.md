# Diagnostic Commands (load on demand) — ECS Fargate Deployer

Verification command listings moved verbatim from SKILL.md. Loaded on demand.

---

## Step 10 — verification commands (moved from SKILL.md)

```bash
aws ecs describe-services --cluster <cluster> --services <service>
aws ecs describe-task-definition --task-definition <family>:<rev>
aws ecs describe-tasks --cluster <cluster> --tasks <task-id>
aws elbv2 describe-target-health --target-group-arn <arn>
aws logs describe-log-groups --log-group-name-prefix /ecs/<service>
aws application-autoscaling describe-scaling-policies --service-namespace ecs
```
