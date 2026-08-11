# Baseline (no-skill) — missing-instance-profile

> This is the response a model produces **without** the skill
> definition. It creates the environment with SSM connection mode
> but does not flag that the instance profile (BasicEC2Role) is
> missing AmazonSSMManagedInstanceCore, which means the IDE will
> silently fail to connect. Does not emit a PREREQUISITES_MISSING
> verdict. Generated for with-skill-vs-baseline comparison.

---

```bash
aws cloud9 create-environment-ec2 \
  --name "broken-ide" \
  --instance-type t3.medium \
  --connection-type CONNECT_SSM \
  --subnet-id subnet-aaa11122 \
  --instance-profile BasicEC2Role
```

You should be good to go.
