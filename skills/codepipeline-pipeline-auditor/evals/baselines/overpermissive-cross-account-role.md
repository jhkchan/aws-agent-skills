# Baseline (no-skill) response: overpermissive-cross-account-role

This file captures what a generic assistant produces WITHOUT the
codepipeline-pipeline-auditor skill loaded.

---

The pipeline deploys using a CloudFormation role from account
222222222222, which is different from the pipeline's account
(111111111111). This means the pipeline is deploying resources into
another AWS account.

The artifact store has KMS encryption which is good. The source uses
CodeStar Connection which is secure.

If the cross-account deployment is intentional, make sure the role in
account 222222222222 has appropriate permissions and an ExternalId
condition. Otherwise, update the RoleArn to use a same-account role.
