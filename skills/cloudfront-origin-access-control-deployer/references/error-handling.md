# Error Handling (load on demand) — CloudFront Origin Access Control Deployer

Error handling moved verbatim from SKILL.md: the 403/migration failure deep dives.


---

## Error handling (moved from SKILL.md)

### CloudFront returns 403 AccessDenied from S3
- The S3 bucket policy is missing or incorrect. Verify the policy
  grants `cloudfront.amazonaws.com` `s3:GetObject` with the correct
  `AWS:SourceArn` matching the distribution ARN.

### CloudFront returns 403 from KMS (SSE-KMS buckets)
- The KMS key policy does not grant `cloudfront.amazonaws.com`
  `kms:Decrypt`. Update with the same principal and condition pattern.
- Verify OAC `SigningBehavior` is `always-sign` (sigv4).

### OAC not signing requests (objects served without OAC)
- Verify the distribution origin `OriginAccessControlId` is set. If
  empty, OAC is not used.
- Verify the origin type is S3 (not Website Endpoint).

### OAI-to-OAC migration causes downtime
- The OAI was removed before the OAC was fully functional. Keep both
  active during migration, verify traffic, then remove the OAI.

### Multi-distribution: some distributions get 403
- The bucket policy `AWS:SourceArn` list is missing distribution ARNs.
  Verify ALL ARNs are listed, or use `AWS:SourceAccount` for broader
  access.
