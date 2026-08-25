# Cognito Troubleshooting Commands Reference

Supplementary reference for the Cognito Auth Troubleshooter skill.
Loaded on-demand when a diagnostic needs the exact CLI commands for
probing Cognito configuration, trigger Lambda logs, identity pool
roles, and provider metadata.

## User Pool and App Client inspection

### Describe User Pool (pool-level config)

```bash
aws cognito-idp describe-user-pool \
  --user-pool-id <pool-id> --output json | \
  jq '{UserPool: {Id, Name, MfaConfiguration, Policies,
    LambdaConfig, Domain, AccountRecoverySetting,
    SchemaAttributes, AutoVerifiedAttributes}}'
```

### Describe App Client (client-level config)

```bash
aws cognito-idp describe-user-pool-client \
  --user-pool-id <pool-id> --client-id <client-id> --output json | \
  jq '{ClientId, ClientName, ClientSecret: (.ClientSecret != null),
    ExplicitAuthFlows, AllowedOAuthFlows, AllowedOAuthScopes,
    CallbackURLs, LogoutURLs, SupportedIdentityProviders,
    RefreshTokenValidity, AccessTokenValidity, IdTokenValidity,
    TokenValidityUnits, PreventUserExistenceErrors}'
```

Note: `ClientSecret` is redacted to a boolean to avoid leaking the
secret in logs. Use `jq '.ClientSecret'` to see the actual value when
needed.

### List all App Clients for a Pool

```bash
aws cognito-idp list-user-pool-clients \
  --user-pool-id <pool-id> --max-results 60 --output json | \
  jq '.UserPoolClients[] | {ClientId, ClientName}'
```

### List all User Pools

```bash
aws cognito-idp list-user-pools --max-results 60 --output json | \
  jq '.UserPools[] | {Id, Name}'
```

## Identity Provider inspection

### Describe a specific identity provider

```bash
aws cognito-idp describe-identity-provider \
  --user-pool-id <pool-id> \
  --provider-name <provider-name> --output json | \
  jq '.IdentityProvider | {ProviderType, ProviderName,
    ProviderDetails, AttributeMapping}'
```

### List all identity providers for a pool

```bash
aws cognito-idp list-identity-providers \
  --user-pool-id <pool-id> --max-results 50 --output json | \
  jq '.Providers[] | {ProviderType, ProviderName}'
```

## Identity Pool inspection

### Describe Identity Pool

```bash
aws cognito-identity describe-identity-pool \
  --identity-pool-id <identity-pool-id> --output json
```

### Get Identity Pool Roles

```bash
aws cognito-identity get-identity-pool-roles \
  --identity-pool-id <identity-pool-id> --output json
```

### List Identity Pools

```bash
aws cognito-identity list-identity-pools \
  --max-results 60 --output json | \
  jq '.IdentityPools[] | {IdentityPoolId, IdentityPoolName}'
```

## IAM role trust policy inspection

### Get role (trust policy)

```bash
aws iam get-role --role-name <role-name> --output json | \
  jq '.Role.AssumeRolePolicyDocument'
```

### Simulate principal policy (verify role can be assumed)

```bash
aws iam simulate-principal-policy \
  --policy-source-arn <role-arn> \
  --action-names sts:AssumeRoleWithWebIdentity \
  --output json --profile <p>
```

## Lambda trigger inspection

### List Lambda triggers for a User Pool

```bash
aws cognito-idp describe-user-pool \
  --user-pool-id <pool-id> --output json | \
  jq '.UserPool.LambdaConfig'
```

### Get Lambda function details

```bash
aws lambda get-function-configuration \
  --function-name <lambda-arn> --output json | \
  jq '{FunctionName, Runtime, Timeout, LastUpdateStatus, State}'
```

### Filter Lambda trigger logs

```bash
aws logs filter-log-events \
  --log-group-name /aws/lambda/<lambda-name> \
  --start-time $(date -d '-30 minutes' +%s)000 \
  --filter-pattern '"ERROR" OR "Exception" OR "Task timed out"' \
  --output json
```

## User inspection

### Get user details (admin)

```bash
aws cognito-idp admin-get-user \
  --user-pool-id <pool-id> \
  --username <username> --output json | \
  jq '{Username, UserStatus, Enabled, UserAttributes,
    PreferredMfaSetting, UserMFASettingList}'
```

### List users (with optional filter)

```bash
aws cognito-idp list-users \
  --user-pool-id <pool-id> \
  --filter 'attribute.[email] = "user@example.com"' \
  --output json
```

## Domain inspection

### Describe a User Pool domain

```bash
aws cognito-idp describe-user-pool-domain \
  --domain <domain-prefix> --output json
```

### List all User Pool domains

```bash
aws cognito-idp list-user-pool-domains \
  --max-results 60 --output json
```

## TLS / ACM certificate inspection

### Describe ACM certificate (must be in us-east-1 for CloudFront)

```bash
aws acm describe-certificate \
  --certificate-arn <arn> --region us-east-1 --output json | \
  jq '.Certificate.{Status, DomainName,
    DomainValidationOptions, NotAfter}'
```

### List ACM certificates

```bash
aws acm list-certificates --region us-east-1 --output json | \
  jq '.CertificateSummaryList[] | {CertificateArn, DomainName}'
```

## CloudTrail lookup

### Find Cognito API errors

```bash
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventSource,AttributeValue=cognito-idp.amazonaws.com \
  --start-time $(date -d '-1 hour' +%s) --end-time $(date +%s) \
  --output json | \
  jq '.Events[] | select(.CloudTrailEvent | contains("NotAuthorized") or contains("UserLambdaValidation"))'
```

### Find token revocation or global sign-out

```bash
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=GlobalSignOut \
  --start-time $(date -d '-24 hours' +%s) --end-time $(date +%s) \
  --output json
```

## AWS Health

### Check for regional Cognito events

```bash
aws health describe-events \
  --filter eventStatusCodes=OPEN,UPCOMING \
  --region us-east-1 --output json | \
  jq '.events[] | select(.service == "COGNITO")'
```

## DNS / domain verification (for custom domains)

### Verify the Cognito auth domain resolves

```bash
dig +short auth.example.com
dig +short auth.example.com CNAME
```

### Verify the ACM validation CNAME is in place

```bash
dig +short _<hash>.acm-validations.aws
```

## State-changing commands (require CONFIRM gate)

### Update App Client

```bash
aws cognito-idp update-user-pool-client \
  --user-pool-id <pool-id> \
  --client-id <client-id> \
  --callback-urls "https://app.example.com/auth/callback" \
  --explicit-auth-flows ALLOW_USER_PASSWORD_AUTH ALLOW_USER_SRP_AUTH ALLOW_REFRESH_TOKEN_AUTH \
  --profile <p>
```

### Update Identity Provider metadata (SAML)

```bash
aws cognito-idp update-identity-provider \
  --user-pool-id <pool-id> \
  --provider-name <saml-name> \
  --provider-details MetadataURL=<new-metadata-url> \
  --profile <p>
```

### Update IAM role trust policy

```bash
aws iam update-assume-role-policy \
  --role-name <role-name> \
  --policy-document '<trust-policy-json>' \
  --profile <p>
```

### Set Identity Pool Roles

```bash
aws cognito-identity set-identity-pool-roles \
  --identity-pool-id <identity-pool-id> \
  --roles authenticated=<auth-role-arn>,unauthenticated=<unauth-role-arn> \
  --profile <p>
```

### Reset user MFA

```bash
aws cognito-idp admin-set-user-mfa-preference \
  --user-pool-id <pool-id> \
  --username <username> \
  --software-token-mfa-settings Enabled=false,PreferredMfa=false \
  --sms-mfa-settings Enabled=false,PreferredMfa=false \
  --profile <p>
```

### Reset user password (sends reset code)

```bash
aws cognito-idp admin-reset-user-password \
  --user-pool-id <pool-id> \
  --username <username> \
  --profile <p>
```

## Account-wide pre-flight commands (moved from SKILL.md)

```bash
# 1. User Pool configuration (Policies, MfaConfiguration,
#    AdminCreateUserConfig, SchemaAttributes, LambdaConfig, Domain)
aws cognito-idp describe-user-pool \
  --user-pool-id <pool-id> --output json

# 2. App Client configuration (ExplicitAuthFlows, CallbackURLs,
#    LogoutURLs, SupportedIdentityProviders, ClientSecret,
#    RefreshTokenValidity, AccessTokenValidity, IdTokenValidity,
#    AllowedOAuthFlows, AllowedOAuthScopes)
aws cognito-idp describe-user-pool-client \
  --user-pool-id <pool-id> --client-id <client-id> --output json

# 3. Identity Pool configuration + role mappings
aws cognito-identity describe-identity-pool \
  --identity-pool-id <identity-pool-id> --output json

aws cognito-identity get-identity-pool-roles \
  --identity-pool-id <identity-pool-id> --output json

# 4. Trigger Lambda CloudWatch Logs (pre-token-generation, etc.)
aws logs filter-log-events \
  --log-group-name /aws/lambda/<trigger-lambda-name> \
  --start-time $(date -d '-30 minutes' +%s)000 \
  --filter-pattern '"ERROR" OR "Exception" OR "timeout"' \
  --output json

# 5. CloudTrail lookup for Cognito API errors
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventSource,AttributeValue=cognito-idp.amazonaws.com \
  --start-time $(date -d '-1 hour' +%s) --end-time $(date +%s) \
  --output json

# 6. AWS Health (regional events)
aws health describe-events --filter eventStatusCodes=OPEN,UPCOMING \
  --region us-east-1 --output json
```


## Pre-flight safety checks - run before any state-changing CLI (moved from SKILL.md)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`update-user-pool-client`, `update-user-pool`, `update-identity-pool`,
  `update-assume-role-policy`, `set-identity-pool-roles`,
  `admin-set-user-mfa-preference`, `admin-reset-user-password`), emit
  and await operator approval. Do NOT execute the CLI until the
  operator confirms.

- **Read-only first.** Every probe in the diagnostic tree is
  read-only (`describe-user-pool`, `describe-user-pool-client`,
  `describe-identity-provider`, `get-identity-pool-roles`,
  `describe-user-pool-domain`, `filter-log-events`,
  `lookup-events`, `get-role`, `describe-certificate`). Do not perform
  state-changing operations as diagnostic probes.

- **`update-user-pool-client`** changes the app client config. Some
  fields (like `CallbackURLs` and `ExplicitAuthFlows`) are safe to
  update; others (like `GenerateClientSecret`) require recreating the
  client. Always confirm before updating.

- **`update-user-pool`** changes the pool-level config (MFA, password
  policy, Lambda triggers). Changes propagate within seconds but affect
  all users immediately. Confirm before applying.

- **`update-assume-role-policy`** on the identity pool role trust policy
  can break ALL authentication if the policy is malformed. Always
  validate the JSON syntax before applying. Use
  `iam simulate-principal-policy` to verify after the change.

- **`admin-reset-user-password`** sends a reset code to the user. Do
  NOT use this as a diagnostic probe; it has user-visible side effects.

- **Bulk remediation batch limit.** If the diagnosis identifies the
  same root cause across multiple app clients or pools, batch
  remediation into groups of at most 5 resources, emit a single
  CONFIRM per batch, and verify between batches.


