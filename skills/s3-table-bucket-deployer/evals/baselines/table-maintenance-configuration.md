# Baseline (no-skill) — table-maintenance-configuration

> This is the response a model produces **without** the skill
> definition. It creates the table but has no concept of built-in
> maintenance configuration (compaction, snapshot management,
> unreferenced file cleanup), may suggest setting up a separate
> compaction job (unnecessary for S3 Tables), and does not emit the
> READY_TO_DEPLOY checklist. Generated for with-skill-vs-baseline
> comparison.

---

Create the table, then set up a Glue job to compact the files:

```bash
aws s3api create-bucket --bucket ops-tables --region us-east-1
```

You'll need to write your own compaction job and schedule it.
