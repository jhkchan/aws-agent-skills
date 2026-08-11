# Baseline (no-skill) — react-spa-static-no-backend

> This is the response a model produces **without** the skill definition.
> It misses the SPA rewrite rule (404 on refresh), the build artifacts
> directory for Vite (`dist`), the branch-scoped environment variables,
> and the READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

Create the app:

```bash
aws amplify create-app --name marketing-site
```

Push your React code to CodeCommit and Amplify will auto-detect it.
For the custom domain, add it in the console.
