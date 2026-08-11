# Baseline (no-skill) — cross-account-org-sharing

> This is the response a model produces **without** the skill
> definition. It attempts cross-account sharing but misses the
> Organizations prerequisites (all-features, License Manager trusted
> service, delegated administrator registration) and the OU-based
> sharing mechanism. Does not emit a READY_TO_DEPLOY checklist.
> Generated for with-skill-vs-baseline comparison.

---

Here's the license config:

```bash
aws license-manager create-license-configuration \
  --name "dev-tools" \
  --license-counting-type Instance \
  --license-count 100
```

To share it:

```bash
aws license-manager create-license-configuration-cross-account \
  --license-configuration-arn "$ARN"
```
