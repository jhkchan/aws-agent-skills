# Baseline (no-skill) response: s3-oac-full-security

This file captures what a generic assistant produces WITHOUT the
cloudfront-distribution-deployer skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, enumerated CHECKLIST,
specific DEPLOY_COMMANDS, expert knowledge of OAC vs OAI, ACM us-east-1
constraint, WAF scope, and security headers policy).

---

Here's a plan to set up CloudFront for your S3 bucket. I'll create a
distribution pointing at prod-app-assets.s3.us-east-1.amazonaws.com.

The distribution will:

- Use your S3 bucket as the origin
- Redirect HTTP to HTTPS for viewers
- Use your ACM certificate
- Have a WAF attached for security
- Cache static assets aggressively
- Restrict access to a few countries
- Send logs to your S3 logs bucket

Steps:

1. Create the CloudFront distribution pointing at the S3 bucket.
2. Attach your ACM cert.
3. Set up a WAF Web ACL.
4. Configure logging to S3.
5. Deploy.

You may also want to set up bucket policies to keep the bucket private.
Some people use OAI for this — look into that.

Commands:

```
aws cloudfront create-distribution ...
aws wafv2 create-web-acl ...
```

This should give you a working CDN. Let me know if you need help with
any of the steps.
