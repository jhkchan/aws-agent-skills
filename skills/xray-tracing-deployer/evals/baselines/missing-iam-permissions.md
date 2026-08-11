# Baseline (no-skill) — missing-iam-permissions

> This is the response a model produces **without** the skill definition.
> It does NOT flag the missing GetSamplingRules and GetSamplingTargets
> permissions. The model produces a deployment that will silently fail
> to apply central sampling rules.

---

Here's how to add X-Ray tracing to your Node.js Express service:

```bash
npm install aws-xray-sdk-core
```

```javascript
const awsXRay = require('aws-xray-sdk-core');
const express = require('express');
const app = express();

app.use(awsXRay.express.openSegment('search-api-prod'));
// ... routes
app.use(awsXRay.express.closeSegment());
```

Add the xray-daemon container to your ECS task definition. Your task
role already has the PutTraceSegments permission so you should be
good to go.
