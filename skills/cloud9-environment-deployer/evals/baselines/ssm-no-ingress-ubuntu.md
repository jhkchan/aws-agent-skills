# Baseline (no-skill) — ssm-no-ingress-ubuntu

> This is the response a model produces **without** the skill
> definition. It creates the environment but misses the
> AmazonSSMManagedInstanceCore requirement in the instance profile
> for SSM connection, the auto-hibernation cost optimization, and
> the no-ingress security posture benefit. Does not emit a
> READY_TO_DEPLOY checklist. Generated for with-skill-vs-baseline
> comparison.

---

```bash
aws cloud9 create-environment-ec2 \
  --name "dev-team-ide" \
  --instance-type t3.medium
```

That should create your Cloud9 environment.
