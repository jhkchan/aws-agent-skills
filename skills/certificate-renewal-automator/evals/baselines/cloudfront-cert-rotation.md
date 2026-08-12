# Baseline (no-skill) response: cloudfront-cert-rotation

This file captures what a generic assistant produces WITHOUT the
certificate-renewal-automator skill loaded.

---

For CloudFront certificates, ACM handles the renewal automatically if
the cert is DNS-validated and in us-east-1. Since this one is in
us-east-1, you should be fine.

If you need to rotate manually, you can update the distribution with
`aws cloudfront update-distribution`. You'll need the distribution ID.

The cert renewal should happen automatically, so you probably don't
need to do anything.
