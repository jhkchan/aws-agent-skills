# Baseline (no-skill) — instance-id-target-association

> This is the response a model produces **without** the skill
> definition. It lists CLI commands but does not flag that instance-ID
> targets are static (new instances will not be picked up), uses
> Unix-style cron (`0 3 * * 0`) instead of AWS cron, omits
> apply-at-creation, and skips the OPERATION_COMPLETED checklist
> format. Generated for with-skill-vs-baseline comparison.

---

Create the association:

```bash
aws ssm create-association \
  --name Custom-HardenBaseline \
  --targets "Key=InstanceIds,Values=i-aaa111bb222,i-ccc333dd444" \
  --schedule-expression "cron(0 3 * * 0)" \
  --parameters Mode=Strict \
  --region us-east-1
```

It will run at 3 AM every Sunday.
