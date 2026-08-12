# Eval prompt: identity-pool-unauth-role-trust

Diagnose the Cognito identity pool failure for the following Identity
Pool configuration. Walk the symptom-driven diagnostic tree and emit the
standard diagnostic block (TARGET, VERDICT, REASON, LAYER, EVIDENCE,
REMEDIATION).

Symptom: unauthenticated guests cannot access the app. API calls return
403. `GetCredentialsForIdentity` returns `NotAuthorizedException`.
Authenticated users (via User Pool login) work fine.

```text
IdentityPoolId: us-east-1:123456789012:example-pool
IdentityPool config:
  AllowUnauthenticatedIdentities: true
  Roles:
    AuthRole: arn:aws:iam::123456789012:role/CognitoAuthRole
    UnauthRole: arn:aws:iam::123456789012:role/CognitoUnauthRole

UnauthRole trust policy (get-role output):
  {
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "sts.amazonaws.com"},
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "cognito-identity.amazonaws.com:aud":
            "us-east-1:OLD_POOL_ID_9999"
        }
      }
    }]
  }

AuthRole trust policy (for comparison — works correctly):
  {
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Federated": "cognito-identity.amazonaws.com"},
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "cognito-identity.amazonaws.com:aud":
            "us-east-1:123456789012:example-pool"
        },
        "ForAnyValue:StringLike": {
          "cognito-identity.amazonaws.com:amr": "authenticated"
        }
      }
    }]
  }

Error:
  { "__type": "NotAuthorizedException",
    "message": "Invalid identity pool configuration." }
```

The unauthenticated role trust policy has TWO errors: the Principal is
`sts.amazonaws.com` instead of `cognito-identity.amazonaws.com`, and the
`aud` condition references an old pool ID. The authenticated role works
because its trust policy is correct.
