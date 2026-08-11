# Baseline (no-skill) — nextjs-ssr-gen2-backend

> This is the response a model produces **without** the skill definition.
> It lists CLI commands but misses the Gen 2 pipeline-deploy build phase,
> the SSR-vs-SSG rendering-mode directive, the Secrets Manager integration
> for Stripe, the branch-based backend environments, the ACM us-east-1
> requirement, and the READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

Here's how to create an Amplify app:

```bash
aws amplify create-app --name prod-web
aws amplify create-branch --app-id dXXXX --branch-name main
```

Connect your GitHub repo in the console. For the backend, run:

```bash
amplify init
amplify add auth
amplify add api
amplify push
```

That should deploy your app.
