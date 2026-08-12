# Baseline (no-skill) — public-app-cross-account-policy

> This is the response a model produces **without** the skill
> definition. It attempts to publish as public but does not flag
> that LICENSE is required for public sharing (API will reject),
> does not note that public apps require AWS verification
> (IsVerifiedAuthor), and omits the READY_TO_DEPLOY checklist
> format. Generated for with-skill-vs-baseline comparison.

---

Publish the app as public:

```bash
aws serverlessrepo create-application \
  --author "Jacky Chan" \
  --description "Realtime stream processor" \
  --semantic-version "1.2.0" \
  --template-body file://template.yaml
```

Make sure the README is included. Anyone can deploy it once published.
