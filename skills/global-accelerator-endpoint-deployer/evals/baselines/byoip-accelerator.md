# Baseline (no-skill) — byoip-accelerator

> This is the response a model produces **without** the skill
> definition. It creates the accelerator but does not flag that BYOIP
> must be specified at creation time (not added later), does not verify
> the pool READY state, and misses the READY_TO_DEPLOY checklist format.
> Generated for with-skill-vs-baseline comparison.

---

Create the accelerator with your IP range:

```bash
aws globalaccelerator create-accelerator --name "byoip-accelerator"
```

Then add the BYOIP and endpoints.
