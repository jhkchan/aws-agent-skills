# Baseline (no-skill) — gen2-backend-ampx-pipeline-deploy

> This is the response a model produces **without** the skill definition.
> It suggests `amplify push` (Gen 1 sandbox mutation model) instead of
> the Gen 2 `npx ampx pipeline-deploy`, misses the CDK bootstrap
> prerequisite, and does not emit the READY_TO_DEPLOY checklist format.
> Generated for with-skill-vs-baseline comparison.

---

For the backend:

```bash
amplify init
amplify add api
amplify push
```

Then connect your GitLab repo to Amplify and deploy.
