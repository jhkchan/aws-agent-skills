# Baseline (no-skill) — missing-readme-license

> This is the response a model produces **without** the skill
> definition. It attempts to publish the app as public without
> flagging the missing LICENSE file (the SAR API will reject the
> public publish). Does not emit a PREREQUISITES_MISSING verdict.
> Generated for with-skill-vs-baseline comparison.

---

Publish the app:

```bash
aws serverlessrepo create-application \
  --author "Jacky Chan" \
  --description "Event router" \
  --semantic-version "1.0.0" \
  --readme-body file://README.md \
  --template-body file://template.yaml
```

That should make it public.
