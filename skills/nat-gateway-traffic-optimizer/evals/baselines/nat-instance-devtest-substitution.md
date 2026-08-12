# Baseline (no-skill) response: nat-instance-devtest-substitution

This file captures what a generic assistant produces WITHOUT the
nat-gateway-traffic-optimizer skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, NAT Instance throughput
limitations, iptables setup, source-dest-check requirement, CONFIRM gate).

---

Your dev VPC is only using 30 GB per month through NAT but you're
paying $34/month for the NAT Gateway. For a dev environment with such
low traffic, you could replace the NAT Gateway with a NAT Instance
to save money.

A t3.micro instance would cost about $7.60/month compared to $34 for
the NAT Gateway. That's a significant saving for a dev environment.

You can set up a NAT Instance by launching an EC2 instance with NAT
rules:

```
aws ec2 run-instances --image-id ami-0al2023 --instance-type t3.micro \
  --subnet-id subnet-0public --source-dest-check false
```

Then point your route table at the instance instead of the NAT Gateway.
Just note that the NAT Instance won't have the same throughput or
reliability as a managed NAT Gateway, but for dev that should be fine.
