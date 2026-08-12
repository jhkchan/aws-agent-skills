# Baseline (no-skill) — missing-vpc-association

> This is the response a model produces **without** the skill
> definition. It creates the service without flagging that the VPC is
> not associated with the service network (instances cannot resolve
> Lattice DNS names or reach services without association). Does not
> emit a PREREQUISITES_MISSING verdict. Generated for
> with-skill-vs-baseline comparison.

---

Sure, here's the service:

```bash
aws vpc-lattice create-service --name payments-svc
```

The VPC should be able to reach it once the service is created.
