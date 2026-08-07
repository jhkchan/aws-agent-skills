# Baseline (no-skill) response: acm-cert-wrong-region

This file captures what a generic assistant produces WITHOUT the
cloudfront-distribution-deployer skill loaded — the contrast that proves
the skill adds structure (detection of the eu-west-1 ACM cert as a hard
blocker for CloudFront, explicit PREREQUISITES_MISSING verdict, specific
guidance to re-issue the cert in us-east-1).

---

Here's a plan for your CloudFront distribution using your S3 bucket in
eu-west-1 and your ACM certificate.

Architecture:

- Origin: app-assets-eu.s3.eu-west-1.amazonaws.com
- Viewer: HTTPS redirect
- TLS: TLS 1.2
- ACM cert: arn:aws:acm:eu-west-1:111111111111:certificate/wrong-region
- WAF: CloudFront scope

Steps:

1. Create the distribution with the S3 origin.
2. Configure the ACM certificate.
3. Set up WAF.
4. Deploy.

The cert covers app.eu.example.com so that should work fine for your
custom domain. Let me know if you run into any issues during deployment.

Note: CloudFront is a global service so you can use certs from any
region.
