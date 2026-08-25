# Error handling - Cognito Auth Troubleshooter (load on demand)

## Remediation guidance (moved from SKILL.md)

### For APP_CLIENT_SECRET

```bash
# Recreate the client as PUBLIC (no secret) — requires deleting and recreating
aws cognito-idp delete-user-pool-client \
  --user-pool-id <pool-id> --client-id <client-id> --profile <p>

aws cognito-idp create-user-pool-client \
  --user-pool-id <pool-id> \
  --client-name <name> \
  --no-generate-secret \
  --explicit-auth-flows ALLOW_USER_SRP_AUTH ALLOW_REFRESH_TOKEN_AUTH \
  --callback-urls "https://app.example.com/callback" \
  --profile <p>
```

### For AUTH_FLOW

```bash
aws cognito-idp update-user-pool-client \
  --user-pool-id <pool-id> --client-id <client-id> \
  --explicit-auth-flows ALLOW_USER_PASSWORD_AUTH ALLOW_USER_SRP_AUTH ALLOW_REFRESH_TOKEN_AUTH \
  --profile <p>
```

### For HOSTED_UI_REDIRECT

```bash
aws cognito-idp update-user-pool-client \
  --user-pool-id <pool-id> --client-id <client-id> \
  --callback-urls "https://app.example.com/auth/callback" "https://app.example.com/callback" \
  --profile <p>
```

### For TOKEN_REFRESH

- If expired: re-authenticate the user. Consider raising
  `RefreshTokenValidity` (check `TokenValidityUnits`).
- If revoked: re-authenticate; old refresh tokens are permanently invalid.

```bash
aws cognito-idp update-user-pool-client \
  --user-pool-id <pool-id> --client-id <client-id> \
  --refresh-token-validity 90 \
  --token-validity-units '{"RefreshToken":"days","AccessToken":"hours","IdToken":"hours"}' \
  --profile <p>
```

### For PRE_TOKEN_GEN_LAMBDA / CUSTOM_SENDER_LAMBDA

Fix the Lambda code:
- Add defensive null checks for missing attributes.
- Ensure the response shape matches the Cognito trigger contract.
- Increase the Lambda timeout (Cognito triggers have a 5-second limit).
- Verify IAM permissions for any downstream calls (DynamoDB, SES, SNS, KMS).

### For IDENTITY_POOL_TRUST

```bash
aws iam update-assume-role-policy \
  --role-name <role-name> \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Federated": "cognito-identity.amazonaws.com"},
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {"cognito-identity.amazonaws.com:aud": "<identity-pool-id>"},
        "ForAnyValue:StringLike": {"cognito-identity.amazonaws.com:amr": "unauth"}
      }
    }]
  }' --profile <p>
```

### For SOCIAL_PROVIDER

- Update the provider's authorized redirect URI to
  `https://<user-pool-domain>/oauth2/idpresponse`.
- Update Cognito provider credentials (`ProviderDetails.client_id` /
  `client_secret`).
- Fix the attribute mapping.

### For SAML_PROVIDER / SAML_CERTIFICATE

```bash
aws cognito-idp update-identity-provider \
  --user-pool-id <pool-id> \
  --provider-name <saml-name> \
  --provider-details MetadataURL=<new-metadata-url> \
  --profile <p>
```

### For MFA_CONFIG

```bash
# Set pool-level MFA to OPTIONAL
aws cognito-idp update-user-pool \
  --user-pool-id <pool-id> \
  --mfa-configuration OPTIONAL \
  --profile <p>

# Reset a user's MFA
aws cognito-idp admin-set-user-mfa-preference \
  --user-pool-id <pool-id> --username <username> \
  --software-token-mfa-settings Enabled=false,PreferredMfa=false \
  --sms-mfa-settings Enabled=false,PreferredMfa=false \
  --profile <p>
```

### For PASSWORD_POLICY

```bash
aws cognito-idp update-user-pool \
  --user-pool-id <pool-id> \
  --policies '{
    "PasswordPolicy": {
      "MinimumLength": 12,
      "RequireUppercase": true,
      "RequireLowercase": true,
      "RequireNumbers": true,
      "RequireSymbols": true,
      "TemporaryPasswordValidityDays": 7
    }
  }' --profile <p>
```

### For DOMAIN_PREFIX

- Choose a different prefix (globally unique within region).
- Or use a custom domain (ACM certificate in us-east-1 + CloudFront).

### For TLS_CERTIFICATE

- Request an ACM certificate in us-east-1 for the custom auth domain.
- Add DNS validation CNAME records.
- Wait for `Status: ISSUED`.
- Associate the certificate with the Cognito user pool custom domain.


