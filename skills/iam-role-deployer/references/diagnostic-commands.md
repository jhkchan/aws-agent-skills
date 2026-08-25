# IAM Role Deployer — diagnostic & pre-flight commands (moved verbatim from SKILL.md)

> Progressive-disclosure split: this content was moved verbatim from SKILL.md; nothing was rewritten.

## Live-account pre-flight checks (from Pre-flight: role specification gate)

**Live-account pre-flight checks (skip if doing offline policy authoring):**
1. Verify the caller can run `iam:CreateRole`, `iam:PutRolePolicy`,
   `iam:AttachRolePolicy`, `iam:CreatePolicy`, and
   `iam:SimulatePrincipalPolicy`. Surface IAM gaps BEFORE emitting
   deployment commands.
2. Check for existing roles with the same name:
   `aws iam get-role --role-name <name>` (404 = available).
3. Verify referenced managed policies exist:
   `aws iam get-policy --policy-arn <arn>`.
4. For service-linked roles, verify the service supports them:
   some roles (e.g., `AWSServiceRoleForECS`) are auto-created and cannot
   be manually created with `create-role`.
5. For OIDC roles, verify the OIDC provider exists in the account:
   `aws iam list-open-id-connect-providers`.

## Step 10: Verification — deployment verification commands

```bash
# Simulate what the role can do (before deployment)
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::111111111111:role/<role> \
  --action-names s3:GetObject ecs:UpdateService iam:PassRole \
  --resource-arns "arn:aws:s3:::my-bucket/*" \
  --query 'EvaluationResults[*].[EvalActionName,EvalDecision]'

# Verify the role exists and has correct trust policy
aws iam get-role --role-name <role> \
  --query 'Role.[RoleName,Arn,MaxSessionDuration,AssumeRolePolicyDocument]'

# Verify attached managed policies
aws iam list-attached-role-policies --role-name <role>

# Verify inline policies
aws iam list-inline-role-policies --role-name <role>

# Verify permission boundary
aws iam get-role --role-name <role> --query 'Role.PermissionsBoundary'

# After AssumeRole, verify the session's effective permissions
aws sts get-caller-identity  # Confirm assumed the right role
aws iam simulate-principal-policy \
  --policy-source-arn <assumed-role-arn> \
  --action-names <action> \
  --resource-arns <resource>
```

## Pre-flight safety checks (run before any deployment CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`create-role`, `put-role-policy`, `attach-role-policy`,
  `delete-role`), the deployer MUST emit:
  `CONFIRM: About to <action> on IAM role <name> in account <account>.
  This affects <consequence>. Proceed? (yes/no)`

- **Trust policy dry-run.** Before `create-role`, validate the trust
  policy JSON:
  `aws iam simulate-principal-policy --policy-source-arn <caller> --action-names sts:AssumeRole --policy-input-list file://trust-policy.json`

- **Permission simulation.** Before attaching a permission policy, run:
  `aws iam simulate-principal-policy --policy-source-arn <role-arn> --action-names <actions> --resource-arns <resources>`
  Verify the EvalDecision is `allowed` ONLY for the intended actions.

- **Permission boundary check.** For delegated/admin roles, verify the
  boundary is in place BEFORE attaching the broad permission policy. The
  safe sequence is: (1) create role with trust policy, (2) put permission
  boundary, (3) put/attach permission policy. Reversing steps 2 and 3
  creates a window where the role has broad permissions without a
  boundary.

- **ExternalId rotation.** For cross-account roles, document the
  ExternalId and schedule annual rotation. A leaked ExternalId + a
  compromised trusted account = unauthorized assume.

- **DeleteRole is DESTRUCTIVE.** Deleting a role breaks all services and
  sessions using it. The deployer MUST require confirmation for
  `delete-role` and verify no Lambda functions, ECS tasks, EC2 instance
  profiles, or CloudFormation stacks reference the role.

- **Tag everything.** IAM roles support tags. Use
  `--tags Key=Environment,Value=prod Key=Team,Value=platform`. Tags are
  the primary cost-allocation and access-control mechanism for ABAC
  (Attribute-Based Access Control).
