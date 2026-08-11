# Baseline (no-skill) — stale-finding-already-patched

> This is the response a model produces **without** the skill definition.
> It recommends re-patching the already-patched package instead of
> recognizing the finding is stale and will auto-close on rescan, missing
> the STALE_FINDING layer classification. Generated for
> with-skill-vs-baseline comparison.

---

You still have an open finding. Run the patch again:

```bash
aws ssm send-command --instance-ids i-789xyz \
  --document-name AWS-RunPatchBaseline
```

That should update curl and close the finding.
