# Error handling - Cognito Identity Pool Deployer (load on demand)

## Error handling (moved from SKILL.md)

### AccessDenied when calling GetCredentialsForIdentity
- The authenticated role trust policy is missing or incorrect. Verify
  `cognito-identity.amazonaws.com:aud` matches the pool ID and
  `cognito-identity.amazonaws.com:amr` includes "authenticated".

### Guest users get AccessDenied
- The unauthenticated role does not exist or has the wrong trust
  policy. Verify the role exists and the `amr` condition includes
  "unauthenticated".

### Role mapping rules not matching
- The JWT claim may not exist or may have a different name. Decode the
  JWT token and verify the claim name and value. For Cognito User Pool
  groups, the claim is `cognito:groups`.

### SAML federation fails
- The SAML provider metadata may be stale. Re-import the metadata XML.
  Verify the SAML `aud` condition matches the expected audience.

### Expired credentials
- AWS credentials from the identity pool expire (typically 1 hour).
  The client must call `GetCredentialsForIdentity` again with a fresh
  provider token. Ensure token refresh is implemented.

