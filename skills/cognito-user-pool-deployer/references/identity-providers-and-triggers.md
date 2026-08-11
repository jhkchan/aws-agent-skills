# Cognito Identity Providers, Lambda Triggers, and Domains Reference

Load this reference when planning federated identity, Lambda trigger
wiring, or hosted UI domain configuration for a Cognito user pool.

## Identity provider decision tree

| Scenario | IdP type | Why |
|---|---|---|
| Corporate Okta/Azure AD/ADFS | **SAML** | Industry-standard federation, attribute mapping |
| External OIDC provider (Auth0, Keycloak) | **OIDC** | Standards-based, well-known endpoints |
| Social login (Google/Facebook/Apple/Amazon) | **Social** | Native provider integration via Cognito |
| Multiple B2B tenants | **Multiple SAML IdPs** | One per tenant, named in `SupportedIdentityProviders` on each app client |

## SAML provider procedure

**Pre-checks:**
1. Metadata document is well-formed XML with `EntityDescriptor` root.
2. For MetadataURL: HTTPS, reachable, returns XML.
3. X509 signing certificate is present in metadata.
4. ACS URL configured in IdP matches
   `https://<domain>.auth.<region>.amazoncognito.com/saml2/idpresponse`.

**CLI structure:**
```bash
aws cognito-idp create-identity-provider \
  --user-pool-id <pool-id> \
  --provider-name "CorpOkta" \
  --provider-type SAML \
  --provider-details file://saml-provider-details.json \
  --attribute-mapping file://saml-attr-mapping.json \
  --idpIdentifiers '["corp.okta.com"]'
```

`saml-provider-details.json`:
```json
{
  "MetadataFile": "<EntityDescriptor XML contents>",
  "EncryptedResponses": "false"
}
```

`saml-attr-mapping.json` (maps SAML claim URIs to Cognito attributes):
```json
{
  "email": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
  "given_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname",
  "family_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname",
  "custom:department": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/department"
}
```

**Common failure modes:**
- "Invalid SAML metadata" — XML not well-formed, or root is not
  `EntityDescriptor`. Re-fetch from IdP.
- "Provider name already exists" — `list-identity-providers` returns
  the name; choose unique or update existing.
- "Attribute mapping not written" — claim URI mismatch. Verify in IdP
  debug logs.

## OIDC provider procedure

**Pre-checks:**
1. `OIDCIssuer` is HTTPS URL with no trailing slash.
2. `.well-known/openid-configuration` resolves and returns JSON.
3. `authorize`, `token`, `userInfo`, `jwks` endpoints present.
4. `ClientId` and `ClientSecret` from the OIDC provider configured.

**CLI structure:**
```bash
aws cognito-idp create-identity-provider \
  --user-pool-id <pool-id> \
  --provider-name "Auth0" \
  --provider-type OIDC \
  --provider-details '{
    "OIDCIssuer": "https://tenant.auth0.com",
    "ClientId": "abc123",
    "ClientSecret": "secret",
    "AuthorizeScopes": "openid email profile"
  }' \
  --attribute-mapping '{"email":"email","given_name":"given_name"}'
```

## Social provider procedure

Google, Facebook, Apple, and Amazon have native providers in Cognito.
Configure via console or `create-identity-provider` with `provider-type`
set to `Google`, `Facebook`, `Apple`, or `LoginWithAmazon`.

```bash
aws cognito-idp create-identity-provider \
  --user-pool-id <pool-id> \
  --provider-name "Google" \
  --provider-type Google \
  --provider-details '{
    "client_id": "google-client-id.apps.googleusercontent.com",
    "client_secret": "google-client-secret",
    "authorize_scopes": "profile email openid"
  }' \
  --attribute-mapping '{"email":"email","given_name":"given_name"}'
```

## Lambda trigger procedure

**Pre-checks:**
1. Every ARN in `LambdaConfig` resolves via `lambda:get-function`.
2. The pool principal (`cognito-idp.amazonaws.com`) has
   `lambda:InvokeFunction` on each function's resource-based policy.
3. Source ARN condition locks the permission to this specific pool
   (`aws:SourceArn: arn:aws:cognito-idp:<region>:<account>:userpool/<id>`).

**Grant invoke permission to the pool:**
```bash
aws lambda add-permission \
  --function-name prod-cognito-pre-signup \
  --statement-id cognito-invoke \
  --action lambda:InvokeFunction \
  --principal cognito-idp.amazonaws.com \
  --source-arn arn:aws:cognito-idp:us-east-1:111111111111:userpool/us-east-1_abc123
```

**Wire triggers in create-user-pool:**
```bash
aws cognito-idp create-user-pool \
  --pool-name prod-users \
  --lambda-config '{
    "PreSignUp": "arn:aws:lambda:us-east-1:111111111111:function:prod-cognito-pre-signup",
    "PostConfirmation": "arn:aws:lambda:us-east-1:111111111111:function:prod-cognito-post-confirmation",
    "CustomMessage": "arn:aws:lambda:us-east-1:111111111111:function:prod-cognito-custom-message",
    "PreTokenGeneration": "arn:aws:lambda:us-east-1:111111111111:function:prod-cognito-pre-token-gen"
  }' \
  --policies '...' --mfa-configuration ON ...
```

**Trigger matrix:**

| Trigger | When invoked | Common use |
|---|---|---|
| `PreSignUp` | Before user confirmed | Auto-confirm, validate signup domain |
| `PostConfirmation` | After user confirmed | Welcome email, sync to CRM |
| `CustomMessage` | Before any templated email/SMS | Localize, brand the verification email |
| `PreTokenGeneration` | Before tokens issued | Add custom claims (tenantId, role) |
| `PostAuthentication` | After user signs in | Audit log, MFA enrollment prompt |
| `DefineAuthChallenge` | Custom auth flow | MFA step-up, magic link |
| `CreateAuthChallenge` | Custom auth flow | Generate OTP, magic link |
| `VerifyAuthChallengeResponse` | Custom auth flow | Verify OTP, magic link |
| `UserMigration` | Legacy user sign-in | Migrate user from old IdP on first login |

## Domain procedure (Cognito vs custom)

**Cognito-managed domain:**
```bash
aws cognito-idp create-user-pool-domain \
  --user-pool-id <pool-id> \
  --domain "my-app-auth"
# Result: my-app-auth.auth.us-east-1.amazoncognito.com
```

**Custom domain (requires ACM cert in us-east-1):**
```bash
aws cognito-idp create-user-pool-domain \
  --user-pool-id <pool-id> \
  --domain "auth.example.com" \
  --custom-domain-config '{"CertificateArn":"arn:aws:acm:us-east-1:111111111111:certificate/abc-123"}'

# CloudFront alias DNS record is returned — point your DNS at it
aws cognito-idp describe-user-pool-domain --domain auth.example.com \
  --query 'DomainDescription.CloudFrontDistribution'
```

**Managed Login Branding (2024-2026):**
```bash
aws cognito-idp create-managed-login-branding \
  --user-pool-id <pool-id> \
  --client-id <client-id> \
  --assets '[{"Bytes":"<base64-logo>","Category":"BANNER_LOGO","ColorMode":"LIGHT","Extension":"PNG"}]' \
  --settings '{"brandingBackgroundColor":"#FFFFFF","brandingPrimaryColor":"#1a73e8"}'
```

Replaces the legacy `UISettings` CSS customization which is being
deprecated for managed branding.

## Pre-flight verification commands

```bash
# SAML metadata reachable?
curl -sI https://corp.okta.com/app/abc123/sso/saml | head -1

# OIDC discovery resolves?
curl -s https://tenant.auth0.com/.well-known/openid-configuration | jq '.issuer'

# ACM cert in us-east-1 and ISSUED?
aws acm describe-certificate --certificate-arn <arn> --region us-east-1 \
  --query 'Certificate.[Status,SubjectAlternatives]'

# Lambda function exists and pool can invoke?
aws lambda get-policy --function-name prod-cognito-pre-signup \
  --query 'Policy' --output text | jq '.Statement[] | select(.Principal.Service=="cognito-idp.amazonaws.com")'

# SNS caller role exists?
aws iam get-role --role-name CognitoSmsCaller --query 'Role.Arn'
```
