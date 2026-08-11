# Baseline (no-skill) — missing-byoip-pool

> This is the response a model produces **without** the skill
> definition. It attempts to create the accelerator with BYOIP without
> verifying the pool is in READY state, which will fail at runtime. Does
> not emit a PREREQUISITES_MISSING verdict. Generated for with-skill-vs-
> baseline comparison.

---

Sure, here's the accelerator with BYOIP:

```bash
aws globalaccelerator create-accelerator \
  --name "byoip-accelerator" \
  --ip-addresses Cidr=198.51.100.0/24
```

Then add listener and endpoints.
