# Baseline (no-skill) — active-standby-with-safety-rule

> This is the response a model produces **without** the skill
> definition. It creates routing controls but misses the mandatory
> safety rule (the #1 guardrail omission), the config-vs-cluster API
> distinction, the readiness check requirement, and the
> READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

You can create routing controls using the CLI:

```bash
aws route53-recovery-control-config create-control-panel \
  --cluster-arn arn:aws:route53-recovery-control-config:...:cluster/... \
  --control-panel-name "failover"
```

Then add routing controls and toggle them as needed.
