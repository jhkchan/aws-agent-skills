# Baseline (no-skill) response: rum-application-signals-correlation-gap

This file captures what a generic assistant produces WITHOUT the
cloudwatch-rum-deployer skill loaded.

---

To enable RUM with X-Ray tracing, set `enableXRay: true` in the
SDK config:

```typescript
const awsRum = new AwsRum('checkout-web-prod', '1.0.0', 'us-east-1', {
  enableXRay: true,
  telemetries: ['errors', 'performance', 'http']
});
```

For Application Signals correlation, you may need to enable
Application Signals on the server separately. X-Ray sampling may
also need adjustment.
