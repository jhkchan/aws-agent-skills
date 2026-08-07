---
description: Create production-grade IAM roles with correct trust policies, least-privilege permissions, condition keys, permission boundaries, and MFA enforcement across AWS service, cross-account, OIDC, and SAML principal types.
nl_triggers:
  - "create an IAM role"
  - "trust policy for Lambda"
  - "cross-account role with ExternalId"
  - "OIDC role for GitHub Actions"
  - "SAML federation role"
  - "permission boundary for delegation"
  - "deploy role for CI/CD"
  - "MFA enforcement on assume role"
  - "role chaining pattern"
  - "session policy for scoped access"
  - "maximum session duration"
  - "simulate principal policy"
  - "ECS task role trust policy"
  - "EC2 instance profile role"
  - "least privilege IAM role"
routes_to: iam-role-deployer
---

# /aws:deploy-iam-role

Activate the `iam-role-deployer` skill and produce a deployment plan for
an IAM role with correct trust policy and least-privilege permissions.

## What it does

Reads a role specification (principal type, trusted entities, required
permissions, condition keys, session duration, permission boundary) and
produces a deployment plan with:

1. Pre-flight specification gate — validates principal type, trusted
   principal, permissions. Blocks deployment (PREREQUISITES_MISSING) on
   wildcard principals, missing SourceArn conditions, or missing required
   fields.
2. Principal type classification — AWS service (lambda, ecs, ec2),
   cross-account (with ExternalId), Web Identity (OIDC for GitHub
   Actions, Cognito), SAML federation (Okta, Azure AD).
3. Trust policy design — specific principal (no wildcards), condition
   keys (SourceArn, SourceAccount, ExternalId, MFA), correct action
   (AssumeRole, AssumeRoleWithWebIdentity, AssumeRoleWithSAML).
4. Permission policy design — least-privilege, managed policies preferred,
   iam:PassRole scoped to specific role ARNs.
5. Permission boundary — MAXIMUM permissions for delegated/admin roles
   (intersection with permission policy).
6. Condition keys — SourceVpc/SourceVpce (strong), RequestedRegion,
   CalledVia, MFA with Bool qualifier (mandatory).
7. Session duration tuning — 1h for services, 1-4h for humans with MFA,
   15min for break-glass.
8. Role chaining patterns — linear, hub-and-spoke, break-glass. Max
   chain depth is 4.
9. Session policies — just-in-time scoping at AssumeRole time.
10. Verification — simulate-principal-policy, get-role,
    list-attached-role-policies before deployment.

Emits a deterministic deployment plan per role:

```text
ROLE_SPEC: <name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
TRUST_POLICY:
  Principal / Action / Conditions / ExternalId / MFA
PERMISSIONS:
  Managed policies / Inline policies / Permission boundary / Effective scope
CHECKLIST:
  [x] Trust policy has specific principal (no wildcards)
  [x] Trust policy has condition keys (SourceArn/SourceAccount)
  [x] Permission policy is least-privilege
  [x] iam:PassRole scoped to specific role ARNs
  ...
FINDINGS:
  - [INFO] ExternalId recommended for cross-account trust
  - [WARN] MaxSessionDuration is 12h — consider reducing
DEPLOY_COMMANDS:
  <ordered list of aws iam create-role + put/attach-policy commands>
```

## When to invoke

Provide a role spec and ask any of:

- "create a Lambda role that reads from S3 and writes to DynamoDB"
- "cross-account role with ExternalId for our CI/CD pipeline"
- "OIDC role for GitHub Actions to deploy to production"
- "permission boundary for delegated admin access"
- "MFA enforcement on the break-glass admin role"
- "simulate what this role can actually do before we deploy it"

A bare role name + principal type + "create role" also routes here via
the orchestrator.

## Inputs

- **Required:** role_name, principal_type (service | cross-account |
  web-identity | saml), trusted_principal (service name, account ID, or
  provider ARN), permissions (required actions/resources, or managed
  policy ARNs).
- **Optional:** condition_keys (SourceArn, SourceVpc, RequestedRegion),
  permission_boundary (ARN), max_session_duration (seconds), mfa_required
  (true/false), external_id (for cross-account).

## Outputs

- One VERDICT block per role (READY_TO_DEPLOY or PREREQUISITES_MISSING).
- TRUST_POLICY summary with principal, conditions, ExternalId, MFA.
- PERMISSIONS summary with managed policies, inline policies, permission
  boundary, and effective scope (intersection).
- CHECKLIST with all 10 trust-and-permission dimensions validated.
- FINDINGS with security warnings and best-practice notes.
- DEPLOY_COMMANDS with ordered `aws iam create-role` + `put/attach-policy`
  commands.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 1 Deploy specialist for IAM identity).
- `/aws:audit-iam-least-privilege` for post-deployment IAM policy analysis.
- `/aws:audit-sts-cross-account-role` for cross-account trust-policy
  auditing.
- `/aws:deploy-vpc-network` for VPC provisioning (roles often need VPC-
  scoped conditions referencing the VPC ID).
