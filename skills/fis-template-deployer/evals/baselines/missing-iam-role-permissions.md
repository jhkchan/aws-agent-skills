# Baseline (no-skill) — missing-iam-role-permissions

> This is the response a model produces **without** the skill
> definition. It creates the experiment template without flagging
> that the IAM role lacks ec2:StopInstances, which will cause the
> experiment to fail at start with an opaque permission error. Does
> not emit a PREREQUISITES_MISSING verdict. Generated for with-
> skill-vs-baseline comparison.

---

Sure, here's the template:

```bash
aws fis create-experiment-template \
  --description "Stop instance test" \
  --role-arn arn:aws:iam::123456789012:role/FISExperimentRole \
  --actions file://actions.json \
  --targets file://targets.json
```

Then start it with `aws fis start-experiment`.
