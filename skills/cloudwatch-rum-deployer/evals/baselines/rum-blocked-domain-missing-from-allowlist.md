# Baseline (no-skill) response: rum-blocked-domain-missing-from-allowlist

This file captures what a generic assistant produces WITHOUT the
cloudwatch-rum-deployer skill loaded.

---

To deploy RUM on the beta subdomain, you can add the script tag
to your HTML page:

```html
<script src="https://client.rum.us-east-1.amazonaws.com/aws-rum-web.min.js"></script>
<script>
  cwr('init', { applicationId: 'checkout-web-prod', region: 'us-east-1' });
  cwr('load');
</script>
```

The SDK should send events to the existing app monitor. If you
don't see data in the console, double-check the role permissions.
