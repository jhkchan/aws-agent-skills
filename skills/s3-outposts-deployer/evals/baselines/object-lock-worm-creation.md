# Baseline (no-skill) — object-lock-worm-creation

> This is the response a model produces **without** the skill
> definition. It does not know that object lock must be enabled at
> bucket creation on Outposts, may try to enable it after creation,
> and does not emit the READY_TO_DEPLOY checklist. Generated for
> with-skill-vs-baseline comparison.

---

Create the bucket:

```bash
aws s3 mb s3://worm-outpost-bucket
```

Then enable object lock in the console.
