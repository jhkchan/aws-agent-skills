# Baseline (no-skill) response: cors-wildcard-with-credentials-missing

This file captures what a generic assistant produces WITHOUT the
cloudfront-response-headers-deployer skill loaded — the contrast that
proves the skill catches the browser-rejected CORS combination before
the operator ships a broken policy.

---

To configure CORS on your CloudFront distribution:

1. Go to CloudFront → Response Headers Policies → Create policy.
2. Name it `prod-cors-policy`.
3. Set:
   - Access-Control-Allow-Origin: `*`
   - Access-Control-Allow-Methods: GET, POST, OPTIONS
   - Access-Control-Allow-Credentials: true
4. Save and attach.

That should allow any origin to make credentialed requests to your
distribution. Let me know if you run into any issues.
