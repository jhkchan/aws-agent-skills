# Baseline (no-skill) — same-account-same-region-dns

> This is the response a model produces **without** the skill
> definition. It lists CLI commands but misses the both-sides route
> table requirement (the accepter-side route is the #1 forgotten step),
> the DNS resolution flag requirement on BOTH sides, the security group
> cross-VPC reference being valid only for same-account+region, and the
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-baseline
> comparison.

---

Create the peering connection:

```bash
aws ec2 create-vpc-peering-connection \
  --vpc-id vpc-aaa11122 --peer-vpc-id vpc-bbb22233
```

Then add a route in the requester route table and you should be good.
