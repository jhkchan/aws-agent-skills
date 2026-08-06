# Baseline (no-skill) response: no-lifecycle-policy

This file captures what a generic assistant produces WITHOUT the
ecr-repository-auditor skill loaded.

---

This repository doesn't have a lifecycle policy configured. Without one,
old images will accumulate over time. The scanning and tag immutability
settings look good.

You should consider adding a lifecycle policy to clean up old images and
save on storage costs.
