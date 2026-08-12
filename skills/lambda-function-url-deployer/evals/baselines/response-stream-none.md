# Baseline (no-skill) — response-stream-none

> This is the response a model produces **without** the skill
> definition. It creates the function URL but misses the handler
> signature change required for RESPONSE_STREAM mode, the security
> implication of NONE auth being public internet, and the
> READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

Create the function URL:

```bash
aws lambda create-function-url-config \
  --function-name my-streaming-handler \
  --auth-type NONE \
  --invoke-mode RESPONSE_STREAM
```

Your handler just needs to return the response normally.
