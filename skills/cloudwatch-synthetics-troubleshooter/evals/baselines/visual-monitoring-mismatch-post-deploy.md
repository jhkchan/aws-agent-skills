# Baseline (no-skill) response: visual-monitoring-mismatch-post-deploy

This file captures what a generic assistant produces WITHOUT the
cloudwatch-synthetics-troubleshooter skill loaded — the contrast that
proves the skill adds structure (deterministic VERDICT, category-aware
walk, specific remediation).

---

Your CloudWatch Synthetics canary is failing because of a visual
monitoring issue. The canary detected that the payment page looks
different from the baseline screenshot. This likely means something
broke on your checkout page.

You should check if the "Pay Now" button is working correctly. The
canary found a 12.4% visual difference, which is pretty high. You
might need to fix the UI or update the canary baseline.

To fix this, try updating the canary:

```bash
aws synthetics update-canary --name checkout-ui-canary
```

Or you could increase the tolerance in the canary settings. Also check
if your checkout page is loading correctly by visiting it in a browser.
If the page looks fine, just update the baseline screenshot.
