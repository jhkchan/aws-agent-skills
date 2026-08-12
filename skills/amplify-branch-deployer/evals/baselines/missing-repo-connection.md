# Baseline (no-skill) — missing-repo-connection

> This is the response a model produces **without** the skill
> definition. It proceeds to create the app via CLI without flagging the
> missing Git provider OAuth connection — the create-app call will fail
> or produce an app that cannot pull from the repo. Does not emit a
> PREREQUISITES_MISSING verdict. Generated for with-skill-vs-baseline
> comparison.

---

Create the app:

```bash
aws amplify create-app --name my-app \
  --repository https://github.com/org/my-repo
```

Then create the main branch and you should be good.
