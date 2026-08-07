# Eval prompt: missing-required-fields

Design a deployment plan for a CloudFront distribution. Emit the
standard VERDICT block (DISTRIBUTION_SPEC, VERDICT, ARCHITECTURE,
CHECKLIST, FINDINGS, DEPLOY_COMMANDS).

Requirements:

- Origin: S3 REST (app-assets.s3.us-east-1.amazonaws.com)
- Domain: app.example.com
- Cache policy: CachingOptimized
- Price class: PriceClass_100

The user did NOT specify:

- Viewer protocol policy (redirect-to-https vs https-only vs allow-all)
- TLS minimum protocol version
- ACM certificate ARN (required for the custom domain app.example.com)
- WAF requirements (associated or not, which rule groups)
- OAC configuration for the S3 origin
- Logging requirements
- Geo restriction
- Response headers policy

The user expects the skill to flag the missing prerequisites rather than
guessing defaults silently.
