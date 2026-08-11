# Baseline (no-skill) — python-powertools-layer

> This is the response a model produces **without** the skill
> definition. It lists CLI commands but misses the arm64 architecture
> declaration, the correct zip path convention (python/ at root), the
> compatible-runtimes list, the immutability of layer versions, and
> the READY_TO_DEPLOY checklist format. Generated for with-skill-vs-
> baseline comparison.

---

Here's how to create a Lambda layer:

1. Install your dependencies and zip them:
```bash
pip install aws-lambda-powertools boto3 requests
zip -r layer.zip /path/to/site-packages/
```

2. Publish the layer:
```bash
aws lambda publish-layer-version \
  --layer-name my-powertools-layer \
  --zip-file fileb://layer.zip
```

3. Attach it to your function:
```bash
aws lambda update-function-configuration \
  --function-name my-api-fn \
  --layers arn:aws:lambda:us-east-1:123456789012:layer:my-powertools-layer
```

That should work.
