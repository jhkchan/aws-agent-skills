# Worked Examples (load on demand) — Cognito User Pool Deployer

Common pool pattern CLI boilerplate — production pool, OAuth code+PKCE client, client-credentials, SAML IdP, custom domain + managed branding, Lambda triggers, groups — moved verbatim from SKILL.md.


---

## Common pool patterns (boilerplate) (moved from SKILL.md)

### Production user pool — TOTP MFA, email login

```bash
aws cognito-idp create-user-pool \
  --pool-name "prod-users" \
  --policies '{
    "PasswordPolicy": {
      "MinimumLength": 16,
      "RequireUppercase": true,
      "RequireLowercase": true,
      "RequireNumbers": true,
      "RequireSymbols": true,
      "TemporaryPasswordValidityDays": 1
    }
  }' \
  --mfa-configuration ON \
  --enabled-mfas "[\"TOTP\"]" \
  --username-attributes '["email"]' \
  --schema '[
    {"Name":"email","AttributeDataType":"String","Required":true,"Mutable":false},
    {"Name":"given_name","AttributeDataType":"String","Required":true,"Mutable":true},
    {"Name":"family_name","AttributeDataType":"String","Required":true,"Mutable":true},
    {"Name":"custom:tenantId","AttributeDataType":"String","Required":false,"Mutable":false}
  ]' \
  --user-pool-add-ons 'AdvancedSecurityMode=ENFORCED' \
  --account-recovery-setting '{
    "RecoveryMechanisms": [
      {"Priority":1,"Name":"verified_email"}
    ]
  }' \
  --deletion-protection ACTIVE \
  --prevent-user-existence-errors ENABLED
```

### App client — OAuth code flow with PKCE, web SPA

```bash
aws cognito-idp create-user-pool-client \
  --user-pool-id <pool-id> \
  --client-name "prod-web-spa" \
  --generate-client-secret \
  --explicit-auth-flows ALLOW_USER_SRP_AUTH ALLOW_REFRESH_TOKEN_AUTH \
  --allowed-o-auth-flows code \
  --allowed-o-auth-scopes openid email profile \
  --callback-urls '["https://app.example.com/callback"]' \
  --logout-urls '["https://app.example.com/logout"]' \
  --supported-identity-providers COGNITO \
  --access-token-validity 1 \
  --id-token-validity 1 \
  --token-validity-units '{
    "AccessToken":"hours","IdToken":"hours","RefreshToken":"days"
  }' \
  --refresh-token-validity 30 \
  --enable-token-revocation \
  --prevent-user-existence-errors ENABLED
```

### App client — machine-to-machine (client-credentials)

```bash
aws cognito-idp create-resource-server \
  --user-pool-id <pool-id> \
  --identifier "https://api.example.com" \
  --name "products-api" \
  --scopes '[{"ScopeName":"products.read","ScopeDescription":"Read products"},{"ScopeName":"products.write","ScopeDescription":"Write products"}]'

aws cognito-idp create-user-pool-client \
  --user-pool-id <pool-id> \
  --client-name "m2m-orders-service" \
  --generate-client-secret \
  --explicit-auth-flows ALLOW_CUSTOM_AUTH ALLOW_REFRESH_TOKEN_AUTH \
  --allowed-o-auth-flows client-credentials \
  --allowed-o-auth-scopes "https://api.example.com/products.read" \
  --access-token-validity 1 \
  --token-validity-units '{"AccessToken":"hours"}'
```

### SAML identity provider federation

```bash
aws cognito-idp create-identity-provider \
  --user-pool-id <pool-id> \
  --provider-name "CorpOkta" \
  --provider-type SAML \
  --provider-details '{
    "MetadataFile": "<saml metadata XML>",
    "EncryptedResponses": "false"
  }' \
  --attribute-mapping '{
    "email":"http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
    "given_name":"http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname"
  }'
```

### Custom domain (hosted UI branding)

```bash
aws cognito-idp create-user-pool-domain \
  --user-pool-id <pool-id> \
  --domain "auth.example.com" \
  --custom-domain-config '{
    "CertificateArn": "arn:aws:acm:us-east-1:111111111111:certificate/abc-123"
  }'

# Managed branding (2024-2026):
aws cognito-idp create-managed-login-branding \
  --user-pool-id <pool-id> \
  --client-id <client-id> \
  --assets '[{"Bytes":"<base64-logo>","Category":"BANNER_LOGO","ColorMode":"LIGHT","Extension":"PNG"}]' \
  --settings '{"brandingBackgroundColor":"#FFFFFF","brandingPrimaryColor":"#1a73e8"}'
```

### Lambda triggers (pre-signup, post-confirmation)

```bash
# Resource-based policy so the pool can invoke the function
aws lambda add-permission \
  --function-name prod-cognito-pre-signup \
  --statement-id cognito-invoke \
  --action lambda:InvokeFunction \
  --principal cognito-idp.amazonaws.com \
  --source-arn arn:aws:cognito-idp:us-east-1:111111111111:userpool/<pool-id>

aws cognito-idp create-user-pool \
  --pool-name "prod-users" \
  --lambda-config '{
    "PreSignUp": "arn:aws:lambda:us-east-1:111111111111:function:prod-cognito-pre-signup",
    "PostConfirmation": "arn:aws:lambda:us-east-1:111111111111:function:prod-cognito-post-confirmation",
    "CustomMessage": "arn:aws:lambda:us-east-1:111111111111:function:prod-cognito-custom-message",
    "PreTokenGeneration": "arn:aws:lambda:us-east-1:111111111111:function:prod-cognito-pre-token-gen"
  }' \
  --policies '...' --mfa-configuration ON ...
```

### User pool groups (RBAC)

```bash
aws cognito-idp create-group \
  --user-pool-id <pool-id> \
  --group-name "admins" \
  --description "Administrative users" \
  --role-arn "arn:aws:iam::111111111111:role/CognitoAdminRole" \
  --precedence 1

aws cognito-idp create-group \
  --user-pool-id <pool-id> \
  --group-name "editors" \
  --description "Content editors" \
  --precedence 2
```
