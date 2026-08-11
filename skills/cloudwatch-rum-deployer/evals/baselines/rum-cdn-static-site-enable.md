# Baseline (no-skill) response: rum-cdn-static-site-enable

This file captures what a generic assistant produces WITHOUT the
cloudwatch-rum-deployer skill loaded.

---

To enable CloudWatch RUM, you can use the AWS CLI to create an
app monitor and then add a script tag to your HTML page.

```
aws rum create-app-monitor --name checkout-web-prod --domain checkout.example.com
```

Then add the SDK to your page:

```html
<script src="https://client.rum.us-east-1.amazonaws.com/aws-rum-web.min.js"></script>
<script>
  cwr('init', { applicationId: 'checkout-web-prod', region: 'us-east-1' });
  cwr('load');
</script>
```

You should see data in the CloudWatch console after a few
minutes. Make sure the role has permission to write to RUM.
