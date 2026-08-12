# Baseline (no-skill) — production-branch-with-custom-domain

> This is the response a model produces **without** the skill
> definition. It creates the app and branch but uses `buildspec.yml`
> (Amplify IGNORES this — the build spec must be `amplify.yml`), misses
> the SPA rewrite requirement (status 200, not 301), does not wire the
> Route 53 CNAME verification, omits security headers, and does not emit
> the READY_TO_DEPLOY checklist format. Generated for with-skill-vs-
> baseline comparison.

---

Create the app and branch:

```bash
aws amplify create-app --name my-web-app \
  --repository https://github.com/org/my-web-app

aws amplify create-branch --app-id d2y0lrmp1qq2tu \
  --branch-name main
```

Add a `buildspec.yml` at the repo root with your build commands, then
map the custom domain in the console.
