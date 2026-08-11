# Baseline (no-skill) — missing-runtime-arch

> This is the response a model produces **without** the skill
> definition. It lists CLI commands without flagging the missing
> runtime/architecture declarations, and does NOT emit the
> PREREQUISITES_MISSING verdict. Generated for with-skill-vs-baseline
> comparison.

---

Sure, here's how to create a Lambda layer:

1. Install your libraries:
```bash
pip install some-library
npm install some-package
zip -r my-deps-layer.zip .
```

2. Publish:
```bash
aws lambda publish-layer-version \
  --layer-name my-deps-layer \
  --zip-file fileb://my-deps-layer.zip
```

3. Attach to functions:
```bash
aws lambda update-function-configuration \
  --function-name my-function \
  --layers arn:aws:lambda:us-east-1:123456789012:layer:my-deps-layer
```

Let me know if you need help!
