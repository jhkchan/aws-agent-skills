# Baseline (no-skill) — cors-update-existing

> This is the response a model produces **without** the skill
> definition. It does not use update-function-url-config, instead
> suggesting the handler be modified for CORS. It misses that CORS
> must be updated at the function URL level and the READY_TO_DEPLOY
> checklist format. Generated for with-skill-vs-baseline comparison.

---

To update CORS, you should modify your Lambda handler to return
the additional Access-Control-Allow-Origin header for
https://staging.example.com.
