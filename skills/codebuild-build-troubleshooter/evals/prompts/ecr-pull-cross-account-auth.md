# Eval prompt: ecr-pull-cross-account-auth

Diagnose the CodeBuild build failure for the following project. Walk
the phase-status-driven diagnostic tree and emit the standard
diagnostic block (TARGET, VERDICT, REASON, ROOT_CAUSE, EVIDENCE,
REMEDIATION).

Symptom: project `cb-deploy-runner` fails in the INSTALL phase before
any buildspec command runs. The error is
BUILD_CONTAINER_UNABLE_TO_PULL_IMAGE for image
`111111111111.dkr.ecr.us-east-1.amazonaws.com/base-images:latest`.
The CodeBuild project is in account 222222222222; the ECR repo is in
account 111111111111.

```text
ProjectName: cb-deploy-runner
BuildId: cb-deploy-runner:def67890
Environment:
  Image: 111111111111.dkr.ecr.us-east-1.amazonaws.com/base-images:latest
  PrivilegedMode: false
  ComputeType: BUILD_GENERAL1_MEDIUM
ServiceRole: arn:aws:iam::222222222222:role/service-role-codebuild-cb-deploy-runner
ServiceRolePolicies:
  - AWSCodeBuildDeveloperAccess (managed)
  - inline: { s3-artifacts: s3:PutObject on artifacts bucket }
ServiceRole ECR permissions: NOT PRESENT
ECR Repository: 111111111111.dkr.ecr.us-east-1.amazonaws.com/base-images
Image exists: yes, 850 MB compressed
Build is NOT VPC-attached.

Phase details:
  phaseType: INSTALL
  phaseStatus: FAILED
  contexts[0].message: "BUILD_CONTAINER_UNABLE_TO_PULL_IMAGE:
    Unable to pull
    111111111111.dkr.ecr.us-east-1.amazonaws.com/base-images:latest"
```

The image exists and is under the size cap. The build is not
VPC-attached so VPC routing is not in play. Focus on the service role
permissions for ECR.
