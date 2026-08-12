# Baseline (no-skill) — direct-connect-networking

> This is the response a model produces **without** the skill
> definition. It attempts to apply VPC security groups to on-prem nodes
> (wrong — on-prem nodes are not in the VPC and use firewall rules
> instead), misses the kubelet heartbeat latency requirement, and does
> not emit the READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

Set up the Direct Connect and apply security groups to the nodes:

```bash
aws ec2 describe-security-groups
```

Allow the on-prem CIDR through the VPC security group.
