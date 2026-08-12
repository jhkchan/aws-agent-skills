# Baseline (no-skill) — pr-preview-ephemeral

> This is the response a model produces **without** the skill
> definition. It enables PR preview but does not set a fixed
> `pullRequestEnvironmentName` (so each PR gets its own environment —
> high build-minute cost), misses the ephemeral-URL-rotates-per-build
> caveat, and does not emit the READY_TO_DEPLOY checklist format.
> Generated for with-skill-vs-baseline comparison.

---

Enable PR preview:

```bash
aws amplify update-branch --app-id d2y0lrmp1qq2tu \
  --branch-name main \
  --enable-pull-request-preview
```

Each PR will get a preview URL automatically.
