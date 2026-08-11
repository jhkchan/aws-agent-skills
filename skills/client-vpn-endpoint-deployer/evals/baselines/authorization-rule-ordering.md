# Baseline (no-skill) — authorization-rule-ordering

> This is the response a model produces **without** the skill
> definition. It creates both authorization rules but in arbitrary
> order (broad first), shadowing the specific rule, and does not
> verify the first-match-wins evaluation order. Generated for
> with-skill-vs-baseline comparison.

---

Create the rules:

```bash
aws ec2 authorize-client-vpn-ingress \
  --target-network-cidr 0.0.0.0/0 \
  --authorize-all-groups

aws ec2 authorize-client-vpn-ingress \
  --target-network-cidr 10.0.0.0/16 \
  --access-group-id sg-data-team
```

Note: the broad rule was created first, shadowing the specific rule.
