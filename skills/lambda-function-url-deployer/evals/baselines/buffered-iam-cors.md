# Baseline (no-skill) — buffered-iam-cors

> This is the response a model produces **without** the skill
> definition. It creates the function URL but misses the CORS
> configuration at the function URL level (configures it only in
> the handler), the resource-based policy for IAM auth callers, the
> 15-second timeout cap warning, and the READY_TO_DEPLOY checklist
> format. Generated for with-skill-vs-baseline comparison.

---

Create the function URL:

```bash
aws lambda create-function-url-config \
  --function-name my-api-handler \
  --auth-type AWS_IAM \
  --invoke-mode BUFFERED
```

Then make sure your handler returns the right CORS headers.
