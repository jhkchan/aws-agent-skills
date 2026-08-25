# Worked examples - CodeBuild Build Troubleshooter

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

### Worked example — ECR image pull auth (BUILD_CONTAINER_UNABLE_TO_PULL_IMAGE)

```text
TARGET: cb-deploy-runner (arn:aws:codebuild:us-east-1:123456789012:project/cb-deploy-runner)
  Build ID: cb-deploy-runner:9f8e7d6c-5b4a-3210-fedc-ba9876543210
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: The INSTALL phase fails with BUILD_CONTAINER_UNABLE_TO_PULL_IMAGE
  when pulling 111111111111.dkr.ecr.us-east-1.amazonaws.com/ci-base-images:python3.12
  (cross-account ECR). The CodeBuild service role
  (arn:aws:iam::123456789012:role/codebuild-cb-deploy-runner-role) lacks
  ecr:BatchGetImage and ecr:GetDownloadUrlForLayer on the source ECR repo.
  The image exists (950 MB, under 15 GB cap) and the project is not
  VPC-attached, ruling out IMAGE_PULL_SIZE and VPC_NO_EGRESS.
ROOT_CAUSE: IMAGE_PULL_AUTH
EVIDENCE:
  - Symptom: INSTALL phase FAILED. Log excerpt from CloudWatch:
    "BUILD_CONTAINER_UNABLE_TO_PULL_IMAGE: Unable to pull
     111111111111.dkr.ecr.us-east-1.amazonaws.com/ci-base-images:python3.12:
     insufficient privileges"
  - Failing probe:
    aws iam simulate-principal-policy \
      --policy-source-arn arn:aws:iam::123456789012:role/codebuild-cb-deploy-runner-role \
      --action-names ecr:BatchGetImage ecr:GetDownloadUrlForLayer ecr:BatchCheckLayerAvailability \
      --resource-arns arn:aws:ecr:us-east-1:111111111111:repository/ci-base-images \
      --output json
    Result: "EvalDecision": "implicitDeny" for all three actions.
  - Passing probes:
    - Image exists: aws ecr describe-images --repository-name ci-base-images \
      --image-ids imageTag=python3.12 --registry-id 111111111111
      → imageSizeInBytes: ~950 MB (under 15 GB cap)
    - Not VPC-attached: batch-get-projects shows vpcConfig = null
    - ECR repo policy exists but only grants account 111111111111 roles,
      not the CodeBuild service role in account 123456789012
REMEDIATION:
  1. Add ECR read permissions to the CodeBuild service role (account
     123456789012):
     aws iam put-role-policy \
       --role-name codebuild-cb-deploy-runner-role \
       --policy-name ecr-pull-ci-base-images \
       --policy-document '{
         "Version": "2012-10-17",
         "Statement": [
           {
             "Effect": "Allow",
             "Action": [
               "ecr:BatchGetImage",
               "ecr:GetDownloadUrlForLayer",
               "ecr:BatchCheckLayerAvailability"
             ],
             "Resource": "arn:aws:ecr:us-east-1:111111111111:repository/ci-base-images"
           },
           {
             "Effect": "Allow",
             "Action": "ecr:GetAuthorizationToken",
             "Resource": "*"
           }
         ]
       }'
  2. Grant cross-account access in the ECR repo policy (account
     111111111111):
     aws ecr put-repository-policy \
       --registry-id 111111111111 \
       --repository-name ci-base-images \
       --policy-text '{
         "Version": "2012-10-17",
         "Statement": [{
           "Sid": "AllowCodeBuildCrossAccountPull",
           "Effect": "Allow",
           "Principal": {
             "AWS": "arn:aws:iam::123456789012:role/codebuild-cb-deploy-runner-role"
           },
           "Action": [
             "ecr:BatchGetImage",
             "ecr:GetDownloadUrlForLayer",
             "ecr:BatchCheckLayerAvailability"
           ]
         }]
       }'
  3. Verify the IAM simulation now returns allowed:
     aws iam simulate-principal-policy \
       --policy-source-arn arn:aws:iam::123456789012:role/codebuild-cb-deploy-runner-role \
       --action-names ecr:BatchGetImage \
       --resource-arns arn:aws:ecr:us-east-1:111111111111:repository/ci-base-images \
       --output json
     Expected: "EvalDecision": "allowed"
  4. Re-run the build to confirm the fix:
     aws codebuild start-build --project-name cb-deploy-runner --region us-east-1
  5. Verify the INSTALL phase succeeds:
     aws codebuild batch-get-builds --ids <new-build-id> \
       --query 'builds[0].phases[?phaseType==`INSTALL`].phaseStatus' --output text
     Expected: SUCCEEDED
CONFIRM: Before updating the service role IAM and ECR repo policy, emit
  and await: "CONFIRM: About to add ECR read permissions to role
  codebuild-cb-deploy-runner-role (account 123456789012) and update the
  cross-account repo policy on ci-base-images (account 111111111111).
  Proceed? (yes/no)"
```

### Worked example — INSUFFICIENT_DATA

```text
TARGET: unknown
VERDICT: INSUFFICIENT_DATA
REASON: Input is "CodeBuild build failing in prod" with no project name,
  build ID, failed phase, or error string.
ROOT_CAUSE: UNKNOWN
EVIDENCE:
  - Missing: project name or build ID
  - Missing: observed error string or failed phase
  - Missing: region
REMEDIATION:
  1. Run aws codebuild list-projects and share the project name.
  2. Run aws codebuild list-builds-for-project --project-name <name>
     and share the most recent build ID.
  3. Run aws codebuild batch-get-builds --ids <build-id> and share
     phases[] output.
```

