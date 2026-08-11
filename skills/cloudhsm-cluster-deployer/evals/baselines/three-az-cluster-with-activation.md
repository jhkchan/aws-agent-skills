# Baseline (no-skill) — three-az-cluster-with-activation

> This is the response a model produces **without** the skill
> definition. It lists CLI commands but misses that activation is
> one-time, that HA requires ≥2 AZs in the SAME cluster, that the
> CO password is not recoverable, and the READY_TO_DEPLOY checklist
> format. Generated for with-skill-vs-baseline comparison.

---

Here's how to set up a CloudHSM cluster:

```bash
aws cloudhsmv2 create-cluster \
  --hsm-type hsm1.medium \
  --subnet-ids subnet-aaa subnet-bbb subnet-ccc
```

Then create HSMs and you should be good.
