# Worked examples - Cognito Identity Pool Deployer (load on demand)

## Step 3 - set-identity-pool-roles example (moved from SKILL.md)

**Set the roles on the identity pool:**

```bash
aws cognito-identity set-identity-pool-roles \
  --identity-pool-id us-east-1:abcdef-1234 \
  --roles authenticated=arn:aws:iam::123456789012:role/AppAuthenticatedRole,unauthenticated=arn:aws:iam::123456789012:role/AppUnauthenticatedRole
```

## Step 7 - GetId + GetCredentialsForIdentity authflow (moved from SKILL.md)

**Step 1: GetId** — exchange the provider token for an identity ID.

```bash
aws cognito-identity get-id \
  --identity-pool-id us-east-1:abcdef-1234 \
  --logins '{"cognito-idp.us-east-1.amazonaws.com/us-east-1_AbCdEf123":"<id-token-jwt>"}'
```

**Step 2: GetCredentialsForIdentity** — exchange the identity ID for
AWS credentials.

```bash
aws cognito-identity get-credentials-for-identity \
  --identity-id us-east-1:abcdef-1234:uuid \
  --logins '{"cognito-idp.us-east-1.amazonaws.com/us-east-1_AbCdEf123":"<id-token-jwt>"}'
```

This returns temporary AWS credentials:

```json
{
  "Credentials": {
    "AccessKeyId": "ASIA...",
    "SecretKey": "...",
    "SessionToken": "...",
    "Expiration": "2026-08-11T20:00:00Z"
  }
}
```

