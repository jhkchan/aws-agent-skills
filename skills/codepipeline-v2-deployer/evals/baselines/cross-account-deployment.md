# Baseline (no-skill) response: cross-account-deployment

This file captures what a generic assistant produces WITHOUT the
codepipeline-v2-deployer skill loaded. The contrast proves the skill
adds the cross-account contract (KMS key policy grants for target
role, target account IAM role trust policy, S3 bucket policy + KMS
policy coordination, the "Access Denied on S3 is usually KMS"
diagnostic).

---

Here's a plan for your cross-account pipeline.

Architecture:

- Pipeline in source account 111111111111
- Deploy to target account 222222222222
- Source: CodeCommit
- Build: CodeBuild
- Deploy: CloudFormation in target account

Steps:

1. Create a KMS key in the source account.
2. Create a cross-account IAM role in the target account.
3. Set up the artifact bucket.
4. Configure the pipeline with CloudFormation deploy action pointing
   at the cross-account role.

For cross-account, you need to share the artifact bucket and grant
the target role access.

Commands:

```
aws kms create-key ...
aws iam create-role --role-name CrossAccountCFNExecution ...
aws s3api create-bucket ...
aws codepipeline create-pipeline ...
```

Make sure the target role can decrypt the artifacts.
