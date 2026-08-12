# Baseline (no-skill) — missing-function-exists

> This is the response a model produces **without** the skill
> definition. It attempts to create the function URL without
> verifying the function exists first. Does not emit a
> PREREQUISITES_MISSING verdict. Generated for
> with-skill-vs-baseline comparison.

---

Sure, here's the command:

```bash
aws lambda create-function-url-config \
  --function-name nonexistent-function \
  --auth-type AWS_IAM \
  --invoke-mode BUFFERED
```
