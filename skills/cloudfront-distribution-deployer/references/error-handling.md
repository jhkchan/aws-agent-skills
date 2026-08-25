# Error Handling (load on demand) — CloudFront Distribution Deployer

Remediation moved verbatim from SKILL.md: the PREREQUISITES_MISSING remediation sequences.


---

## Remediation guidance (moved from SKILL.md)

**Ordering principle:** origin access model first (active exposure if wrong),
then TLS posture (data-in-transit), then WAF (defense-in-depth), then
optimizations (caching, headers).

### For PREREQUISITES_MISSING — ACM cert in wrong region

1. Re-issue or import the cert in us-east-1:
   `aws acm request-certificate --domain-name app.example.com --validation-method DNS --region us-east-1`
2. Wait for `ISSUED` status.
3. Update distribution config with the new ARN.

### For PREREQUISITES_MISSING — S3 website endpoint origin

1. Switch origin to REST endpoint: `bucket.s3.<region>.amazonaws.com`.
2. Create OAC and attach to the origin.
3. Update bucket policy to service-principal with `AWS:SourceArn`.
4. Remove public read access from the bucket.

### For PREREQUISITES_MISSING — Lambda@Edge in wrong region

1. Recreate the function in us-east-1.
2. Publish version: `aws lambda publish-version --function-name <name> --region us-east-1`.
3. Update distribution to reference the new function ARN with version suffix.
