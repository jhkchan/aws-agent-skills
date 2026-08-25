# Error Handling — signer-signing-profile-deployer

Moved verbatim from SKILL.md (progressive disclosure; load on demand). Sections keep their original headings.

---

## Error handling

### CreateCodeSigningConfig fails with ValidationException
- The `AllowedPublishingProfiles` ARN is malformed or the profile is
  on the wrong platform. Confirm ARN includes the version suffix and
  platform is `AWSLambda-SHA384-ECDSA`.

### UpdateFunctionCode fails with ResourceConflictException
- Signature verification failed. Package was not signed by a profile
  in `AllowedPublishingProfiles`, the version is revoked, or
  `Enforce` is correctly blocking an unsigned package. Re-sign and
  redeploy.

### StartSigningJob fails with AccessDeniedException
- Caller missing `signer:StartSigningJob` on the profile ARN or
  `s3:GetObject` on the source bucket.

### Signing job stuck InProgress
- Poll with `describe-signing-job`. If stuck >15 min, source may be
  inaccessible or destination bucket missing Signer write grant.

### Profile version not appearing in ARN
- Version suffix is assigned after the first successful signing job.

### Already-published function keeps running after profile revoke
- Expected. Code signing is a deploy-time gate. Revoke triggers a
  CI/CD redeploy workflow, not a runtime rollback.

