# Baseline (no-skill) — inter-region-peering

> This is the response a model produces **without** the skill
> definition. It creates the peering but misses the --peer-region
> parameter requirement for inter-region peering, the cross-region data
> transfer cost implications, the accepter being in a different region,
> and the READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

Create the peering connection between the regions:

```bash
aws ec2 create-vpc-peering-connection \
  --vpc-id vpc-useast111 --peer-vpc-id vpc-uswest222
```

Then add routes on both sides.
