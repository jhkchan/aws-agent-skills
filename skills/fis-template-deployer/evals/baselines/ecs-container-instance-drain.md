# Baseline (no-skill) — ecs-container-instance-drain

> This is the response a model produces **without** the skill
> definition. It references the ECS drain action but misses the
> tag-based target scoping on the ECS cluster, the IAM role
> scoping to ecs:UpdateContainerInstancesState, the stop condition
> safety net, and the READY_TO_DEPLOY checklist. Generated for
> with-skill-vs-baseline comparison.

---

For draining an ECS container instance:

```bash
aws fis create-experiment-template \
  --description "ECS drain test" \
  --role-arn arn:aws:iam::123456789012:role/FISExperimentRole \
  --actions file://actions.json
```

Target your ECS cluster and use the drain action.
