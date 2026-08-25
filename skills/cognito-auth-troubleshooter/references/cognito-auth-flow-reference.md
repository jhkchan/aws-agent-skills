# Cognito Authentication Flow Reference Guide

Supplementary reference for the Cognito Auth Troubleshooter skill.
Loaded on-demand when a diagnostic needs auth-flow semantics, token
lifecycle rules, role trust policy templates, or provider redirect URI
matrices.

## App client types

| Type | `GenerateClientSecret` | `ClientSecret` in describe | Used by | Sends secret? |
|---|---|---|---|---|
| CONFIDENTIAL | `true` (default) | Present (string) | Server-side apps, machine-to-machine | Yes — in every token exchange |
| PUBLIC | `false` | null (absent) | SPAs, mobile apps, CLI clients | No — must NOT send a secret |

The client type is set at creation time and cannot be changed. To
switch from CONFIDENTIAL to PUBLIC (or vice versa), the app client must
be deleted and recreated.

## Explicit auth flows

| Flow constant | SDK API | Use case | Added to ExplicitAuthFlows? |
|---|---|---|---|
| `ALLOW_USER_PASSWORD_AUTH` | `InitiateAuth` | Direct username/password (insecure without TLS) | Must be explicitly added |
| `ALLOW_USER_SRP_AUTH` | `InitiateAuth` + `RespondToAuthChallenge` | Secure Remote Password (recommended for direct auth) | Must be explicitly added |
| `ALLOW_ADMIN_USER_PASSWORD_AUTH` | `AdminInitiateAuth` | Server-side admin login | Must be explicitly added |
| `ALLOW_REFRESH_TOKEN_AUTH` | `InitiateAuth` | Refresh expired access/ID tokens | Must be explicitly added |
| `ALLOW_CUSTOM_AUTH` | `InitiateAuth` + `RespondToAuthChallenge` | Custom challenge flow (OTP, CAPTCHA) | Must be explicitly added |

A new app client has NO flows enabled by default. Every flow must be
explicitly added via `update-user-pool-client --explicit-auth-flows`.

## Token lifecycle

| Token | Default validity | Configurable via | Configurable unit | Used for |
|---|---|---|---|---|
| Access token | 1 hour | `AccessTokenValidity` | hours, minutes, seconds (default hours) | API authorization (Bearer) |
| ID token | 1 hour | `IdTokenValidity` | hours, minutes, seconds (default hours) | OIDC identity claims |
| Refresh token | 30 days | `RefreshTokenValidity` | days, hours, minutes, seconds (default days) | Minting new access/ID tokens |

### Token validity units

```bash
aws cognito-idp describe-user-pool-client \
  --user-pool-id <pool-id> --client-id <client-id> --output json | \
  jq '{AccessTokenValidity, IdTokenValidity, RefreshTokenValidity,
       TokenValidityUnits}'
```

The `TokenValidityUnits` object specifies the time unit for each token
type. A `RefreshTokenValidity: 30` with `TokenValidityUnits.RefreshToken:
days` is 30 days. The same value with unit `hours` is only 30 hours.

### Refresh token expiry vs revocation

| State | Cause | Recoverable with old token? |
|---|---|---|
| Expired | Time since issuance exceeds `RefreshTokenValidity` | No — user must re-authenticate |
| Revoked | `RevokeToken` API called for this token | No — permanently invalid |
| Globally signed out | `GlobalSignOut` called (any device) | No — all tokens for the user are invalid |
| Device mismatch | `DeviceConfiguration` enabled, wrong device key | No — re-authenticate on the correct device |

## Hosted UI endpoints

| Endpoint | URL pattern | Purpose |
|---|---|---|
| Authorize | `https://<domain>/oauth2/authorize` | Start OAuth/OIDC flow; validates `redirect_uri` |
| Token | `https://<domain>/oauth2/token` | Exchange code for tokens; validates `redirect_uri` matches authorize |
| UserInfo | `https://<domain>/oauth2/userInfo` | Standard OIDC UserInfo endpoint |
| Logout | `https://<domain>/logout` | End session; redirects to `LogoutURLs` entry |
| JWKS | `https://<domain>/<pool-id>/.well-known/jwks.json` | Public keys for JWT verification |

The `redirect_uri` is validated at BOTH the authorize endpoint and the
token endpoint. Both must match the `CallbackURLs` list exactly.

## Identity pool role trust policy — authenticated role

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Federated": "cognito-identity.amazonaws.com"},
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "cognito-identity.amazonaws.com:aud": "<identity-pool-id>"
      },
      "ForAnyValue:StringLike": {
        "cognito-identity.amazonaws.com:amr": "authenticated"
      }
    }
  }]
}
```

## Identity pool role trust policy — unauthenticated role

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Federated": "cognito-identity.amazonaws.com"},
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "cognito-identity.amazonaws.com:aud": "<identity-pool-id>"
      },
      "ForAnyValue:StringLike": {
        "cognito-identity.amazonaws.com:amr": "unauth"
      }
    }
  }]
}
```

The `amr` (Authentication Methods Reference) condition distinguishes
authenticated from unauthenticated access. The `aud` condition must
match the identity pool ID exactly.

## Social provider configuration matrix

| Provider | Cognito ProviderType | ProviderDetails fields | Authorized redirect URI at provider |
|---|---|---|---|
| Google | `Google` | `client_id`, `client_secret`, `authorize_scope` | `https://<user-pool-domain>/oauth2/idpresponse` |
| Facebook | `Facebook` | `client_id`, `client_secret`, `authorize_scope`, `api_version` | `https://<user-pool-domain>/oauth2/idpresponse` |
| SignInWithApple | `SignInWithApple` | `client_id`, `client_secret`, `authorize_scope`, `team_id`, `key_id`, `private_key` | `https://<user-pool-domain>/oauth2/idpresponse` |
| LoginWithAmazon | `LoginWithAmazon` | `client_id`, `client_secret`, `authorize_scope` | `https://<user-pool-domain>/oauth2/idpresponse` |

### Apple-specific notes

- The `client_secret` is a JWT signed with the `.p8` private key,
  valid for up to 6 months. Cognito regenerates it automatically using
  the `team_id`, `key_id`, and `private_key` fields.
- Apple authorization codes are valid for 10 minutes only. The token
  exchange must happen immediately after the redirect.
- Apple does not return a `refresh_token` unless the `email` scope is
  requested on the first authorization.

## SAML provider configuration

| Field | Value |
|---|---|
| `ProviderType` | `SAML` |
| `ProviderDetails.MetadataURL` | URL to the IdP's metadata XML (Cognito fetches at login time) |
| `ProviderDetails.MetadataFile` | Base64-encoded metadata XML (alternative to URL) |
| `attribute_mapping` | Maps SAML attributes to User Pool attributes (e.g., `email: "email"`) |
| IdP Entity ID / Audience | Must be the Cognito User Pool SAML endpoint: `https://<domain>/saml2/idpresponse` |

### SAML certificate validation

Cognito validates the SAML assertion signature against the signing
certificate embedded in the metadata. If the IdP rotates its signing
certificate:

1. The IdP's metadata at the `MetadataURL` is updated automatically
   (for URL-based config).
2. Cognito must re-fetch the metadata. This happens at login time, but
   caching can delay the update.
3. To force an immediate update, call `update-identity-provider` with
   the same `MetadataURL`, or switch to `MetadataFile` with the new XML.

## Lambda trigger contracts

| Trigger | Event source | Response shape | Timeout |
|---|---|---|---|
| `PreSignUp` | Sign-up | `{response: {autoConfirmUser, autoVerifyEmail, autoVerifyPhone}}` | 5s |
| `CustomMessage` | Verification / MFA / invitation | `{response: {smsMessage, emailMessage, emailSubject}}` | 5s |
| `PostConfirmation` | After user confirms | Void (no response needed) | 5s |
| `PreAuthentication` | Before authentication | Void (can deny by throwing) | 5s |
| `PostAuthentication` | After authentication | Void | 5s |
| `PreTokenGeneration` | Before token issuance | `{response: {claimsToAddOrOverride, claimsToSuppress}}` (max 100 KB) | 5s |
| `DefineAuthChallenge` | Custom auth sequence | `{response: {challengeName, issueTokens, failAuthentication}}` | 5s |
| `CreateAuthChallenge` | Custom auth challenge | `{response: {publicChallengeParameters, privateChallengeParameters, challengeMetadata}}` | 5s |
| `VerifyAuthChallenge` | Verify custom auth response | `{response: {answerCorrect}}` | 5s |
| `CustomEmailSender` | Email sending | `{response: {emailMessage, emailSubject}}` (KMS-encrypted) | 5s |
| `CustomSMSSender` | SMS sending | `{response: {smsMessage}}` (KMS-encrypted) | 5s |
| `UserMigration` | User migration at login | `{response: {userAttributes, finalUserStatus, messageAction}}` | 5s |

All triggers have a 5-second timeout. If the Lambda exceeds 5 seconds,
the auth flow fails with `UserLambdaValidationException`.

## MFA configuration reference

| Pool-level `MfaConfiguration` | Effect |
|---|---|
| `OFF` | No MFA enforced; per-user MFA settings ignored |
| `OPTIONAL` | MFA available but not required; users can opt in |
| `ON` | MFA required for ALL users; users must enrol before completing auth |

| Per-user setting | Effect |
|---|---|
| `PreferredMfaSetting: SOFTWARE_TOKEN_MFA` | TOTP is the primary MFA |
| `PreferredMfaSetting: SMS_MFA` | SMS is the primary MFA |
| No MFA setting + pool `OPTIONAL` | User is not prompted for MFA |
| No MFA setting + pool `ON` | User is prompted to enrol at next sign-in |

### TOTP enrolment sequence

1. `AssociateSoftwareToken` (returns a secret code for QR generation)
2. User scans the QR code in their authenticator app
3. `VerifySoftwareToken` (user enters the 6-digit code)
4. `SetUserMFAPreference` or `AdminSetUserMFAPreference` (enable
   `SOFTWARE_TOKEN_MFA`)

If step 3 is skipped, the TOTP is not active and MFA prompts will fail.

## Password policy defaults

| Field | Default |
|---|---|
| `MinimumLength` | 8 |
| `RequireUppercase` | true |
| `RequireLowercase` | true |
| `RequireNumbers` | true |
| `RequireSymbols` | true |
| `TemporaryPasswordValidityDays` | 7 |

Password policy changes apply immediately to new sign-ups and password
resets. Existing passwords are NOT invalidated.

## Step 3 - Auth flow: wrong or missing flow (moved from SKILL.md)

Symptom: `NotAuthorizedException` with `error: invalid_grant` or a
flow-specific error on `InitiateAuth` / `AdminInitiateAuth`.

```bash
aws cognito-idp describe-user-pool-client \
  --user-pool-id <pool-id> --client-id <client-id> --output json | \
  jq '.ExplicitAuthFlows'
```

Common flow errors:

| SDK call | Required `ExplicitAuthFlows` entry | Error if missing |
|---|---|---|
| `AdminInitiateAuth` with `AuthFlow: ADMIN_USER_PASSWORD_AUTH` | `ALLOW_ADMIN_USER_PASSWORD_AUTH` | `NotAuthorizedException: Invalid authentication flow` |
| `InitiateAuth` with `AuthFlow: USER_PASSWORD_AUTH` | `ALLOW_USER_PASSWORD_AUTH` | `NotAuthorizedException: Invalid authentication flow` |
| `InitiateAuth` with `AuthFlow: USER_SRP_AUTH` | `ALLOW_USER_SRP_AUTH` | `NotAuthorizedException: Invalid authentication flow` |
| `InitiateAuth` with `AuthFlow: REFRESH_TOKEN_AUTH` | `ALLOW_REFRESH_TOKEN_AUTH` | `NotAuthorizedException: Invalid authentication flow` |
| `InitiateAuth` with `AuthFlow: CUSTOM_AUTH` | `ALLOW_CUSTOM_AUTH` | `NotAuthorizedException: Invalid authentication flow` |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: AUTH_FLOW`. Fix: add the
required flow to `ExplicitAuthFlows` via
`update-user-pool-client --explicit-auth-flows`.


## Step 5 - Token refresh failure (moved from SKILL.md)

Symptom: `InitiateAuth` with `REFRESH_TOKEN_AUTH` returns
`NotAuthorizedException` or `InvalidGrantException`. The user's access
token expired, and the refresh token exchange fails.

```bash
aws cognito-idp describe-user-pool-client \
  --user-pool-id <pool-id> --client-id <client-id> --output json | \
  jq '{RefreshTokenValidity, TokenValidityUnits}'

aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=InitiateAuth \
  --start-time $(date -d '-1 hour' +%s) --end-time $(date +%s) \
  --output json | jq '.Events[] | select(.CloudTrailEvent | contains("REFRESH_TOKEN"))'
```

| Cause | Diagnosis | Fix |
|---|---|---|
| Refresh token expired (beyond `RefreshTokenValidity`) | Compare issuance timestamp to current time | Re-authenticate the user; consider raising `RefreshTokenValidity` (1-3650 days). |
| Global sign-out or token revocation | CloudTrail shows `GlobalSignOut` or `RevokeToken` for the user | Re-authenticate; the old refresh token is permanently invalid. |
| Wrong `ClientSecret` on a CONFIDENTIAL client during refresh | `NotAuthorizedException` on refresh specifically | Same as Step 2 — include the correct secret. |
| `RefreshTokenValidity` in the wrong unit | `TokenValidityUnits.RefreshToken` is `days` by default but may be `hours`, `minutes`, or `seconds` | Verify the unit; a value of `30` with unit `hours` is 30 hours, not 30 days. |
| Device tracking / remember-device mismatch | `DeviceConfiguration` enabled but client does not send device key | Configure device tracking or disable `DeviceOnlyRememberedOnUserPrompt`. |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: TOKEN_REFRESH` (expiry) or
`TOKEN_REVOCATION` (global sign-out / revoke).


## Deep reference: Cognito authentication layer model (moved from SKILL.md)

### Symptom -> layer decision matrix (offline classification)

```
Error string                                   → Layer
NotAuthorizedException + invalid_client         → APP_CLIENT_SECRET
NotAuthorizedException + invalid_grant          → TOKEN_REFRESH / AUTH_FLOW
redirect_mismatch / invalid_redirect_uri        → HOSTED_UI_REDIRECT
UserLambdaValidationException                   → PRE_TOKEN_GEN_LAMBDA / CUSTOM_SENDER_LAMBDA
GetCredentialsForIdentity NotAuthorizedException → IDENTITY_POOL_ROLE / IDENTITY_POOL_TRUST
Social login blank page                         → SOCIAL_PROVIDER / SOCIAL_REDIRECT
SAMLResponseDoesNotMatch                        → SAML_CERTIFICATE
InvalidPasswordException                        → PASSWORD_POLICY
MFAMethodNotFoundException                      → MFA_CONFIG
DomainAlreadyExistsException                    → DOMAIN_PREFIX
NET::ERR_CERT_COMMON_NAME_INVALID               → TLS_CERTIFICATE
```

### Token lifecycle reference

| Token | Default validity | Configurable via | Used for |
|---|---|---|---|
| Access token | 1 hour | `AccessTokenValidity` + `TokenValidityUnits.AccessToken` | API authorization (Bearer token) |
| ID token | 1 hour | `IdTokenValidity` + `TokenValidityUnits.IdToken` | User identity claims (OIDC) |
| Refresh token | 30 days | `RefreshTokenValidity` + `TokenValidityUnits.RefreshToken` | Minting new access/ID tokens without re-auth |

### Auth flow reference

| Flow | SDK API | Use case |
|---|---|---|
| `USER_PASSWORD_AUTH` | `InitiateAuth` | Direct username/password (insecure; use only over TLS) |
| `USER_SRP_AUTH` | `InitiateAuth` + `RespondToAuthChallenge` | Secure Remote Password (no password sent over wire) |
| `ADMIN_USER_PASSWORD_AUTH` | `AdminInitiateAuth` | Server-side admin login (requires `cognito-idp:AdminInitiateAuth`) |
| `REFRESH_TOKEN_AUTH` | `InitiateAuth` | Refresh expired access/ID tokens |
| `CUSTOM_AUTH` | `InitiateAuth` + `RespondToAuthChallenge` | Custom challenge (OTP, CAPTCHA, etc.) |
| `ALLOW_ADMIN_NO_SRP_AUTH` | Deprecated | Use `ADMIN_USER_PASSWORD_AUTH` instead |

### Identity pool role trust policy templates

Authenticated role:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Federated": "cognito-identity.amazonaws.com"},
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {"cognito-identity.amazonaws.com:aud": "<identity-pool-id>"},
      "ForAnyValue:StringLike": {"cognito-identity.amazonaws.com:amr": "authenticated"}
    }
  }]
}
```

Unauthenticated role:

```json
{
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
}
```

### Lambda trigger response size limits

| Trigger | Response size limit | Timeout |
|---|---|---|
| PreTokenGeneration | 100 KB total response | 5 seconds |
| PreSignUp | N/A (boolean response) | 5 seconds |
| PostConfirmation | N/A (void response) | 5 seconds |
| CustomMessage | Email subject + body | 5 seconds |
| DefineAuthChallenge | Challenge response | 5 seconds |
| CustomEmailSender / CustomSMSSender | Encrypted message | 5 seconds |

### Social provider redirect URI matrix

| Provider | Authorized redirect URI (at provider) |
|---|---|
| Google | `https://<user-pool-domain>/oauth2/idpresponse` |
| Facebook | `https://<user-pool-domain>/oauth2/idpresponse` |
| SignInWithApple | `https://<user-pool-domain>/oauth2/idpresponse` |
| LoginWithAmazon | `https://<user-pool-domain>/oauth2/idpresponse` |


