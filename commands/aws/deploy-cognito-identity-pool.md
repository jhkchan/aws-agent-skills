---
description: Provision an Amazon Cognito Identity Pool with production-grade defaults (federated identity providers, authenticated/unauthenticated roles, rules-based role mapping, principal tag ABAC, SAML/OIDC federation, cross-account roles). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "cognito identity pool"
  - "federated identity"
  - "identity pool"
  - "cognito role mapping"
  - "get credentials for identity"
  - "cognito unauthenticated role"
  - "principal tags cognito"
  - "saml federation cognito"
  - "cognito guest access"
  - "rules-based role mapping"
routes_to: cognito-identity-pool-deployer
---

# /aws:deploy-cognito-identity-pool

Activate the `cognito-identity-pool-deployer` skill and provision an
Amazon Cognito Identity Pool with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Identity pool vs user pool distinction (credentials vs auth)
2. Identity providers (User Pool, social, SAML, OIDC)
3. Authenticated and unauthenticated roles (trust policy)
4. Role mapping (token-based vs rules-based)
5. Principal tag attribute mapping (ABAC)
6. SAML provider trust policy
7. Authflow: GetId + GetCredentialsForIdentity
8. Access control via groups and JWT claims
9. Cross-account role assumption
10. Recent features (principal tag passthrough, OIDC enhancements)

## When to use

- You need to create a Cognito Identity Pool for federated access.
- You need to configure identity providers for the pool.
- You need rules-based role mapping for per-user IAM roles.
- You need guest (unauthenticated) access with a minimal role.
- You need SAML or OIDC federation for enterprise SSO.
- You need principal tag mapping for ABAC.

## When NOT to use

- **Cognito User Pools** — use user-pool skills for user directory
  and authentication.
- **IAM Identity Center** — use identity-center skills for AWS SSO.
- **STS federation directly** — use STS skills for role chaining.

## How to invoke

### Slash command

```
/aws:deploy-cognito-identity-pool
```

Then provide: identity pool name, provider details (type, client ID),
authenticated/unauthenticated roles, role mapping strategy, guest
access decision, SAML/OIDC provider info (if applicable), tags.

### Natural language

Any of these routes to the same skill:

- "create a cognito identity pool"
- "set up federated identity for my app"
- "configure cognito role mapping"
- "enable guest access in cognito identity pool"
- "configure SAML federation with cognito"

### CLI routing

```bash
node cli/bin/cli.js route "create cognito identity pool"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create Cognito
identity pools for federated AWS access. The output checklist feeds
into verification pipelines and downstream audit skills.

## Example

```
You: /aws:deploy-cognito-identity-pool

     Create a Cognito Identity Pool. Federate from User Pool
     us-east-1_AbCdEf123. Guest access. Rules-based mapping:
     admins → AdminRole, readers → ReaderRole.

Skill:
  COGNITO_IDENTITY_POOL: app-identity-pool
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Providers: cognito-idp.us-east-1.amazonaws.com/us-east-1_AbCdEf123
    [✓] Authenticated role: AppAuthenticatedRole
    [✓] Unauthenticated role: AppUnauthenticatedRole
    [✓] Role mapping: Rules-based (admins → AdminRole, readers → ReaderRole)
    [✓] ServerSideTokenCheck: true
  VERIFICATION_COMMANDS:
    aws cognito-identity get-identity-pool-roles --identity-pool-id <pool-id>
```

## References

- Skill definition: `skills/cognito-identity-pool-deployer/SKILL.md`
- Role mapping guide: `skills/cognito-identity-pool-deployer/references/role-mapping-and-jwt.md`
- Providers guide: `skills/cognito-identity-pool-deployer/references/providers-and-trust.md`
- Eval suite: `skills/cognito-identity-pool-deployer/evals/evals.json`
