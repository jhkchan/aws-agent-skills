# Baseline (no-skill) response: cross-account-externalid-deploy-role

This file captures what a generic assistant produces WITHOUT the
iam-role-deployer skill loaded — the contrast that proves the skill adds
structure (ExternalId confused-deputy protection, permission boundary,
iam:PassRole scoping, session duration tuning).

---

Here's the cross-account deploy role:

Trust policy:
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"AWS": "arn:aws:iam::222222222222:root"},
    "Action": "sts:AssumeRole"
  }]
}
```

Permissions: CloudFormation full access, S3 write, ECS update, and
PassRole.

Commands:
1. aws iam create-role --role-name cross-account-deploy-role --assume-role-policy-document file://trust.json
2. aws iam put-role-policy --role-name cross-account-deploy-role --policy-name deploy --policy-document file://perms.json

The CI/CD account can now assume this role to deploy to your production
environment.
