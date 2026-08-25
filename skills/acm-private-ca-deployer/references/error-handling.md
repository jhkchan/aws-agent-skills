# Error Handling — ACM Private CA Deployer

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Error handling

### CA stuck in PENDING_CERTIFICATE
- The CA has not received its CA certificate. For root, issue a self-
  signed cert and import. For subordinate, request from parent and
  import. Check with `describe-certificate-authority`.

### Subordinate CA cannot be signed by parent
- The parent CA lacks `create-permission`. Use `create-permission` on
  the parent CA to grant `IssueCertificate` and `GetCertificate`.

### CRL not publishing to S3
- The bucket policy does not grant `acm-pca.amazonaws.com`
  `s3:PutObject`. Verify with `get-bucket-policy` and add the policy.

### ACM cannot request private certificates
- The PCA lacks `create-permission` for `acm.amazonaws.com`. Grant
  `IssueCertificate`, `GetCertificate`, `ListPermissions`.

### CA deletion did not take effect immediately
- CA deletion has a mandatory 7-30 day waiting period. This is by
  design, not an error. Use `restore-certificate-authority` to undo.
