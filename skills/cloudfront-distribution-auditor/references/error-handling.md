# Error Handling (load on demand) — CloudFront Distribution Auditor

Remediation moved verbatim from SKILL.md: the per-verdict remediation CLI sequences.


---

## Remediation guidance (moved from SKILL.md)

**Ordering principle:** TLS findings first (active data-in-transit exposure),
then OAC (origin bypass), then CONFIG_GAP items (defense-in-depth). This
prioritizes by immediate exploitability.

### For INSECURE_TLS — weak TLS minimum protocol (Step 2)

1. Update the distribution config with `MinimumProtocolVersion: TLSv1.2_2021`:
   ```bash
   # Fetch current config + ETag
   aws cloudfront get-distribution-config --id <id> --output json > /tmp/cf-config.json
   ETAG=$(jq -r '.ETag' /tmp/cf-config.json)
   # Edit MinimumProtocolVersion in the config to TLSv1.2_2021
   jq '.DistributionConfig.ViewerCertificate.MinimumProtocolVersion = "TLSv1.2_2021"' \
     /tmp/cf-config.json | jq '.DistributionConfig' > /tmp/cf-updated.json
   aws cloudfront update-distribution --id <id> \
     --if-match "$ETAG" --distribution-config file:///tmp/cf-updated.json
   ```
2. Verify propagation: `aws cloudfront get-distribution --id <id>` until
   `Status: Deployed`.

### For INSECURE_TLS — viewer protocol allow-all (Step 1)

1. Change `ViewerProtocolPolicy` to `redirect-to-https` (or `https-only` for
   strict environments) in the default cache behavior.
2. Use the same update-distribution flow as above.

### For INSECURE_TLS — custom origin http-only (Step 3)

1. Change `OriginProtocolPolicy` to `https-only` on the custom origin.
2. Verify the origin supports HTTPS (has a valid certificate) before the
   change — CloudFront will fail origin connections if the origin does not
   listen on 443.

### For INSECURE_TLS — S3 website endpoint origin (Step 4)

1. Switch the origin `DomainName` from `bucket.s3-website-<region>.amazonaws.com`
   to `bucket.s3.<region>.amazonaws.com` (REST endpoint).
2. Create an OAC and attach it to the origin (see NO_OAC remediation below).
3. Update the S3 bucket policy to use OAC (deny all except CloudFront OAC).
4. Remove public read access from the bucket.

### For NO_OAC — S3 origin without OAC or OAI (Step 5)

1. Create an OAC:
   ```bash
   aws cloudfront create-origin-access-control \
     --origin-access-control-config \
     '{"Name":"oac-for-<bucket>","Description":"OAC for <bucket>","SigningProtocol":"sigv4","SigningBehavior":"always"}' \
     --output json
   OAC_ID=$(jq -r '.OriginAccessControl.Id' /tmp/oac.json)
   ```
2. Attach the OAC ID to the origin in the distribution config
   (`OriginAccessControlId`).
3. Update the S3 bucket policy to allow CloudFront service principal with the
   OAC condition:
   ```json
   {"Principal": {"Service": "cloudfront.amazonaws.com"},
    "Condition": {"StringEquals":
      {"AWS:SourceArn": "arn:aws:cloudfront::<account>:distribution/<id>"}}}
   ```
4. Deploy the distribution and verify object access.

### For CONFIG_GAP — no WAF (Step 6)

1. Create or identify a Web ACL in us-east-1 with `CLOUDFRONT` scope.
2. Associate it:
   ```bash
   aws cloudfront update-distribution --id <id> --if-match "$ETAG" \
     --distribution-config file:///tmp/cf-config-with-waf.json
   ```
   where the config has `WebACLId` set to the Web ACL ARN.

### For CONFIG_GAP — logging disabled (Step 7)

1. Create or identify an S3 bucket for logs.
2. Grant ACL write permission to `awslogsdelivery`:
   ```bash
   aws s3api put-object-acl --bucket <log-bucket> --key cf-logs/ \
     --grant-write 'id="c4c1ede66af53448b93ce283fc5b7c73"' \
     --grant-read-acp 'id="c4c1ede66af53448b93ce283fc5b7c73"'
   ```
   (The canonical ID `c4c1ede66af53448b93ce283fc5b7c73` is the
   `awslogsdelivery` account.)
3. Enable logging in the distribution config (`Logging.Enabled: true`).

### For CONFIG_GAP — no geo restriction (Step 8)

1. Set `Restrictions.GeoRestriction.RestrictionType` to `whitelist` or
   `blacklist` with the appropriate country codes.

### For CONFIG_GAP — legacy OAI without OAC (Step 5)

1. Create an OAC (same as NO_OAC remediation).
2. Set `OriginAccessControlId` on the origin; clear
   `S3OriginConfig.OriginAccessIdentity`.
3. Update the bucket policy from the OAI canonical-user statement to the OAC
   service-principal statement.

### For OK

1. No remediation required for the current posture.
2. Recommend periodic re-audit after any config change.
3. For defense-in-depth, consider adding response headers (Strict-Transport-
   Security, Content-Security-Policy) via CloudFront response-headers policies.
