# Worked examples - Cognito Auth Troubleshooter (load on demand)

## Worked example - Identity pool unauthenticated role trust policy (secondary)

```text
TARGET: identity-pool us-east-1:123456789012:example-pool
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: GetCredentialsForIdentity returns NotAuthorizedException for
  unauthenticated access. The unauthenticated role's trust policy
  principal is sts.amazonaws.com instead of
  cognito-identity.amazonaws.com, and the aud condition references the
  wrong identity pool ID (Step 7).
LAYER: IDENTITY_POOL_TRUST
EVIDENCE:
  - Symptom: unauthenticated guests cannot access the app; API calls
    return 403. Authenticated users work fine.
  - Probe: aws cognito-identity get-identity-pool-roles returns
    Roles: {UnauthRole: arn:aws:iam::123456789012:role/CognitoUnauthRole}.
    aws iam get-role shows AssumeRolePolicyDocument with Principal:
    {Service: "sts.amazonaws.com"} and condition aud =
    "us-east-1:OLD_POOL_ID".
  - Passing: the authenticated role trust policy is correct (Principal:
    cognito-identity.amazonaws.com, aud matches current pool ID).
REMEDIATION:
  1. Update the unauthenticated role trust policy:
     aws iam update-assume-role-policy \
       --role-name CognitoUnauthRole \
       --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Federated":"cognito-identity.amazonaws.com"},"Action":"sts:AssumeRoleWithWebIdentity","Condition":{"StringEquals":{"cognito-identity.amazonaws.com:aud":"us-east-1:123456789012:example-pool"},"ForAnyValue:StringLike":{"cognito-identity.amazonaws.com:amr":"unauth"}}}]}'
  2. Verify by calling GetCredentialsForIdentity with an unauthenticated
    identity and confirming it returns credentials without error.
CONFIRM: Before updating the trust policy, emit and await:
  "CONFIRM: About to update CognitoUnauthRole trust policy. Proceed?
   (yes/no)"
```


## Worked example - Pre-token-generation Lambda error (secondary)

```text
TARGET: us-east-1_AbCdEf123 / trigger: pre-token-gen-fn
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: Every sign-in fails with UserLambdaValidationException. The
  pre-token-generation Lambda throws TypeError: Cannot read property
  'department' of undefined when the IdP claim mapping is missing the
  custom:department attribute (Step 6).
LAYER: PRE_TOKEN_GEN_LAMBDA
EVIDENCE:
  - Symptom: no user can sign in; all return
    UserLambdaValidationException with the Lambda exception message.
  - Probe: aws logs filter-log-events on /aws/lambda/pre-token-gen-fn
    returns "TypeError: Cannot read property 'department' of undefined"
    200 times in the last hour.
  - Passing: User Pool MfaConfiguration is OFF; no SAML or social
    providers configured; app client ExplicitAuthFlows includes
    ALLOW_USER_PASSWORD_AUTH.
REMEDIATION:
  1. Fix the Lambda to handle missing custom attributes gracefully:
     const department = event.request.userAttributes['custom:department'] || 'unknown';
  2. Deploy the updated Lambda function.
  3. Verify by signing in as a test user and confirming the JWT
    contains the department claim.
```


