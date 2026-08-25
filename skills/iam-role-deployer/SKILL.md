---
name: iam-role-deployer
description: 'Creates production-grade IAM roles with correct trust policies and least- privilege permissions across all principal types: AWS service roles (lambda, ecs-tasks, ec2, etc.), cross-account roles with ExternalId and MFA enforcement, Web Identity / OIDC federation (GitHub Actions, Cognito), and SAML federation. Covers permission boundaries for delegation, managed vs inline policies (prefer managed), condition keys for security (aws:SourceIp, aws:SourceVpc, aws:SourceVpce, aws:MultiFactorAuthPresent, aws:RequestedRegion, aws:CalledVia), role chaining patterns, session policies for scoped access, maximum session duration tuning, common role templates (read-only, deploy, admin-delegated), and verification via simulate-principal-policy, get-role, and list-attached-role-policies. Emits a deterministic deployment plan with a READY_TO_DEPLOY checklist, trust-policy validation, and permission-scope assessment. Use when creating IAM roles for AWS services, designing cross-account access, setting up OIDC/SAML...'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline trust-policy and permission document authoring. Live deployment uses aws iam create-role, put-role-policy, attach-role-policy, create-policy, simulate-principal- policy, get-role, and list-attached-role-policies (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Security
  task_type: deploy
  skill_class: capability
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  when_to_use: Creating an IAM role for an AWS service (Lambda, ECS, EC2, etc.), designing cross-account access with ExternalId or MFA, setting up OIDC federation for GitHub Actions or Cognito, configuring SAML federation, scoping a CI/CD deploy role with permission boundaries, applying condition keys (aws:SourceVpc, aws:RequestedRegion, aws:CalledVia), tuning session duration, building role-chaining patterns, or hardening IAM role posture before production deployment.
  activation_triggers: create an IAM role, trust policy for Lambda, cross-account role with ExternalId, OIDC role for GitHub Actions, SAML federation role, permission boundary for delegation, deploy role for CI/CD, MFA enforcement on assume role, role chaining pattern, session policy for scoped access, maximum session duration, simulate principal policy
  invocation_schema: 'Input shape (one of): (a) a role specification including principal type, trusted entities, required permissions, condition keys, session duration, and permission boundary; (b) a partial spec for interactive refinement (e.g., "Lambda role that reads from S3 and writes to DynamoDB"); (c) an existing role ARN for trust-policy and permission- scope review. Output shape: { ROLE_SPEC, VERDICT, TRUST_POLICY, PERMISSIONS, CHECKLIST[], FINDINGS[], DEPLOY_COMMANDS } where VERDICT ∈ { READY_TO_DEPLOY, PREREQUISITES_MISSING, ERROR }.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: IAM, IAM role, trust policy, assume role, AssumeRolePolicyDocument, least privilege, cross-account, ExternalId, MFA enforcement, Web Identity, OIDC, GitHub Actions, Cognito, SAML federation, permission boundary, managed policy, inline policy, condition keys, aws:SourceIp, aws:SourceVpc, aws:SourceVpce, aws:MultiFactorAuthPresent, aws:RequestedRegion, aws:CalledVia, role chaining, session policy, session duration, sts:AssumeRole, simulate-principal-policy
  tags: iam, security, deploy, trust-policy, cross-account, oidc, saml, permission-boundary, least-privilege, condition-keys, role-chaining
---

# IAM Role Deployer

## Mindset

**One-line takeaway:** an IAM role is a **delegation contract** — the
trust policy defines WHO can assume the role, the permission policy
defines WHAT the role can do, and the gap between the two is the blast
radius if either side is compromised. A well-designed role makes both
sides as narrow as possible and adds condition keys to bind the
delegation to a specific context.

Three facts make IAM role design different from "write a policy JSON":

- **The trust policy is the more dangerous policy.** Operators focus on
  the permission policy (what the role can do) but the trust policy (who
  can assume the role) is the more common attack vector. A trust policy
  with `Principal: {"AWS": "*"}` lets ANY AWS account assume the role —
  the permission policy scope is irrelevant. The majority of cross-
  account privilege-escalation incidents come from permissive trust
  policies, not permissive permission policies.

- **`sts:AssumeRole` is the highest-leverage action in IAM.** A principal
  with `sts:AssumeRole` on a role with broad permissions effectively has
  those permissions. A role that grants `sts:AssumeRole` to `*` delegates
  everything. The permission policy's `Action` and `Resource` scope is
  only half the security boundary — the trust policy's `Principal` scope
  is the other half, and it is evaluated FIRST.

- **Condition keys are the difference between a role and a SCOPED role.**
  A trust policy that allows `lambda.amazonaws.com` to assume a role is
  unscoped — any Lambda function in the account can use it. Adding
  `aws:SourceArn` conditions binds the role to a specific function, app,
  or service. Without condition keys, the trust policy is permissive by
  default.

## Quick reference — deployment checklist

| Dimension | Requirement | Step |
|---|---|---|
| Principal type | Identified: AWS service, cross-account, OIDC, SAML | Step 1 |
| Trust policy | Specific principal, no wildcards, condition keys applied | Step 2 |
| Permission policy | Least-privilege, managed policies preferred | Step 3 |
| Permission boundary | Required for delegation scenarios | Step 4 |
| Condition keys | SourceArn/SourceVpc/RequestedRegion where applicable | Step 5 |
| Session duration | Tuned (1-12 hours), not default 12h | Step 6 |
| MFA enforcement | Required for human-accessible roles | Step 7 |
| Role chaining | Avoid circular chains, document the chain | Step 8 |
| Session policies | Used for just-in-time scoped access | Step 9 |
| Verification | simulate-principal-policy before deploy | Step 10 |

## Pre-flight: role specification gate (run before deployment output)

Before producing the deployment plan, validate the input specification.
Several requirements **block deployment** — proceeding with an invalid
spec produces an insecure or non-functional role.

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

| Attribute | Value | Effect on plan |
|---|---|---|
| Principal type | AWS service (lambda, ecs, ec2) | Trust policy: `Service: <service>.amazonaws.com` |
| Principal type | Cross-account (AWS account) | Trust policy: `AWS: <account-arn>`, ExternalId recommended |
| Principal type | Web Identity (OIDC) | Trust policy: `Federated: <oidc-arn>`, conditions on sub/aud |
| Principal type | SAML | Trust policy: `Federated: <saml-arn>`, conditions on SAML attributes |
| Permission scope | Read-only | Managed: `ReadOnlyAccess` or custom scoped |
| Permission scope | Deploy (CI/CD) | Custom + permission boundary |
| Permission scope | Admin-delegated | `AdministratorAccess` + permission boundary MANDATORY |
| Session duration | Default (1h) | Acceptable for service roles |
| Session duration | Human access | Set to 1-4 hours with MFA requirement |
| MFA required | Yes | Trust policy condition `aws:MultiFactorAuthPresent: true` |

**If the role spec is incomplete** (missing principal type or permission
requirements), output:

```text
ROLE_SPEC: <name-or-unknown>
VERDICT: PREREQUISITES_MISSING
REASON: Role specification is missing required fields (<list>).
Cannot produce a deployment plan without <field> — the resulting role
would be non-functional or insecure.
REQUIRED:
  - role_name (IAM role name, 1-64 chars, alphanumeric + +=,.@-)
  - principal_type (service | cross-account | web-identity | saml)
  - trusted_principal (service name, account ID, or provider ARN)
  - permissions (required actions/resources, or managed policy ARNs)
```

## Process — Trust policy and permission design (apply in order, produce deployment plan)

### Step 0: Expert knowledge — non-obvious IAM behaviors that change the plan

These behaviors are easy to misjudge without operational IAM experience.
Each changes the role design if ignored:

- **The trust policy is the PRIMARY attack surface.** A role's permission
  policy may be perfectly scoped, but if the trust policy allows
  `Principal: {"AWS": "*"}`, any AWS principal in the world can assume
  the role and inherit those permissions. The trust policy is evaluated
  first — if it grants assume, the permission policy's scope applies.
  Always audit the trust policy as rigorously as the permission policy.

- **`lambda.amazonaws.com` in a trust policy means ANY Lambda function in
  the account.** Without a `aws:SourceArn` condition, every Lambda in the
  account can assume the role. A role intended for one function is
  accessible by all functions. Always scope service roles with
  `aws:SourceArn` or `aws:SourceAccount`.

- **`Principal: {"Service": "ec2.amazonaws.com"}` is different from other
  service principals.** EC2 instance profiles use this trust policy, but
  the role is attached to the instance via an instance profile, not
  assumed directly. The role's permissions are available to ALL code on
  the instance — there is no per-process or per-container scoping within
  an EC2 instance.

- **ExternalId is NOT a secret.** The ExternalId is a value set by the
  trusting account (the account that owns the role) and provided to the
  trusted account (the account that assumes the role). It prevents the
  "confused deputy" problem where a third party tricks the trusted
  account into assuming the role. It is NOT a password — it is visible in
  CloudTrail and the role's trust policy. The security comes from the
  trusting account SETTING it, not from keeping it secret.

- **`aws:MultiFactorAuthPresent` in a trust policy condition MUST be
  `Bool`.** Using `String` or without the `Bool` qualifier silently fails
  — the condition evaluates to false for ALL requests, including those
  with MFA. The correct condition is:
  `"Condition": {"Bool": {"aws:MultiFactorAuthPresent": "true"}}`.

- **`aws:MultiFactorAuthPresent` does NOT exist for service roles.**
  Services assuming roles (Lambda, ECS, EC2) do not present MFA. A trust
  policy requiring MFA on a service principal silently breaks the role —
  the service cannot assume it. Only human-facing roles (cross-account,
  SAML, OIDC with user identity) can enforce MFA.

- **Maximum session duration is a MAXIMUM, not a default.** A role with
  `MaxSessionDuration: 3600` (1 hour) allows AssumeRole sessions of up
  to 1 hour. Callers can request shorter durations via `--duration-seconds`.
  The default is 1 hour; the maximum configurable is 12 hours (43200s).
  Setting it to 12 hours for a service role is harmless (services request
  1h or less). Setting it to 12 hours for a human role encourages
  long-lived credentials — set to 1-4 hours with MFA.

- **Permission boundaries are a MAXIMUM, not a grant.** A permission
  boundary sets the MAXIMUM permissions a role can have — it does NOT
  grant any permissions. The effective permissions are the INTERSECTION
  of the permission policy and the permission boundary. A role with
  `AdministratorAccess` and a permission boundary limiting to `s3:*` on
  one bucket can only access that bucket, despite the admin policy.

- **Managed policies are versioned (up to 5 versions).** Inline policies
  are not. Updating a managed policy creates a new version; the previous
  version is preserved for rollback. Updating an inline policy replaces
  it with no history. For any policy that changes over time, use managed.

- **`iam:PassRole` is the most dangerous IAM action.** A principal with
  `iam:PassRole` on `Resource: "*"` can pass ANY role to a service
  (EC2, Lambda, CloudFormation), effectively escalating to that role's
  permissions. Always scope `iam:PassRole` to specific role ARNs, never
  `*`.

- **Service-linked roles cannot be created with `create-role`.** Roles
  like `AWSServiceRoleForECS`, `AWSServiceRoleForOrganizations`, and
  `AWSServiceRoleForSupport` are created automatically when the service
  is enabled. Attempting `create-role` with these names fails. The trust
  policy for service-linked roles uses a special
  `Service: <service>.amazonaws.com` principal that only the service can
  assume.

- **STS is regionally isolated but roles are global.** IAM roles are
  global resources (us-east-1 is the canonical region for IAM API calls).
  STS tokens are regional — `sts.us-east-1.amazonaws.com` and
  `sts.eu-west-1.amazonaws.com` are separate endpoints. Regional STS
  tokens reduce latency but the role's trust policy applies globally.

- **`aws:CalledVia` is a chain-aware condition key.** When a request
  passes through multiple services (e.g., CloudFormation → Lambda → IAM),
  `aws:CalledVia` records the chain. Use it to scope roles that should
  only be assumed when called via a specific service pipeline.

- **Session policies are evaluated at AssumeRole time.** When a caller
  passes a session policy via `--policy` (inline) or
  `--policy-arn` (managed ARN), the session's effective permissions are
  the INTERSECTION of the role's permission policy AND the session
  policy. This is a just-in-time scoping mechanism — the caller can never
  exceed the role's permissions, but can voluntarily narrow them.

- **`iam:CreateAccessKey` on `Resource: "*"` is a credential-creation
  vector.** A role with this permission can create access keys for ANY
  IAM user in the account, including admin users. This is a privilege-
  escalation path. Scope `iam:CreateAccessKey` to the caller's own user
  ARN only.

### Step 1: Principal type classification

Identify the principal type for the trust policy:

| Principal type | Trust policy Principal | Typical use |
|---|---|---|
| **AWS service** | `{"Service": "lambda.amazonaws.com"}` | Lambda function, ECS task, EC2 instance |
| **AWS account** | `{"AWS": "arn:aws:iam::<account>:root"}` | Cross-account access (the root means "any principal in that account") |
| **Specific role/user** | `{"AWS": "arn:aws:iam::<account>:role/<name>"}` | Cross-account role chaining |
| **Web Identity (OIDC)** | `{"Federated": "arn:aws:iam::<account>:oidc-provider/<provider>"}` | GitHub Actions, Cognito, Google |
| **SAML** | `{"Federated": "arn:aws:iam::<account>:saml-provider/<provider>"}` | Okta, Azure AD, ADFS |

**Anti-pattern:** NEVER use `Principal: {"AWS": "*"}` in a trust policy.
This lets any AWS principal in the world assume the role. The only
exception is a role that requires cross-account access from an unknown
set of accounts AND has a strict condition (e.g., `aws:SourceAccount`).
Even then, prefer listing specific accounts.

### Step 2: Trust policy design

The trust policy (AssumeRolePolicyDocument) defines who can assume the
role. Design principles:

1. **Specific principal.** Name the exact service, account, or provider.
   No wildcards.
2. **Condition keys to bind context.** Add `aws:SourceArn`,
   `aws:SourceAccount`, or service-specific conditions.
3. **ExternalId for cross-account.** Prevents confused-deputy attacks.
4. **MFA for human-accessible roles.** Require MFA for roles that humans
   assume interactively.

**Template — AWS service role (Lambda, scoped to one function):**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"Service": "lambda.amazonaws.com"},
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "aws:SourceAccount": "111111111111"
        },
        "ArnLike": {
          "aws:SourceArn": "arn:aws:lambda:us-east-1:111111111111:function:my-app-*"
        }
      }
    }
  ]
}
```

**Template — cross-account role with ExternalId:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::222222222222:root"},
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "sts:ExternalId": "unique-external-id-set-by-trusting-account"
        }
      }
    }
  ]
}
```

**Template — cross-account role with MFA:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::222222222222:role/devops-admin"},
      "Action": "sts:AssumeRole",
      "Condition": {
        "Bool": {"aws:MultiFactorAuthPresent": "true"},
        "NumericLessThan": {"aws:MultiFactorAuthAge": "3600"}
      }
    }
  ]
}
```

**Template — OIDC (GitHub Actions):**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::111111111111:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:my-org/my-repo:ref:refs/heads/main"
        }
      }
    }
  ]
}
```

**Template — SAML (Okta/Azure AD):**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::111111111111:saml-provider/okta-idp"
      },
      "Action": "sts:AssumeRoleWithSAML",
      "Condition": {
        "StringEquals": {
          "SAML:aud": "https://signin.aws.amazon.com/saml"
        }
      }
    }
  ]
}
```

### Step 3: Permission policy design

The permission policy defines what the role can do after assumption.
Design principles:

1. **Prefer managed policies over inline.** Managed policies are
   versioned (rollback support), reusable across roles, and have a 6:1
   inline-policy-to-managed-policy quota advantage.
2. **Least-privilege actions and resources.** Avoid `Action: "*"` and
   `Resource: "*"`. Scope to specific ARNs.
3. **AWS-managed vs customer-managed.** AWS-managed policies
   (`AmazonS3ReadOnlyAccess`, `AWSLambdaBasicExecutionRole`) are
   maintained by AWS but may be broader than needed. Customer-managed
   policies are precisely scoped but require maintenance. Use AWS-managed
   for commodity permissions (CloudWatch Logs), customer-managed for
   resource-specific access.

**Standard permission templates:**

| Template | Permissions | Use case |
|---|---|---|
| **read-only** | `s3:Get*`, `s3:List*`, `dynamodb:GetItem`, `dynamodb:Query`, `dynamodb:Scan` | Audit, reporting, data read |
| **deploy** | `cloudformation:*` (scoped), `s3:PutObject` (artifact bucket), `iam:PassRole` (specific roles), `ecs:*` (specific cluster) | CI/CD pipeline |
| **admin-delegated** | `*` on `*` (with permission boundary) | Break-glass, trusted admin |

**iam:PassRole scoping:**

```json
{
  "Effect": "Allow",
  "Action": "iam:PassRole",
  "Resource": [
    "arn:aws:iam::111111111111:role/ecs-task-execution",
    "arn:aws:iam::111111111111:role/ecs-task-app"
  ]
}
```

NEVER use `Resource: "*"` with `iam:PassRole` — it allows passing any
role, including admin roles, to any service.

### Step 4: Permission boundaries

A permission boundary sets the MAXIMUM permissions a role can have. The
effective permissions are the INTERSECTION of the permission policy and
the boundary.

**When to use permission boundaries:**
- **Delegation.** When delegating limited admin to a team or application
  owner. The team gets `AdministratorAccess` in their permission policy,
  but the boundary limits them to their own resources.
- **Compliance.** When a regulation requires that no role can exceed a
  defined scope (e.g., "no role can delete KMS keys").
- **Multi-tenant.** When multiple tenants share an account and each
  tenant's roles must be isolated.

**Permission boundary template (delegated admin, scoped to one VPC):**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "*",
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "ec2:Vpc": "arn:aws:ec2:us-east-1:111111111111:vpc/vpc-tenant-a"
        }
      }
    },
    {
      "Effect": "Deny",
      "Action": [
        "iam:CreateRole",
        "iam:DeleteRole",
        "iam:AttachRolePolicy",
        "iam:PutRolePolicy"
      ],
      "Resource": "*"
    }
  ]
}
```

**Deployment:**
```
aws iam put-role-permissions-boundary \
  --role-name <role> \
  --permissions-boundary arn:aws:iam::111111111111:policy/boundary-tenant-a
```

### Step 5: Condition keys

Condition keys bind the role's use to a specific context:

| Key | Scope | Use case |
|---|---|---|
| `aws:SourceArn` | Specific resource ARN | Bind Lambda role to one function |
| `aws:SourceAccount` | Specific account ID | Bind service role to owning account |
| `aws:SourceIp` | Caller IP CIDR | Restrict assume to corporate network (weak — bypassable via NAT) |
| `aws:SourceVpc` | VPC ID | Restrict to VPC endpoint origin (strong — set by infrastructure) |
| `aws:SourceVpce` | VPC endpoint ID | Restrict to specific endpoint (strongest network scope) |
| `aws:MultiFactorAuthPresent` | MFA status | Require MFA for human assume (Bool condition) |
| `aws:MultiFactorAuthAge` | Seconds since MFA | Force re-auth after N seconds |
| `aws:RequestedRegion` | AWS region | Restrict actions to specific regions |
| `aws:CalledVia` | Service chain | Restrict to CloudFormation-initiated calls |
| `aws:UserAgent` | Caller user-agent | Weak — easily forgeable |

**`aws:RequestedRegion` example (multi-region restriction):**
```json
"Condition": {
  "StringEqualsIgnoreCase": {
    "aws:RequestedRegion": ["us-east-1", "eu-west-1"]
  }
}
```

**`aws:CalledVia` example (CloudFormation-only):**
```json
"Condition": {
  "StringEquals": {
    "aws:CalledVia": ["cloudformation.amazonaws.com"]
  }
}
```

### Step 6: Maximum session duration tuning

| Role type | Recommended MaxSessionDuration | Rationale |
|---|---|---|
| AWS service (Lambda, ECS) | 3600 (1h, default) | Services auto-renew; duration irrelevant |
| EC2 instance profile | 3600 (1h) | Instance profile uses temporary creds, auto-renewed |
| Cross-account (service-to-service) | 3600 (1h) | Short-lived, auto-renewed by calling service |
| Cross-account (human, with MFA) | 3600-14400 (1-4h) | Limit credential lifetime; force re-auth |
| OIDC (GitHub Actions) | 3600 (1h) | CI/CD jobs are short; GitHub Actions max is 1h |
| SAML (human, with MFA) | 3600-14400 (1-4h) | Limit credential lifetime; force re-auth |
| Break-glass admin | 900 (15min) | Minimize exposure window for emergency access |

**Anti-pattern:** NEVER set MaxSessionDuration to 43200 (12h) for a
human-accessible role without MFA. Long-lived credentials without MFA
are the single most common vector for credential theft escalation.

### Step 7: MFA enforcement

MFA enforcement applies to the trust policy of roles that humans assume
interactively (cross-account, SAML). It does NOT apply to service roles.

**MFA trust policy condition:**
```json
"Condition": {
  "Bool": {"aws:MultiFactorAuthPresent": "true"},
  "NumericLessThan": {"aws:MultiFactorAuthAge": "3600"}
}
```

**Critical:** The `Bool` qualifier is MANDATORY. Without it, the
condition silently fails for all requests. The `aws:MultiFactorAuthAge`
condition forces re-authentication after 3600 seconds (1 hour).

### Step 8: Role chaining patterns

Role chaining is when a principal assumes Role-A, then uses Role-A's
credentials to assume Role-B. Common patterns:

| Pattern | Use case | Risk |
|---|---|---|
| **Linear chain** (A → B → C) | Multi-hop cross-account access | Each hop adds latency; max chain depth is 4 (STS limit) |
| **Hub-and-spoke** (audit → all accounts) | Centralized audit role | Audit role is high-value target; scope tightly |
| **Break-glass** (user → MFA-role → admin-role) | Emergency access | Two-hop requires MFA at first hop; admin at second |

**Anti-pattern:** NEVER create circular chains (A → B → A). STS detects
some loops but not all. Circular chains cause mysterious AssumeRole
failures with `AccessDenied` that is hard to diagnose.

**Deployment:** Role chaining does not require special IAM configuration.
The chained role's trust policy must allow the first role's ARN. No
additional IAM resource is needed.

### Step 9: Session policies

Session policies are inline or managed policies passed at AssumeRole
time. The session's effective permissions are the INTERSECTION of the
role's permission policy AND the session policy.

**Use cases:**
- **Just-in-time scoping.** A CI/CD role with broad permissions assumes
  a session scoped to only the resources being deployed in this run.
- **Multi-tenant.** A shared admin role assumes a session scoped to one
  tenant's resources.
- **Temporary read access.** A role with write permissions assumes a
  read-only session for a specific task.

**Deployment (AssumeRole with session policy):**
```
aws sts assume-role \
  --role-arn arn:aws:iam::111111111111:role/deploy-role \
  --role-session-name deploy-$(date +%s) \
  --policy '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":"ecs:UpdateService","Resource":"arn:aws:ecs:us-east-1:111111111111:service/prod-cluster/my-app"}]}'
```

**Critical:** Session policies can only NARROW permissions. A session
policy cannot grant permissions that the role's permission policy does
not allow.

### Step 10: Verification

Before deploying, verify the role's effective permissions:

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

## Output format (per role deployment plan)

```text
ROLE_SPEC: <name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
TRUST_POLICY:
  Principal: <service | account | federated>
  Action: sts:AssumeRole | AssumeRoleWithWebIdentity | AssumeRoleWithSAML
  Conditions: <list of condition keys>
  ExternalId: <yes/no>
  MFA: <required/not-required>
PERMISSIONS:
  Managed policies: <list>
  Inline policies: <list>
  Permission boundary: <arn or none>
  Effective scope: <intersection summary>
CHECKLIST:
  [x] Trust policy has specific principal (no wildcards)
  [x] Trust policy has condition keys (SourceArn/SourceAccount)
  [x] Permission policy is least-privilege (no Action: * on Resource: *)
  [x] iam:PassRole scoped to specific role ARNs
  [x] Permission boundary applied (for delegated/admin roles)
  [x] MaxSessionDuration tuned (not default 12h for human roles)
  [x] MFA enforced for human-accessible roles
  [x] No circular role chains
FINDINGS:
  - [INFO] ExternalId recommended for cross-account trust
  - [WARN] MaxSessionDuration is 12h — consider reducing for human access
DEPLOY_COMMANDS:
  <ordered list of aws iam create-role + put/attach-policy commands>
```

### Worked example — Lambda role scoped to one function

```text
ROLE_SPEC: my-app-lambda-role
VERDICT: READY_TO_DEPLOY
TRUST_POLICY:
  Principal: Service: lambda.amazonaws.com
  Action: sts:AssumeRole
  Conditions: aws:SourceAccount=111111111111, aws:SourceArn=arn:aws:lambda:us-east-1:111111111111:function:my-app-*
  ExternalId: no (service role)
  MFA: not required (service role)
PERMISSIONS:
  Managed policies: AWSLambdaBasicExecutionRole
  Inline policies: my-app-lambda-permissions (s3:GetObject on prod-data/*, dynamodb:PutItem on prod-table)
  Permission boundary: none
  Effective scope: CloudWatch Logs + S3 read + DynamoDB write (scoped)
CHECKLIST:
  [x] Trust policy has specific principal (lambda.amazonaws.com)
  [x] Trust policy has SourceAccount + SourceArn conditions (scoped to my-app-* functions)
  [x] Permission policy is least-privilege (specific S3 bucket + DynamoDB table)
  [x] No iam:PassRole (Lambda does not pass roles to other services)
  [x] No permission boundary needed (not delegated)
  [x] MaxSessionDuration: 3600 (default, service auto-renews)
  [x] No MFA (service role — MFA not applicable)
  [x] No role chaining
FINDINGS:
  - [INFO] SourceArn uses wildcard suffix (my-app-*) — consider tightening to exact function name
  - [INFO] AWSLambdaBasicExecutionRole grants CloudWatch Logs create/write — verify log group is scoped
DEPLOY_COMMANDS:
  1. aws iam create-role --role-name my-app-lambda-role --assume-role-policy-document file://trust-policy.json
  2. aws iam attach-role-policy --role-name my-app-lambda-role --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
  3. aws iam put-role-policy --role-name my-app-lambda-role --policy-name my-app-lambda-permissions --policy-document file://permissions.json
```

### Worked example — cross-account deploy role with ExternalId

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

## Edge-case handling

- **Service-linked role.** Cannot be created with `create-role`. The role
  is auto-created when the service is enabled (e.g., `ecs create-cluster`
  creates `AWSServiceRoleForECS`). Do not emit a `create-role` command
  for service-linked roles — emit a note that the service will create it.

- **Role with both MFA and ExternalId.** Valid for cross-account human
  access. The ExternalId is set by the trusting account; MFA is presented
  by the human. Both conditions must be met.

- **OIDC provider with multiple repos.** A single OIDC provider
  (`token.actions.githubusercontent.com`) can back multiple roles, each
  scoped to a different repo via the `sub` condition. Do not create
  multiple OIDC providers for multiple repos — one provider + multiple
  roles.

- **SAML provider with multiple IdPs.** Each SAML IdP (Okta, Azure AD)
  needs its own SAML provider in IAM. A role's trust policy references
  ONE SAML provider. For multi-IdP, create separate roles per IdP.

- **Role quota exceeded.** Default quota is 1000 roles per account. For
  large organizations, request a quota increase. Do NOT work around by
  reusing roles across services — this breaks least-privilege.

- **Inline policy size limit.** Inline policies are limited to 10,240
  characters (10KB). For larger policies, use managed policies (limited
  to 10,240 characters per version, but up to 5 versions).

- **Trust policy change does not affect existing sessions.** Updating a
  trust policy does NOT revoke existing assumed-role sessions. Existing
  sessions continue until they expire (MaxSessionDuration). To revoke
  immediately, revoke active sessions via `sts:RevokeSession` (requires
  the role to have a `RevokeOldSessions` permission).

- **`Principal: {"AWS": "arn:aws:iam::<account>:root"}` means ALL
  principals in that account.** The `:root` suffix does not mean "root
  user only" — it means "the account," which includes all users and
  roles in that account. This is a common misunderstanding.

## Anti-Patterns — NEVER

- NEVER use `Principal: {"AWS": "*"}` in a trust policy. This lets any
  AWS principal in the world assume the role. The only exception is a
  role with a strict `aws:SourceAccount` condition, and even then, prefer
  listing specific accounts. A wildcard principal trust policy is the
  single most dangerous IAM misconfiguration.

- NEVER use `Principal: {"AWS": "arn:aws:iam::<account>:root"}` thinking
  it means "root user only." The `:root` suffix means the ENTIRE
  ACCOUNT — all users and roles. If you want to restrict to the root
  user, you cannot do so via the trust policy alone — root user access
  cannot be scoped by IAM.

- NEVER create a service role without `aws:SourceArn` or
  `aws:SourceAccount` conditions. `Principal: {"Service":
  "lambda.amazonaws.com"}` means ANY Lambda function in the account can
  assume the role. Without `aws:SourceArn`, a role intended for one
  function is accessible by all functions — a lateral-movement vector.

- NEVER use `aws:MultiFactorAuthPresent` without the `Bool` qualifier.
  The condition `{"aws:MultiFactorAuthPresent": "true"}` (without
  `Bool`) silently evaluates to false for ALL requests — including those
  with MFA. The correct form is
  `{"Bool": {"aws:MultiFactorAuthPresent": "true"}}`.

- NEVER apply `aws:MultiFactorAuthPresent` to service roles. Services
  (Lambda, ECS, EC2) do not present MFA. A trust policy requiring MFA on
  a service principal silently breaks the role — the service cannot
  assume it.

- NEVER set `MaxSessionDuration` to 43200 (12 hours) for a human-
  accessible role without MFA. Long-lived credentials without MFA are
  the single most common vector for credential theft escalation. Set to
  3600-14400 (1-4 hours) with MFA.

- NEVER use `Resource: "*"` with `iam:PassRole`. This allows passing ANY
  role to any service, including admin roles. Always scope `iam:PassRole`
  to specific role ARNs. A role with `iam:PassRole` on `*` can escalate
  to admin by passing an admin role to an EC2 instance.

- NEVER use `Action: "*"` on `Resource: "*"` without a permission
  boundary. This is `AdministratorAccess`. It is acceptable ONLY for
  break-glass roles with MFA and a permission boundary. For any other
  role, scope actions and resources.

- NEVER prefer inline policies over managed policies for policies that
  change over time. Inline policies have no version history — updating
  one replaces it with no rollback. Managed policies support up to 5
  versions with rollback. Use managed for any policy with a change
  lifecycle.

- NEVER create a trust policy without `sts:AssumeRole` (or
  `AssumeRoleWithWebIdentity` / `AssumeRoleWithSAML`). A trust policy
  without the assume action grants nothing — the role cannot be assumed.
  This is a silent failure: the role exists but is unusable.

- NEVER create circular role chains (A → B → A). STS detects some loops
  but not all. Circular chains cause mysterious `AccessDenied` failures
  on AssumeRole that are extremely hard to diagnose.

- NEVER trust `aws:SourceIp` as a strong condition. SourceIp is bypassable
  via NAT Gateway, proxy, VPN, or any egress-controlling service. Use
  `aws:SourceVpc` or `aws:SourceVpce` for network-scoped conditions —
  these are set by AWS infrastructure and cannot be forged by the caller.

- NEVER assume `Principal: {"AWS": "<account>:root"` restricts to the
  root user. It restricts to the account (all principals). There is no
  IAM mechanism to allow only the root user — root user actions are
  controlled by the account-level setting, not IAM policies.

- NEVER forget that permission boundaries are a MAXIMUM, not a grant. A
  permission boundary that allows `s3:*` does NOT grant S3 access — it
  limits the role to S3 access IF the permission policy also grants it.
  The effective permissions are the intersection.

- NEVER use `iam:CreateAccessKey` with `Resource: "*"`. A role with this
  permission can create access keys for ANY IAM user, including admin
  users. Scope to the caller's own user ARN:
  `arn:aws:iam::<account>:user/${aws:username}`.

- NEVER deploy a role without running `simulate-principal-policy` first.
  The IAM Policy Simulator reveals the effective permissions of a role
  before deployment. Skipping simulation is the most common cause of
  "the role can do more than I intended" incidents.

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

## Expert knowledge: non-obvious IAM behaviors

- **STS regional endpoints reduce latency but the role is global.** Using
  `sts.us-west-2.amazonaws.com` instead of the global `sts.amazonaws.com`
  reduces AssumeRole latency for workloads in us-west-2. The role's trust
  policy applies globally — the regional endpoint just issues the token
  faster.

- **`AssumeRole` has a max chain depth of 4.** A → B → C → D is the max.
  The 5th hop fails with `AccessDenied`. Plan role chains to stay within
  3 hops for safety.

- **`AssumeRoleWithWebIdentity` does NOT support session tags by default.**
  To pass tags from the OIDC token to the session, use `--transitive-tag-keys`
  in the AssumeRole call and configure the IdP to include the tags in the
  token.

- **Service-linked roles have a fixed trust policy.** You cannot modify
  the trust policy of a service-linked role. The service owns it. If you
  need to scope a service's access differently, create a custom role
  instead of relying on the service-linked role.

- **`iam:PassRole` is evaluated at resource creation, not at runtime.**
  When you create an EC2 instance with an instance profile, `iam:PassRole`
  is checked ONCE at `RunInstances`. If the passer loses the permission
  later, the running instance is unaffected — it keeps the role.

- **Permission boundary + permission policy = intersection.** If the
  permission policy allows `s3:*` and the boundary allows only `s3:Get*`,
  the effective permission is `s3:Get*`. Neither policy alone determines
  the effective scope — always compute the intersection.

- **`aws:SourceArn` is set by the AWS service, not the caller.** When
  Lambda assumes a role, `aws:SourceArn` is set to the function's ARN
  by the Lambda service. The caller (the function code) cannot forge
  this value. This is why `aws:SourceArn` is a strong condition.

- **Cross-account AssumeRole is intersection-based.** Both the trusting
  account's role permission policy AND the trusted account's caller IAM
  policy must allow the action. This is the same model as S3 cross-
  account access. Same-account access is union-based (either suffices).

- **Session policies cannot exceed the role's permissions.** A session
  policy that grants `s3:*` when the role only has `s3:Get*` results in
  `s3:Get*` (intersection). The session policy can only NARROW, never
  widen.

- **`sts:GetCallerIdentity` works without any permissions.** Any
  principal can call `sts:GetCallerIdentity` — it requires no IAM
  permissions. This is why it is the standard "am I assuming the right
  role?" check.

- **Role tags support ABAC.** Attribute-Based Access Control uses role
  tags (e.g., `Environment=prod`) in condition keys
  (`aws:PrincipalTag/Environment`). This enables scalable permission
  management without listing every resource.

## Deep reference: IAM authorization internals

### AssumeRole evaluation pipeline

```
Caller → STS:AssumeRole → Evaluate trust policy:
  1. Principal matches?
  2. Action is sts:AssumeRole (or WebIdentity/SAML variant)?
  3. All conditions met (ExternalId, MFA, SourceArn)?
→ If all pass: issue temporary credentials with MaxSessionDuration
→ Effective permissions = role permission policy ∩ session policy (if provided) ∩ permission boundary (if set)
```

### Trust policy vs permission policy scope

| Dimension | Trust policy | Permission policy |
|---|---|---|
| Attached to | The role (as AssumeRolePolicyDocument) | The role (as managed or inline) |
| Controls | WHO can assume the role | WHAT the role can do after assumption |
| Evaluated | At AssumeRole time | At every API call after assumption |
| Principal element | Required (Service, AWS, Federated) | Not used (the role IS the principal) |
| Condition keys | aws:SourceArn, aws:SourceAccount, sts:ExternalId, aws:MultiFactorAuthPresent | aws:SourceIp, aws:SourceVpc, aws:RequestedRegion, aws:CalledVia |
| Version history | No (replace only) | Managed: up to 5 versions. Inline: no. |

### Permission boundary intersection model

```
Effective permissions = PermissionPolicy ∩ PermissionBoundary ∩ SessionPolicy
```

If any of the three does not allow an action, the action is denied.
Permission boundaries and session policies can only NARROW the permission
policy, never widen it.

## Recent AWS features (2024-2026)

- **IAM Session Tagging (2024-2025):** AssumeRole now supports passing
  session tags that propagate to downstream STS calls. Use for ABAC
  multi-tenant isolation without creating per-tenant roles.

- **IAM Access Analyzer policy generation (2024-2025):** Generates least-
  privilege policies based on CloudTrail activity. Deployers should run
  generated policies through the simulator before attaching — the
  generator may over-grant based on noisy CloudTrail data.

- **STS regional endpoints in all regions (2024):** All regions now have
  STS regional endpoints. Use regional endpoints for lower-latency
  AssumeRole in geographically distributed workloads.

- **IAM role last-accessed (2024-2025):** IAM now shows when each role
  was last used. Use to identify and remove unused roles — a key least-
  privilege hygiene practice.

- **PassRole with conditions (2025-2026):** Enhanced `iam:PassRole`
  condition keys allow scoping which services a role can be passed to.
  Use `iam:PassedToService` to prevent passing admin roles to unintended
  services.

## Domain

AWS CloudOps / IAM Security & Identity Management.

## AWS documentation

- **IAM User Guide** — https://docs.aws.amazon.com/IAM/latest/UserGuide/
- **IAM Roles** — https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles.html
- **IAM Trust Policies** — https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_terms-and-concepts.html
- **IAM Permission Boundaries** — https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_boundaries.html
- **IAM Condition Keys** — https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_condition-keys.html
- **STS API Reference** — https://docs.aws.amazon.com/STS/latest/APIReference/
- **IAM Policy Simulator** — https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_testing-policies.html
- **AWS CLI IAM Reference** — https://docs.aws.amazon.com/cli/latest/reference/iam/
- **OIDC for GitHub Actions** — https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers_create_oidc.html
