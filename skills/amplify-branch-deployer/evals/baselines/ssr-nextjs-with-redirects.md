# Baseline (no-skill) — ssr-nextjs-with-redirects

> This is the response a model produces **without** the skill
> definition. It configures redirects using status 301 instead of 200
> (breaks SPA client-side routing), misses the per-branch Lambda cost
> implication for SSR (8 branches = 8 Lambda function sets), omits
> security headers, and does not emit the READY_TO_DEPLOY checklist
> format. Generated for with-skill-vs-baseline comparison.

---

Set up the app with redirects:

```bash
aws amplify create-app --name my-next-app \
  --repository https://github.com/org/my-next-app

# Redirect rules
# /<*> → /index.html (301)
# /api → /api (300)
```

Add your build commands and deploy.
