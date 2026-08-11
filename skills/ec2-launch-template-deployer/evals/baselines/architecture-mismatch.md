# Baseline (no-skill) — architecture-mismatch

> This is the response a model produces **without** the skill
> definition. It creates the launch template with an x86_64 AMI
> paired with a Graviton (arm64) instance type without flagging
> the architecture mismatch. The template creates successfully but
> every instance launched from it will fail to boot (pending →
> shutting-down) with no obvious cause. Generated for with-skill-
> vs-baseline comparison.

---

Here's your web server launch template:

```bash
aws ec2 create-launch-template \
  --launch-template-name web-server \
  --launch-template-data '{
    "ImageId": "ami-0x86image",
    "InstanceType": "m7g.large",
    "KeyName": "web-key",
    "SecurityGroupIds": ["sg-0web"],
    "SubnetId": "subnet-0web"
  }'
```

The m7g.large is a Graviton instance — great choice for cost
savings.
