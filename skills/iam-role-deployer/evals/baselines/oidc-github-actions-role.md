# Baseline (no-skill) response: oidc-github-actions-role

This file captures what a generic assistant produces WITHOUT the
iam-role-deployer skill loaded — the contrast that proves the skill adds
structure (AssumeRoleWithWebIdentity action, sub condition scoping,
permission boundary, iam:PassRole scoping to specific CFn role).

---

Here's the GitHub Actions OIDC role:

Trust policy:
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Federated": "arn:aws:iam::111111111111:oidc-provider/token.actions.githubusercontent.com"
    },
    "Action": "sts:AssumeRoleWithWebIdentity"
  }]
}
```

Permissions: S3 write to the frontend bucket, CloudFormation changeset
create/execute, and PassRole for the CloudFormation execution role.

Commands:
1. aws iam create-role --role-name github-actions-deploy-role --assume-role-policy-document file://trust.json
2. aws iam put-role-policy --role-name github-actions-deploy-role --policy-name deploy --policy-document file://perms.json

Your GitHub Actions workflow can now use this role via the aws-actions/configure-aws-credentials action.
