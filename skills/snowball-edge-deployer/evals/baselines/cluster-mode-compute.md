# Baseline (no-skill) — cluster-mode-compute

> This is the response a model produces **without** the skill
> definition. It creates individual jobs for each device but misses
> the cluster formation step (unlock sequence, cluster quorum), does
> not explain that EKS Anywhere requires min 5 nodes, and omits the
> READY_TO_DEPLOY checklist. Generated for with-skill-vs-baseline
> comparison.

---

Create 5 Snowball jobs:

```bash
for i in $(seq 1 5); do
  aws snowball create-job \
    --job-type LOCAL_USE \
    --snowball-type EDGE_COMPUTE_OPTIMIZED \
    --address-id addr-cluster01 \
    --description "Cluster node $i"
done
```

Then set up EKS Anywhere on the devices when they arrive.
