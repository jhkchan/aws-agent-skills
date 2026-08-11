# Baseline (no-skill) — missing-git-provider-and-amplify-yml

> This is the response a model produces **without** the skill definition.
> It guesses at a provisioning path without asking for the Git provider,
> repo URL, framework version, or rendering mode, missing the
> PREREQUISITES_MISSING gate. Generated for with-skill-vs-baseline
> comparison.

---

Sure, here's how to deploy:

```bash
aws amplify create-app --name new-app
```

Then connect your repo and push. Amplify will figure out the framework.
