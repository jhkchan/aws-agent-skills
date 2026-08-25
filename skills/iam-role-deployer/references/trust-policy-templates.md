# IAM Trust Policy Templates Reference

Supplementary reference for the IAM Role Deployer skill. Use when
authoring trust policies for AWS service roles, cross-account access,
OIDC/SAML federation, and permission boundaries.

## AWS service role trust policies

Service roles are assumed by AWS services (Lambda, ECS, EC2) on behalf
of your workloads. The principal is `Service: <service>.amazonaws.com`.

### Lambda function role (scoped to one function)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"Service": "lambda.amazonaws.com"},
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "aws:SourceAccount": "111111111111"
        },
        "ArnLike": {
          "aws:SourceArn": "arn:aws:lambda:us-east-1:111111111111:function:my-app-*"
        }
      }
    }
  ]
}
```

**Key points:**
- `aws:SourceAccount` prevents Lambda functions in OTHER accounts from
  using this role (defends against cross-account confused-deputy).
- `aws:SourceArn` with `ArnLike` and wildcard suffix scopes to a family
  of functions. Use exact ARN (`StringEquals`) for single-function scope.
- Without these conditions, ANY Lambda function in the account can assume
  the role.

### ECS task execution role

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"Service": "ecs-tasks.amazonaws.com"},
      "Action": "sts:AssumeRole",
      "Condition": {
        "ArnLike": {
          "aws:SourceArn": "arn:aws:ecs:us-east-1:111111111111:*"
        },
        "StringEquals": {
          "aws:SourceAccount": "111111111111"
        }
      }
    }
  ]
}
```

**Note:** ECS task roles and task execution roles share the same trust
principal. Differentiate by permission policy, not trust policy.

### EC2 instance profile role

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"Service": "ec2.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }
  ]
}
```

**Warning:** EC2 instance profile roles CANNOT be scoped with
`aws:SourceArn` the way Lambda roles can. ANY EC2 instance in the account
with this instance profile attached gets the role's permissions. Use
permission boundaries or separate roles per instance tier.

## Cross-account role trust policies

### Cross-account with ExternalId (confused-deputy protection)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::222222222222:root"},
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "sts:ExternalId": "prod-deploy-2026-unique-external-id"
        }
      }
    }
  ]
}
```

**ExternalId best practices:**
- Generate a random 32+ character string. Do NOT use account IDs, project
  names, or predictable values.
- Set the ExternalId in the TRUSTING account (the account owning the
  role). The TRUSTED account (the one assuming) must provide it at
  AssumeRole time.
- Rotate annually. Document the rotation schedule.
- The ExternalId is NOT a secret — it appears in CloudTrail and the trust
  policy JSON. The security comes from the trusting account controlling
  its value, not from secrecy.

### Cross-account with MFA (human access)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::222222222222:role/devops-team"},
      "Action": "sts:AssumeRole",
      "Condition": {
        "Bool": {"aws:MultiFactorAuthPresent": "true"},
        "NumericLessThan": {"aws:MultiFactorAuthAge": "3600"}
      }
    }
  ]
}
```

**Critical:** `Bool` qualifier is MANDATORY for `aws:MultiFactorAuthPresent`.
Without it, the condition silently fails for ALL requests.

### Cross-account with both ExternalId AND MFA

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::222222222222:role/auditor"},
      "Action": "sts:AssumeRole",
      "Condition": {
        "Bool": {"aws:MultiFactorAuthPresent": "true"},
        "StringEquals": {"sts:ExternalId": "audit-firm-2026-id"}
      }
    }
  ]
}
```

## Web Identity (OIDC) trust policies

### GitHub Actions OIDC

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::111111111111:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:my-org/my-repo:ref:refs/heads/main"
        }
      }
    }
  ]
}
```

**Sub condition patterns:**
- `repo:my-org/my-repo:ref:refs/heads/main` — main branch only
- `repo:my-org/my-repo:ref:refs/pull/*` — pull requests (read-only recommended)
- `repo:my-org/my-repo:environment:prod` — specific environment
- `repo:my-org/*` — all repos in org (broad — avoid)

### Cognito user pool OIDC

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:cognito-idp:us-east-1:111111111111:oidc-provider/cognito-idp.us-east-1.amazonaws.com/us-east-1_abc123"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "cognito-identity.amazonaws.com:aud": "us-east-1:abc123def456"
        },
        "ForAnyValue:StringLike": {
          "cognito-identity.amazonaws.com:amr": "authenticated"
        }
      }
    }
  ]
}
```

## SAML federation trust policies

### Okta / Azure AD SAML

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::111111111111:saml-provider/okta-idp"
      },
      "Action": "sts:AssumeRoleWithSAML",
      "Condition": {
        "StringEquals": {
          "SAML:aud": "https://signin.aws.amazon.com/saml"
        }
      }
    }
  ]
}
```

**SAML attribute conditions:**
```json
"Condition": {
  "StringEquals": {
    "SAML:aud": "https://signin.aws.amazon.com/saml"
  },
  "ForAnyValue:StringEquals": {
    "SAML:iss": "http://www.okta.com/abc123"
  }
}
```

## Permission boundary templates

### Delegated admin boundary (scoped to one VPC)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "*",
      "Resource": "*",
      "Condition": {
        "StringEqualsIfExists": {
          "ec2:Vpc": "arn:aws:ec2:us-east-1:111111111111:vpc/vpc-tenant-a"
        }
      }
    },
    {
      "Effect": "Deny",
      "Action": [
        "iam:CreateRole",
        "iam:DeleteRole",
        "iam:AttachRolePolicy",
        "iam:PutRolePolicy",
        "iam:PutRolePermissionsBoundary"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Deny",
      "Action": "organizations:*",
      "Resource": "*"
    }
  ]
}
```

### Region-restricted boundary

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "*",
      "Resource": "*",
      "Condition": {
        "StringEqualsIgnoreCase": {
          "aws:RequestedRegion": ["us-east-1", "eu-west-1"]
        }
      }
    }
  ]
}
```

### KMS-deletion protection boundary

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "*",
      "Resource": "*"
    },
    {
      "Effect": "Deny",
      "Action": [
        "kms:DeleteKey",
        "kms:ScheduleKeyDeletion",
        "kms:DisableKey"
      ],
      "Resource": "*"
    }
  ]
}
```

## Additional trust policy templates — MFA, OIDC, SAML (moved from SKILL.md)

**Template — cross-account role with MFA:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::222222222222:role/devops-admin"},
      "Action": "sts:AssumeRole",
      "Condition": {
        "Bool": {"aws:MultiFactorAuthPresent": "true"},
        "NumericLessThan": {"aws:MultiFactorAuthAge": "3600"}
      }
    }
  ]
}
```

**Template — OIDC (GitHub Actions):**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::111111111111:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:my-org/my-repo:ref:refs/heads/main"
        }
      }
    }
  ]
}
```

**Template — SAML (Okta/Azure AD):**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::111111111111:saml-provider/okta-idp"
      },
      "Action": "sts:AssumeRoleWithSAML",
      "Condition": {
        "StringEquals": {
          "SAML:aud": "https://signin.aws.amazon.com/saml"
        }
      }
    }
  ]
}
```
