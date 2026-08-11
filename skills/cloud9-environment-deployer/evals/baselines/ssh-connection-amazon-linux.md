# Baseline (no-skill) — ssh-connection-amazon-linux

> This is the response a model produces **without** the skill
> definition. It creates the environment but does not flag the
> security group port 22 requirement, the key pair necessity, or
> the auto-hibernation setting. Does not emit a READY_TO_DEPLOY
> checklist. Generated for with-skill-vs-baseline comparison.

---

```bash
aws cloud9 create-environment-ec2 \
  --name "legacy-ide" \
  --instance-type t3.large
```

You might need a security group and key pair for SSH.
