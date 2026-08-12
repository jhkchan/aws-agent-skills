# Baseline (no-skill) — missing-target-iam-role

> This is the response a model produces **without** the skill
> definition. It attempts to create the schedule without checking
> whether the target Lambda function exists or whether the caller
> has iam:PassRole. The create-schedule call will fail. Does not
> emit a PREREQUISITES_MISSING verdict. Generated for with-skill-
> vs-baseline comparison.

---

Create the schedule:

```bash
aws scheduler create-schedule \
  --name my-job \
  --schedule-expression "rate(5 minutes)" \
  --target '{"Arn": "arn:aws:lambda:us-east-1:123456789012:function:nonexistent-function"}' \
  --region us-east-1
```

That should work.
