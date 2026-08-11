# Baseline (no-skill) response: rum-npm-spa-with-xray

This file captures what a generic assistant produces WITHOUT the
cloudwatch-rum-deployer skill loaded.

---

You can install the RUM SDK via npm and initialize it in your
React app:

```
npm install aws-rum-web
```

```typescript
import { AwsRum } from 'aws-rum-web';

const awsRum = new AwsRum('checkout-web-prod', '1.0.0', 'us-east-1', {
  telemetries: ['errors', 'performance', 'http']
});
```

The app monitor should already have X-Ray enabled. You may need
to configure sampling on the server side separately.
