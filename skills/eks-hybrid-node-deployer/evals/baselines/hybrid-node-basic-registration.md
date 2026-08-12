# Baseline (no-skill) — hybrid-node-basic-registration

> This is the response a model produces **without** the skill
> definition. It creates IAM access keys for the node role (wrong —
> hybrid nodes use an activation code, not access keys), misses the
> nodeadm bootstrap flow, and does not emit the READY_TO_DEPLOY checklist
> format. Generated for with-skill-vs-baseline comparison.

---

Create an IAM access key for the hybrid node role:

```bash
aws iam create-access-key --user-name EKSHybridNodeRole
```

Then install kubelet and point it at the EKS cluster.
