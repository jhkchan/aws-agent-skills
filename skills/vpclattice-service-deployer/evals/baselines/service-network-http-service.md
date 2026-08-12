# Baseline (no-skill) — service-network-http-service

> This is the response a model produces **without** the skill
> definition. It creates the service but misses that the service network
> is the top-level routing plane (account-level, not VPC-level), that
> health check status determines routing eligibility (not just
> monitoring), and the READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

Create a Lattice service:

```bash
aws vpc-lattice create-service --name payments-svc
```

Add a target group and listener. Should work.
