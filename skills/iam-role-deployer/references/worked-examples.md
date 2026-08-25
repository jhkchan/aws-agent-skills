# IAM Role Deployer — worked examples (moved verbatim from SKILL.md)

> Progressive-disclosure split: this content was moved verbatim from SKILL.md; nothing was rewritten.

## Worked example — cross-account deploy role with ExternalId

```text
ROLE_SPEC: cross-account-deploy-role
VERDICT: READY_TO_DEPLOY
TRUST_POLICY:
  Principal: AWS: arn:aws:iam::222222222222:root (CI/CD account)
  Action: sts:AssumeRole
  Conditions: sts:ExternalId=prod-deploy-2026-unique-id
  ExternalId: yes
  MFA: not required (service-to-service, CI/CD uses OIDC at the source)
PERMISSIONS:
  Managed policies: none (all custom)
  Inline policies: deploy-permissions (cloudformation:*, s3:PutObject on artifacts/*, ecs:UpdateService on prod-cluster/*, iam:PassRole on ecs-task-*)
  Permission boundary: arn:aws:iam::111111111111:policy/boundary-prod-deploy
  Effective scope: CloudFormation + S3 artifacts + ECS prod-cluster + PassRole (ecs-task roles only)
CHECKLIST:
  [x] Trust policy has specific principal (CI/CD account 222222222222)
  [x] Trust policy has ExternalId (confused-deputy protection)
  [x] Permission policy is least-privilege (specific CloudFormation, S3, ECS, IAM scope)
  [x] iam:PassRole scoped to ecs-task-execution and ecs-task-app only
  [x] Permission boundary applied (limits to prod VPC resources)
  [x] MaxSessionDuration: 3600 (CI/CD jobs are short)
  [x] No MFA (service-to-service via OIDC at source)
  [x] No role chaining (direct assume from CI/CD account)
FINDINGS:
  - [INFO] ExternalId should be rotated annually
  - [WARN] cloudformation:* is broad — consider scoping to specific stack names
DEPLOY_COMMANDS:
  1. aws iam create-role --role-name cross-account-deploy-role --assume-role-policy-document file://trust-policy.json
  2. aws iam create-policy --policy-name boundary-prod-deploy --policy-document file://boundary.json
  3. aws iam put-role-permissions-boundary --role-name cross-account-deploy-role --permissions-boundary arn:aws:iam::111111111111:policy/boundary-prod-deploy
  4. aws iam put-role-policy --role-name cross-account-deploy-role --policy-name deploy-permissions --policy-document file://permissions.json
```
