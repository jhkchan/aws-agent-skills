# Baseline (no-skill) — arm64-graviton-layer

> This is the response a model produces **without** the skill
> definition. It lists CLI commands but misses the provided.al2023
> runtime declaration, the arm64 architecture declaration, the
> correct zip path (bin/), the glibc compatibility note for AL2023,
> and the READY_TO_DEPLOY checklist format. Generated for with-skill-
> vs-baseline comparison.

---

Here's how to create a Lambda layer with your Go binary:

1. Zip the binary:
```bash
zip -r go-utils-layer.zip layer/
```

2. Publish:
```bash
aws lambda publish-layer-version \
  --layer-name go-utils-layer \
  --zip-file fileb://go-utils-layer.zip
```

3. Attach to your function:
```bash
aws lambda update-function-configuration \
  --function-name my-go-fn \
  --layers arn:aws:lambda:us-east-1:123456789012:layer:go-utils-layer
```

That should cover it.
