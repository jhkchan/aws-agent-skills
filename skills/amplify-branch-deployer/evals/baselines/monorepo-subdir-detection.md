# Baseline (no-skill) — monorepo-subdir-detection

> This is the response a model produces **without** the skill
> definition. It creates the app without setting `appRoot` (Amplify
> builds from the repo root, missing `packages/web-app/amplify.yml`),
> does not flag the monorepo detection requirement, and does not emit
> the READY_TO_DEPLOY checklist format. Generated for with-skill-vs-
> baseline comparison.

---

Create the app:

```bash
aws amplify create-app --name my-web-app \
  --repository https://github.com/org/my-monorepo
```

Amplify will detect the app in the repo automatically.
