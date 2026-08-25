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

→ Extended Mindset rationale moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).


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

→ Live-account pre-flight command listing moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).


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

→ Step 0 expert-knowledge deep dive moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).


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

→ Secondary trust policy templates (MFA / OIDC / SAML) moved verbatim to [references/trust-policy-templates.md](references/trust-policy-templates.md).


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

→ iam:PassRole scoping template moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).

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

→ Permission boundary template + deployment commands moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).


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

→ aws:RequestedRegion / aws:CalledVia condition examples moved verbatim to [references/condition-keys-guide.md](references/condition-keys-guide.md).


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

→ Role-chaining deployment note moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).

### Step 9: Session policies

Session policies are inline or managed policies passed at AssumeRole
time. The session's effective permissions are the INTERSECTION of the
role's permission policy AND the session policy.

→ Session-policy use cases + AssumeRole deployment moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).


**Critical:** Session policies can only NARROW permissions. A session
policy cannot grant permissions that the role's permission policy does
not allow.

### Step 10: Verification

Before deploying, verify the role's effective permissions:

→ Deployment verification command listing moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).


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

→ Secondary worked example moved verbatim to [references/worked-examples.md](references/worked-examples.md).


## Edge-case handling

→ Edge-case catalog moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).


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

→ Pre-flight safety checks moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).


## Expert knowledge: non-obvious IAM behaviors

→ Expert-knowledge deep dive moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).


## Deep reference: IAM authorization internals

→ IAM authorization internals deep reference moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).


## Recent AWS features (2024-2026)

→ Recent AWS features catalog moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).


## References (load on demand)

- [references/worked-examples.md](references/worked-examples.md) — secondary worked example: cross-account deploy role with ExternalId.
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — live-account pre-flight checks; Step-10 verification commands; pre-flight safety checks.
- [references/advanced-patterns.md](references/advanced-patterns.md) — extended Mindset rationale; Step-0 expert knowledge; permission-boundary template; session-policy patterns; edge cases; expert knowledge; authorization internals; recent AWS features.
- [references/trust-policy-templates.md](references/trust-policy-templates.md) — extended: MFA, OIDC, SAML trust policy templates.
- [references/condition-keys-guide.md](references/condition-keys-guide.md) — extended: aws:RequestedRegion and aws:CalledVia JSON examples.

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
