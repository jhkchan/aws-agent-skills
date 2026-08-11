# Baseline (no-skill) — blue-green-cname-swap

> This is the response a model produces **without** the skill
> definition. It mentions swapping but misses the
> swap-environment-cnames API call, the health-check prerequisite
> (both environments must be Ready + Green), the DNS TTL overlap
> window, and the READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

Deploy a new version to the green environment, then point your DNS
to the green environment's URL. You can use Route 53 to swap the
CNAME records.

```bash
aws elasticbeanstalk update-environment \
  --environment-name myapp-green \
  --version-label v2
```

Then update your Route 53 record to point to the green URL.
