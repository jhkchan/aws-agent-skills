# End-to-end usage scenario: iam-role-deployer

A walkthrough showing the skill producing a deployment plan for a
cross-account CI/CD deploy role with ExternalId, permission boundary,
scoped iam:PassRole, and session duration tuning. Demonstrates the
READY_TO_DEPLOY verdict, trust-policy validation, and permission-scope
assessment.

## Input (user prompt)

> I need a role that our CI/CD account (222222222222) can assume to
> deploy CloudFormation stacks to production. It should be able to push
> artifacts to S3, update ECS services, and pass the ECS task roles to
> CloudFormation. Limit it to the prod VPC and make sure it can't create
> or delete IAM roles.

## Expected behavior

1. **Pre-flight:** The skill validates the role spec — principal type
   (cross-account), trusted principal (222222222222), permissions
   (CloudFormation, S3, ECS, iam:PassRole), permission boundary
   (prod-VPC-scoped). All required fields present.
2. **Trust policy:** Cross-account with ExternalId for confused-deputy
   protection. No MFA (service-to-service via OIDC at CI/CD source).
3. **Permission policy:** Scoped CloudFormation on `prod-*` stacks, S3
   PutObject on `build-artifacts/*`, ECS UpdateService on
   `prod-cluster/*`, iam:PassRole on `ecs-task-execution` and
   `ecs-task-app` ONLY (not `*`).
4. **Permission boundary:** Allow `*` on resources within
   `vpc-aaaabbbbcccc`; deny IAM role create/delete/policy modification;
   deny Organizations.
5. **Session duration:** 3600s (1 hour — CI/CD jobs are short).
6. **Verification:** simulate-principal-policy before deploy to confirm
   effective permissions match intent.

## Expected output

```text
ROLE_SPEC: cross-account-deploy-role
VERDICT: READY_TO_DEPLOY
TRUST_POLICY:
  Principal: AWS: arn:aws:iam::222222222222:root (CI/CD account)
  Action: sts:AssumeRole
  Conditions: sts:ExternalId=prod-deploy-2026-unique-id
  ExternalId: yes (confused-deputy protection)
  MFA: not required (service-to-service via OIDC at source)
PERMISSIONS:
  Managed policies: none (all custom inline)
  Inline policies: deploy-permissions
    - cloudformation:* on arn:aws:cloudformation:us-east-1:111111111111:stack/prod-*
    - s3:PutObject on arn:aws:s3:::build-artifacts/*
    - ecs:UpdateService on arn:aws:ecs:us-east-1:111111111111:service/prod-cluster/*
    - iam:PassRole on ecs-task-execution and ecs-task-app ONLY
  Permission boundary: arn:aws:iam::111111111111:policy/boundary-prod-deploy
  Effective scope: CloudFormation + S3 artifacts + ECS prod-cluster + PassRole
    (ecs-task roles only), limited to prod VPC, IAM role management denied
CHECKLIST:
  [x] Trust policy has specific principal (CI/CD account 222222222222)
  [x] Trust policy has ExternalId (confused-deputy protection)
  [x] Permission policy is least-privilege (specific CFn, S3, ECS, IAM scope)
  [x] iam:PassRole scoped to ecs-task-execution and ecs-task-app only
  [x] Permission boundary applied (limits to prod VPC, denies IAM management)
  [x] MaxSessionDuration: 3600 (CI/CD jobs are short-lived)
  [x] No MFA (service-to-service via OIDC at CI/CD source account)
  [x] No circular role chains
FINDINGS:
  - [INFO] ExternalId should be rotated annually — document the rotation schedule
  - [WARN] cloudformation:* is broad within prod-* scope — consider scoping to specific stack names
  - [INFO] Permission boundary denies Organizations actions — prevents account-level changes
DEPLOY_COMMANDS:
  1. aws iam create-role --role-name cross-account-deploy-role \
       --assume-role-policy-document file://trust-policy.json \
       --max-session-duration 3600
  2. aws iam create-policy --policy-name boundary-prod-deploy \
       --policy-document file://boundary.json
  3. aws iam put-role-permissions-boundary --role-name cross-account-deploy-role \
       --permissions-boundary arn:aws:iam::111111111111:policy/boundary-prod-deploy
  4. aws iam put-role-policy --role-name cross-account-deploy-role \
       --policy-name deploy-permissions --policy-document file://permissions.json
  5. aws iam simulate-principal-policy \
       --policy-source-arn arn:aws:iam::111111111111:role/cross-account-deploy-role \
       --action-names cloudformation:CreateStack s3:PutObject ecs:UpdateService iam:PassRole \
       --query 'EvaluationResults[*].[EvalActionName,EvalDecision]'
```

## Post-deployment verification

After running the deploy commands, verify the role's effective permissions:

```bash
# Verify the role exists with correct trust policy and session duration
aws iam get-role --role-name cross-account-deploy-role \
  --query 'Role.[RoleName,Arn,MaxSessionDuration]'

# Verify the trust policy includes ExternalId
aws iam get-role --role-name cross-account-deploy-role \
  --query 'Role.AssumeRolePolicyDocument.Statement[0].Condition'

# Verify the permission boundary is applied
aws iam get-role --role-name cross-account-deploy-role \
  --query 'Role.PermissionsBoundary.PermissionsBoundaryArn'

# Verify the inline permission policy scope
aws iam get-role-policy --role-name cross-account-deploy-role \
  --policy-name deploy-permissions

# Simulate effective permissions (intersection of permission policy + boundary)
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::111111111111:role/cross-account-deploy-role \
  --action-names cloudformation:CreateStack iam:CreateRole organizations:LeaveOrganization \
  --query 'EvaluationResults[*].[EvalActionName,EvalDecision]'

# Expected: CreateStack=allowed, CreateRole=implicitDeny (boundary), LeaveOrganization=implicitDeny (boundary)
```

## Common pitfalls to verify after deployment

1. **ExternalId is set in the trust policy.** Without it, any principal
   in account 222222222222 can assume the role — including compromised
   roles in that account.
2. **Permission boundary applied BEFORE broad permission policy.** The
   safe sequence is: create-role → put-permissions-boundary → put-role-policy.
   Reversing the last two creates a window with broad permissions and no
   boundary.
3. **iam:PassRole scoped to specific roles.** A broad `Resource: "*"` on
   PassRole allows passing admin roles to EC2/Lambda/CloudFormation — a
   privilege-escalation path.
4. **MaxSessionDuration is 3600, not 43200.** Long-lived credentials for
   CI/CD are unnecessary and increase the credential-theft window.
