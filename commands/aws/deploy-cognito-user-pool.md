---
description: Provision a production-grade Amazon Cognito user pool with secure defaults — TOTP MFA, ENFORCED ASF, OAuth code flow + PKCE, SAML/OIDC federation, Lambda triggers, resource servers, and hosted UI branding. Emits a READY_TO_DEPLOY checklist with verification commands and blocks implicit/admin auth flows.
nl_triggers:
  - "create cognito user pool"
  - "provision user pool"
  - "deploy cognito"
  - "OAuth app client"
  - "code flow with PKCE"
  - "client credentials grant"
  - "SAML federation cognito"
  - "OIDC identity provider"
  - "social login cognito"
  - "hosted UI"
  - "cognito branding"
  - "managed login branding"
  - "pre-signup trigger"
  - "post-confirmation trigger"
  - "custom message trigger"
  - "pre-token-generation trigger"
  - "resource server custom scopes"
  - "user pool groups"
  - "custom domain cognito"
  - "advanced security features"
  - "cognito-idp create-user-pool"
  - "TOTP MFA pool"
  - "SMS MFA pool"
routes_to: cognito-user-pool-deployer
---

# /aws:deploy-cognito-user-pool

Activate the `cognito-user-pool-deployer` skill and provision a
production-grade Amazon Cognito user pool with secure identity defaults.

## What it does

The skill walks a pre-check gate and emits a READY_TO_DEPLOY checklist:

1. Pool name uniqueness (no collision with existing pools)
2. Attribute schema (custom attributes use `custom:` prefix, immutable)
3. Password policy (>= 12 chars, all four character classes)
4. MFA configuration (TOTP preferred; SMS requires SNS caller role)
5. App client auth flows (SRP-only — ADMIN and USER_PASSWORD blocked)
6. OAuth flows (code+PKCE default — implicit blocked at pre-check)
7. PreventUserExistenceErrors (ENABLED — blocks user enumeration)
8. Advanced Security Features (ENFORCED — adaptive threat protection)
9. Deletion protection (ACTIVE — accidental deletion prevention)
10. Token validity (explicit units — AccessToken/IdToken <= 1h,
    RefreshToken <= 3650d)
11. SAML identity provider (metadata URL/document resolves)
12. OIDC identity provider (issuer URL + endpoints resolve)
13. Lambda triggers (ARNs resolve + pool principal has invoke permission)
14. Resource server + custom scopes (M2M client-credentials flow)
15. User pool groups (RBAC via `cognito:groups` claim or IAM role vending)
16. Custom domain (ACM cert in us-east-1, status ISSUED)
17. Managed Login Branding (logo, colors, font per app client)

## When to use

- You need to create a new Cognito user pool with production defaults.
- You are configuring an OAuth app client (web, mobile, or M2M).
- You are federating with a SAML or OIDC identity provider.
- You want to enable Cognito Advanced Security Features (ENFORCED mode).
- You need to wire Lambda triggers (pre-signup, post-confirmation,
  custom message, pre-token-generation).
- You need a resource server with custom scopes for client-credentials.
- You want to register a custom domain for the hosted UI.
- You want managed login branding per app client.

## How to invoke

### Slash command

```
/aws:deploy-cognito-user-pool
```

Then provide: pool name, region, attribute schema, password policy,
MFA configuration (TOTP/SMS/both), app client config (OAuth flows,
scopes, callbacks), identity providers, Lambda triggers, resource
servers, groups, and domain type (Cognito-managed or custom).

### Natural language

Any of these routes to the same skill:

- "create a Cognito user pool for my web app"
- "federate Cognito with Okta SAML"
- "configure OAuth client credentials for my API"
- "enable Advanced Security Features on my pool"
- "wire pre-token-generation Lambda trigger"
- "set up a custom domain for hosted UI"

### CLI routing

```bash
node cli/bin/cli.js route "create a cognito user pool"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create or extend
Cognito user pools. The output checklist feeds into verification
pipelines and the `cognito-idp-user-pool-auditor` skill for post-deploy
security auditing.

## Example

```
You: /aws:deploy-cognito-user-pool

     Create a production user pool "prod-users" in us-east-1 with email
     login, TOTP MFA ON, ENFORCED ASF, and a prod-web-spa app client
     using OAuth code flow with PKCE. Account: 111111111111.

Skill:
  POOL: prod-users
  VERDICT: READY_TO_DEPLOY
  TARGET: prod-users
  PRE_CHECKS:
    [PASS] Pool name unique (no collision in list-user-pools)
    [PASS] Password policy: 16 chars, all classes, 1-day temp
    [PASS] MFA: TOTP-only, no SMS role required
    [PASS] DeletionProtection: ACTIVE
    [PASS] AdvancedSecurityMode: ENFORCED
    [PASS] IAM principal holds cognito-idp:CreateUserPool
  MFA: TOTP-only (config: ON)
  OAUTH_FLOWS: code
  ASF: ENFORCED
```

## References

- Skill definition: `skills/cognito-user-pool-deployer/SKILL.md`
- Pool config & security defaults: `skills/cognito-user-pool-deployer/references/pool-config-and-security-defaults.md`
- Identity providers & triggers: `skills/cognito-user-pool-deployer/references/identity-providers-and-triggers.md`
- Eval suite: `skills/cognito-user-pool-deployer/evals/evals.json`
