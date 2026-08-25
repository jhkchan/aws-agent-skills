# IAM Role Deployer — advanced patterns (moved verbatim from SKILL.md)

> Progressive-disclosure split: this content was moved verbatim from SKILL.md; nothing was rewritten.

## Mindset — extended rationale (three facts)

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

## Step 0: Expert knowledge — non-obvious IAM behaviors that change the plan

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

## Permission boundary template — delegated admin scoped to one VPC

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

## Session policy use cases and deployment

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

## iam:PassRole scoping template (moved from SKILL.md)

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

## Role chaining — deployment note (moved from SKILL.md)

**Deployment:** Role chaining does not require special IAM configuration.
The chained role's trust policy must allow the first role's ARN. No
additional IAM resource is needed.
