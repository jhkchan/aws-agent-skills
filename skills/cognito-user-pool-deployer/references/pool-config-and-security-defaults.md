# Cognito User Pool Config & Security Defaults Reference

Load this reference when planning or executing any Cognito user pool
deployment. The procedures below are the canonical pool configurations,
app client patterns, and verification sequences for each pool archetype.

## Decision tree — which pool archetype

| Scenario | Use | Why |
|---|---|---|
| Consumer B2C app (mobile/web) | **Standard user pool, email login, TOTP MFA** | SRP auth + code+PKCE OAuth, no SMS cost |
| B2B / workforce | **SAML/OIDC federation pool** | IdP is the source of truth; Cognito is bridge |
| Machine-to-machine API access | **Resource server + client-credentials client** | Issued tokens carry custom scopes |
| High-trust regulated (PCI/HIPAA) | **Strict pool with TOTP+ASF ENFORCED** | SMS not accepted; ENFORCED blocks risk events |
| White-label B2B portal | **Multi-domain pool with branding per client** | One pool, many custom domains + branding |
| Legacy migration | **Migration trigger pool** | `PreTokenGeneration` + `UserMigration` Lambdas |

## Standard user pool procedure

**When to use:** consumer application with email/phone login.

**Pre-checks:**
1. Pool name unique within account+region.
2. Password policy >= 12 chars, all four classes true.
3. MfaConfiguration is one of OFF/ON/OPTIONAL.
4. DeletionProtection: ACTIVE.
5. PreventUserExistenceErrors: ENABLED.
6. AdvancedSecurityMode: ENFORCED.

**CLI structure:**
```bash
aws cognito-idp create-user-pool \
  --pool-name "prod-users" \
  --policies '{"PasswordPolicy":{"MinimumLength":16,"RequireUppercase":true,"RequireLowercase":true,"RequireNumbers":true,"RequireSymbols":true,"TemporaryPasswordValidityDays":1}}' \
  --mfa-configuration ON \
  --enabled-mfas '["TOTP"]' \
  --username-attributes '["email"]' \
  --schema '[
    {"Name":"email","AttributeDataType":"String","Required":true,"Mutable":false},
    {"Name":"custom:tenantId","AttributeDataType":"String","Mutable":false}
  ]' \
  --user-pool-add-ons 'AdvancedSecurityMode=ENFORCED' \
  --deletion-protection ACTIVE \
  --prevent-user-existence-errors ENABLED \
  --account-recovery-setting '{"RecoveryMechanisms":[{"Priority":1,"Name":"verified_email"}]}'
```

**Common failure modes:**
- "Custom attribute does not exist" — declare `custom:*` in Schema at
  pool creation. Schema is immutable after creation.
- "Invalid SMS role" — for SMS MFA, the SNS caller IAM role must exist,
  trust `cognito-idp.amazonaws.com`, and have `sns:Publish`.
- "Cannot enable TOTP" — TOTP requires `MfaConfiguration: ON` or
  `OPTIONAL` and `"TOTP"` in `EnabledMfas`.

## App client procedure (code flow + PKCE)

**When to use:** web SPA or mobile app.

**CLI structure:**
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
  --token-validity-units '{"AccessToken":"hours","IdToken":"hours","RefreshToken":"days"}' \
  --refresh-token-validity 30 \
  --enable-token-revocation \
  --prevent-user-existence-errors ENABLED
```

**Auth flow strength matrix:**

| Flow | Strength | When acceptable |
|---|---|---|
| `ALLOW_USER_SRP_AUTH` | Strong | Default for all clients — SRP never sends password |
| `ALLOW_REFRESH_TOKEN_AUTH` | Strong | Always paired with SRP for silent refresh |
| `ALLOW_USER_PASSWORD_AUTH` | Weak | Trusted server-side only; password hits the client SDK |
| `ALLOW_ADMIN_USER_PASSWORD_AUTH` | Block | Admin auth bypasses SRP — security red flag |
| `ALLOW_CUSTOM_AUTH` | Varies | Used for `client-credentials` challenge flow |

**OAuth flow strength matrix:**

| Flow | Strength | When acceptable |
|---|---|---|
| `code` (+ PKCE for SPA/mobile) | Strong | Default — token exchange happens server-side |
| `client-credentials` | Strong | M2M only — requires resource server with custom scopes |
| `implicit` | BLOCK | Token leaks via URL fragment (browser history, Referer, proxies) |

## Token validity reference

| Token | Default | Recommended | Hard ceiling |
|---|---|---|---|
| AccessToken | 1 hour | 1 hour | 1 day |
| IdToken | 1 hour | 1 hour | 1 day |
| RefreshToken | 30 days | 30-90 days | 3650 days (10 years) |

Always set `TokenValidityUnits` explicitly — Cognito defaults vary and
a bare value of `5` is hours, not minutes.

## Verification commands

```bash
# Verify pool created with expected config
aws cognito-idp describe-user-pool --user-pool-id <id> \
  --query 'UserPool.[PoolName,MfaConfiguration,UserPoolAddOns.AdvancedSecurityMode,DeletionProtection]'

# List app clients and verify auth flows
aws cognito-idp list-user-pool-clients --user-pool-id <id> \
  --query 'UserPoolClients[].[ClientName,ExplicitAuthFlows,AllowedOAuthFlows]'

# List identity providers
aws cognito-idp list-identity-providers --user-pool-id <id>

# Verify custom domain status
aws cognito-idp describe-user-pool-domain --domain auth.example.com \
  --query 'DomainDescription.Status'
```
