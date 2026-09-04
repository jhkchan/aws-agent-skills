# DevTools skills (24)

Precise call: `@skills:gh:jhkchan/aws-agent-skills/skills/<name>` (swap `<name>` for a row below).

| Skill | Task type | What it does |
|---|---|---|
| `amplify-app-deployer` | deploy | Provisions AWS Amplify applications with production defaults: Git-based deployments (CodeCommit, GitHub, GitLab, Bitbucket) with OAuth or service-role |
| `amplify-branch-deployer` | deploy | Configures AWS Amplify branch deployments with production defaults: app creation from a Git repository (GitHub/GitLab/Bitbucket), branch configuration |
| `cicd-pipeline-automator` | automate | Designs and implements AWS-native CI/CD pipelines end-to-end using CodePipeline, CodeBuild, CodeDeploy, CloudFormation, CDK, and Terraform. |
| `cloud9-environment-deployer` | deploy | Provisions AWS Cloud9 environments with production defaults: EC2 instance type selection, platform (Amazon Linux, Ubuntu), connection mode (SSH, SSM), |
| `cloudformation-cfn-lint-operator` | operate | Operates CloudFormation template linting and validation with production defaults: cfn-lint integration (rule-based static analysis), template pre-depl |
| `cloudformation-drift-troubleshooter` | troubleshoot | Diagnoses AWS CloudFormation stack drift — resources whose actual configuration diverged from the template because they were changed, deleted, or adde |
| `cloudformation-stack-rollback-troubleshooter` | troubleshoot | Diagnoses AWS CloudFormation stack rollback failures through a rollback-focused decision tree: UPDATE_ROLLBACK_FAILED state requiring ContinueUpdateRo |
| `cloudformation-stack-troubleshooter` | troubleshoot | Diagnoses AWS CloudFormation stack failures across the lifecycle. |
| `cloudformation-stackset-deployer` | deploy | Provisions AWS CloudFormation StackSets with production defaults: StackSet creation (template, parameters, capabilities), permission model (SELF_MANAG |
| `codeartifact-domain-deployer` | deploy | Provisions AWS CodeArtifact domains with production defaults: domain creation (create-domain), repository creation within a domain (create-repository) |
| `codeartifact-repository-deployer` | deploy | Provisions AWS CodeArtifact repositories: domain creation, repository creation across package formats (npm, pip, maven, nuget, cargo, rubygems, generi |
| `codebuild-build-troubleshooter` | troubleshoot | Diagnoses AWS CodeBuild build failures through a stopped-phase-first diagnostic tree: BUILD_CONTAINER_UNABLE_TO_PULL_IMAGE (ECR auth, image size, Dock |
| `codebuild-project-auditor` | audit | Audits AWS CodeBuild projects for privileged mode (Docker-in-Docker host kernel access), plaintext secrets in environment variables, unencrypted S3 lo |
| `codecommit-repository-auditor` | audit | Audits AWS CodeCommit repositories for approval-rule-template coverage, customer-managed KMS encryption, default-branch deletion protection (IAM enfor |
| `codecommit-repository-deployer` | deploy | Provisions AWS CodeCommit repositories with production defaults: repository creation (create-repository), default branch, KMS encryption with customer |
| `codedeploy-deployment-group-auditor` | audit | Audits AWS CodeDeploy deployment groups for auto-rollback enablement, CloudWatch alarm monitoring, deployment-config risk (AllAtATime, custom minimum- |
| `codepipeline-failure-troubleshooter` | troubleshoot | Diagnoses AWS CodePipeline execution failures across source, build, deploy, and approval stages. |
| `codepipeline-pipeline-auditor` | audit | Audits AWS CodePipeline pipelines for artifact-store encryption (KMS CMK presence), cross-account or over-permissive action roles, disabled stage tran |
| `codepipeline-v2-deployer` | deploy | Provisions production-grade CodePipeline V2-type pipelines with event-driven triggers (no polling), structure (stages and actions), source actions (Co |
| `ecr-push-pull-troubleshooter` | troubleshoot | Diagnoses Amazon ECR push and pull failures through a fourteen-category diagnostic tree: authentication (docker login token expiry, IAM ecr:GetAuthori |
| `ecr-replication-deployer` | deploy | Provisions Amazon ECR cross-region and cross-account replication with production defaults: registry-level replication configuration (put-registry-repl |
| `eventbridge-bus-policy-auditor` | audit | Audits AWS EventBridge event buses for public event-injection exposure (Principal:* or cross-account with events:PutEvents and no strong condition), m |
| `iac-template-automator` | automate | Generates and validates Infrastructure-as-Code templates for common AWS patterns across CloudFormation (template structure, nested stacks, cross-stack |
| `serverlessrepo-application-deployer` | deploy | Provisions AWS Serverless Application Repository (SAR) applications with production defaults: SAM template (template.yaml) with Transform: AWS::Server |
