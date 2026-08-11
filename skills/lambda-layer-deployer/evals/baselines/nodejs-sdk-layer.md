# Baseline (no-skill) — nodejs-sdk-layer

> This is the response a model produces **without** the skill
> definition. It lists CLI commands but misses the compatible runtimes
> declaration, the compatible architectures, the correct zip path
> (nodejs/node_modules/), the Node.js 22+ no-SDK-bundle caveat, and
> the READY_TO_DEPLOY checklist format. Generated for with-skill-vs-
> baseline comparison.

---

To create a Node.js Lambda layer with the AWS SDK:

1. Install the SDK packages:
```bash
npm init -y
npm install @aws-sdk/client-s3 @aws-sdk/client-dynamodb @aws-sdk/lib-dynamodb
zip -r sdk-layer.zip node_modules/
```

2. Publish:
```bash
aws lambda publish-layer-version \
  --layer-name sdk-layer \
  --zip-file fileb://sdk-layer.zip
```

The SDK should be available in your functions.
