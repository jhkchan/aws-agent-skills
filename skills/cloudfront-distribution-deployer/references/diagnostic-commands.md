# Diagnostic Commands (load on demand) — CloudFront Distribution Deployer

Command listings moved verbatim from SKILL.md: the live-account pre-flight checks, the post-deployment verification commands, and the pre-flight safety checks.


---

## Live-account pre-flight checks (moved from SKILL.md)

**Live-account pre-flight checks (skip if doing offline architecture plan):**
1. Verify IAM permissions for `cloudfront:CreateDistribution`,
   `cloudfront:CreateOriginAccessControl`, `cloudfront:CreateCachePolicy`,
   `cloudfront:CreateOriginRequestPolicy`, `cloudfront:CreateResponseHeadersPolicy`,
   `cloudfront:CreateDistributionWithStagingConfig`, and
   `wafv2:CreateWebACL`, `wafv2:AssociateWebACL`.
2. Verify the ACM certificate exists and is ISSUED in us-east-1:
   `aws acm list-certificates --region us-east-1 --output text`
3. For S3 origins, verify the bucket exists and note its region
   (cross-region S3 origins are supported but incur cross-region data
   transfer to the CloudFront edge).
4. For ALB/EC2 custom origins, verify HTTPS is reachable on 443 and the
   origin certificate is trusted by CloudFront (public CA, not self-signed).
5. For WAFv2, verify the Web ACL scope is `CLOUDFRONT` (not `REGIONAL`).


---

## Verification commands (run after deployment) (moved from SKILL.md)

```bash
# Verify distribution is Deployed
aws cloudfront get-distribution --id <id> \
  --query 'Distribution.Status'

# Verify OAC exists
aws cloudfront get-origin-access-control --id <oac-id>

# Verify WAF is associated
aws cloudfront get-distribution-config --id <id> \
  --query 'DistributionConfig.WebACLId'

# Verify ACM cert is in us-east-1 and ISSUED
aws acm describe-certificate --certificate-arn <arn> --region us-east-1 \
  --query 'Certificate.Status'

# Verify logging bucket ACL grant
aws s3api get-object-acl --bucket prod-cf-logs --key cdn-logs/

# Test distribution
curl -I https://<distribution-domain>.cloudfront.net/
# Expect: HTTP/2 200, strict-transport-security header present
```


---

## Pre-flight safety checks (moved from SKILL.md)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`create-distribution`, `update-distribution`, `create-origin-access-control`),
  the deployer MUST emit:
  `CONFIRM: About to deploy distribution <name> in account <account>.
  Estimated monthly cost: <$X>. Distribution changes propagate globally
  (5-60 min). Proceed? (yes/no)`

- **ACM cert region check.** `aws acm describe-certificate --certificate-arn
  <arn> --region us-east-1 --query 'Certificate.Status'` MUST return
  `ISSUED`. A cert in any other region or in `PENDING_VALIDATION` fails.

- **WAF scope check.** `aws wafv2 list-web-acls --scope CLOUDFRONT --region
  us-east-1` MUST list the intended ACL. REGIONAL-scope ACLs cannot be
  associated.

- **S3 bucket policy dry-run.** Before attaching OAC, verify the bucket
  policy has the service-principal statement. Without it, all object GETs
  fail immediately on distribution deployment.

- **Cost estimate.** Emit before deployment:
  - CloudFront data transfer to origin: $0.085/GB (varies by price class)
  - CloudFront data transfer to internet: $0.02/GB (varies by region)
  - Lambda@Edge invocations: $0.60 per million + GB-second
  - CloudFront Functions: $0.10 per million
  - WAF: $5/ACL/month + $0.60 per million requests
  - Real-time logging: Kinesis cost

- **Distribution update is global.** Changes take 5-60 minutes to propagate
  to all edge locations. Verify via `get-distribution Status: Deployed`
  before declaring deployment complete.
