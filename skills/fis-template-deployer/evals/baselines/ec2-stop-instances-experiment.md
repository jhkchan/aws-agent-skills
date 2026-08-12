# Baseline (no-skill) — ec2-stop-instances-experiment

> This is the response a model produces **without** the skill
> definition. It emits the create-template CLI command but misses
> the tag-based target scoping rationale (safest mechanism), the
> CloudWatch alarm stop condition auto-abort safety net, the IAM
> role permission scoping via Condition on resource tags, and the
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-
> baseline comparison.

---

Here's the FIS template command:

```bash
aws fis create-experiment-template \
  --description "Stop an EC2 instance" \
  --role-arn arn:aws:iam::123456789012:role/FISExperimentRole \
  --actions file://actions.json \
  --targets file://targets.json \
  --stop-conditions file://stop.json
```

Make sure your role has EC2 permissions and you should be good.
