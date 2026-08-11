# Baseline (no-skill) — cross-account-same-region

> This is the response a model produces **without** the skill
> definition. It creates the peering but misses the cross-account
> acceptance step (accepter account must call accept), the CIDR-based SG
> rule requirement (SG cross-references not supported cross-account),
> the both-sides route table requirement, and the READY_TO_DEPLOY
> checklist format. Generated for with-skill-vs-baseline comparison.

---

Create the peering:

```bash
aws ec2 create-vpc-peering-connection \
  --vpc-id vpc-prod111 --peer-vpc-id vpc-dev222 --peer-owner-id 999999999999
```

Then add routes and security group rules.
