# Baseline (no-skill) response: lambda-at-edge-viewer-request-runtime-error

---

Your CloudFront distribution is returning 502 errors intermittently.
This could be from the origin or from CloudFront itself. Try:

1. Check the ALB origin health.
2. Look at the CloudFront metrics in the console.
3. Try reproducing the issue with curl.
4. Check if there are any Lambda@Edge functions attached, and review
   their logs.

If the 5xx errors started recently, consider rolling back any recent
changes to the distribution or attached functions.
