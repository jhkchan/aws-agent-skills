# Baseline (no-skill) response: auth-failure-secret-rotation

This file captures what a generic assistant produces WITHOUT the
cloudwatch-synthetics-troubleshooter skill loaded.

---

Your canary is getting a 401 Unauthorized error. This means the
authentication is failing. The error says "invalid_client" which means
your OAuth credentials are wrong.

Try checking your Secrets Manager secret. It looks like it was rotated
recently. You should verify that the canary is using the correct
secret value.

To fix this, update the canary's secret or check the OAuth credentials:

```bash
aws secretsmanager get-secret-value --secret-id prod/oauth-client-secret
```

Make sure the secret value matches what your OAuth server expects. You
might also need to check if the OAuth server itself is having issues.
