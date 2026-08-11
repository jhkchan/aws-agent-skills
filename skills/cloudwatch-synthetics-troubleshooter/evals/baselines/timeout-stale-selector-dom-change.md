# Baseline (no-skill) response: timeout-stale-selector-dom-change

This file captures what a generic assistant produces WITHOUT the
cloudwatch-synthetics-troubleshooter skill loaded.

---

Your canary is timing out after 60 seconds. It seems like the canary
script is taking too long to complete. The last step it logged was
waiting for a dashboard element.

You should try increasing the timeout setting:

```bash
aws synthetics update-canary --name login-flow-canary \
  --run-config TimeoutInSeconds=120
```

Also check if the target application is responding slowly. The dashboard
page might be loading slowly. If the application is slow, you'll need
to fix that separately.

If the element #welcome-banner is taking too long to appear, the page
might need performance optimization.
