# Advanced Patterns (load on demand) — Cognito User Pool Deployer

Step-0 expert Cognito behaviors and 2024-2026 feature changes, moved verbatim from SKILL.md. Load when a plan hinges on non-obvious pool behavior.


---

## Step 0: Expert knowledge — non-obvious Cognito behaviors (moved from SKILL.md)

These behaviors are easy to misjudge without operational Cognito
experience. Each changes a plan if ignored:

- **Schema is immutable after pool creation.** The `Schema` array in
  `create-user-pool` can be set only once. To add a new attribute to an
  existing pool, you must create a new pool and migrate users. Always
  over-specify attributes at creation.

- **`RequiredAttributes` and `Schema` are independent.** An attribute
  listed in `RequiredAttributes` but missing from `Schema` will be
  auto-added by Cognito, but explicitly declaring in both is safer.
  Custom attributes (`custom:companyId`) must be declared in `Schema`
  with type `String`, `Number`, or `DateTime`.

- **`MfaConfiguration` values: OFF, ON, OPTIONAL.** `ON` requires every
  user to enroll. `OPTIONAL` (newer; also surfaced as `ENABLED`) lets
  users opt in. Prefer `ON` with TOTP only — SMS requires an SNS caller
  role and incurs per-message cost.

- **App client `ExplicitAuthFlows` controls the credential path.**
  `ALLOW_USER_SRP_AUTH` + `ALLOW_REFRESH_TOKEN_AUTH` is the secure
  baseline. `ALLOW_USER_PASSWORD_AUTH` sends the password to the client
  SDK (acceptable only for trusted server-side clients).
  `ALLOW_ADMIN_USER_PASSWORD_AUTH` enables admin password auth — almost
  always a security red flag.

- **OAuth `AllowedOAuthFlows`: code is the only safe grant.** `code`
  with PKCE keeps tokens off the URL fragment.
  `implicit` leaks tokens via the URL fragment — block it. The
  `client-credentials` grant is for machine-to-machine and requires a
  `GenerateClientSecret: true` app client plus a resource server with
  custom scopes.

- **`PreventUserExistenceErrors: ENABLED` (default).** Returns generic
  auth errors regardless of whether the user exists — blocks user
  enumeration. `LEGACY` returns distinct errors for "user not found"
  vs "wrong password" and is blocked by the skill.

- **`UserPoolAddOns.AdvancedSecurityMode`: ENFORCED preferred.** ASF
  detects compromised credentials, impossible travel, and account
  takeover. `AUDIT` mode logs but does not block; `ENFORCED` blocks
  at runtime. Always emit `ENFORCED` for production pools.

- **DeletionProtection defaults to ACTIVE on new pools.** Set
  `DeletionProtection: INACTIVE` only when intentionally destroying.
  Never set INACTIVE for production deploys.

- **Lambda triggers are ARNs in `LambdaConfig`.** The pool needs
  `lambda:InvokeFunction` permission via resource-based policy on each
  function. Cognito does not auto-grant this — missing permission causes
  triggers to silently no-op.

- **Custom domain requires ACM cert in us-east-1.** Always. The cert
  subject must match the custom domain exactly. Wildcard certs work
  for subdomains.

- **Hosted UI branding (2024-2026).** Newer managed branding via
  `cognito-idp:CreateManagedLoginBranding` lets you customize the
  hosted UI per app client (logo, background, colors, font). Legacy
  `UISettings` (CSS customization) is being deprecated for managed
  branding.

- **Resource servers define custom scopes.** A resource server with
  identifier `https://api.example.com` and scope `products.read` is
  requested as `https://api.example.com/products.read` in OAuth scope
  negotiation. Mismatched identifiers are the #1 cause of "invalid
  scope" errors in client-credentials flows.

- **User pool groups carry IAM roles.** A group with `Precedence: 1`
  and `RoleArn` set can issue credentials via the identity pool
  (classic) flow. Pure user-pool JWTs include `cognito:groups` as a
  claim — your app enforces authorization from there.

- **Token revocation requires `EnableTokenRevocation: true`.** New
  app clients default to true. Without it, refresh tokens remain
  valid until expiry even after sign-out. Always set true.

- **`AccessTokenValidity` and `IdTokenValidity` use hours units.** A
  value of `5` means 5 hours, not 5 minutes. Cognito also accepts
  `TokenValidityUnits` (Hours/Minutes/Days) explicitly — set this to
  avoid off-by-60 bugs.

## Recent AWS features (2024-2026) (moved from SKILL.md)

- **Cognito Managed Login Branding (2024-2025):** the new managed
  branding API (`create-managed-login-branding`) lets you customize the
  hosted UI per app client — logo, background, primary color, fonts,
  dark/light mode variants. Replaces the legacy `UISettings` CSS-based
  customization which is being deprecated.
- **Advanced Security Features ENFORCED mode improvements (2024-2025):**
  ASF ENFORCED now blocks risky sign-ins (impossible travel, leaked
  password) and exposes risk events to CloudWatch. Cheaper to run and
  no longer requires per-user pricing on most tiers.
- **Token revocation default (2024):** new app clients default to
  `EnableTokenRevocation: true`. Older pools created before 2024 still
  need explicit enablement.
- **`OPTIONAL` MFA configuration (2024-2025):** introduced as the
  recommended middle ground between OFF and ON. Users opt in to MFA
  but the pool advertises both factors. Equivalent to the legacy
  `ENABLED` value with clearer semantics.
- **Cognito user pool groups IAM role vending (2024):** groups with
  `RoleArn` set can issue AWS credentials via the identity pool flow.
  The user pool JWT also includes `cognito:groups` as a claim for
  application-layer RBAC.
- **Hosted UI custom domain alias for app clients (2024-2025):** a
  single user pool can host multiple custom domains, one per app
  client, enabling white-label B2B portals.
- **Cognito Managed Login Branding asset API (2025):** programmatic
  upload of logo images via `CreateManagedLoginBranding` assets —
  previously console-only.
