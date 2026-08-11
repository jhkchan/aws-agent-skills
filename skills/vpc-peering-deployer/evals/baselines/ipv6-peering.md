# Baseline (no-skill) — ipv6-peering

> This is the response a model produces **without** the skill
> definition. It creates the peering but misses that IPv4 and IPv6
> routes must be added independently (the --destination-ipv6-cidr-block
> parameter), the both-sides route requirement for both protocols, and
> the READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

Create the peering:

```bash
aws ec2 create-vpc-peering-connection \
  --vpc-id vpc-app-v6 --peer-vpc-id vpc-data-v6
```

Then add routes for IPv4. IPv6 should work automatically.
