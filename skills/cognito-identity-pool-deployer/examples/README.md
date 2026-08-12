# End-to-End Example: Cognito Identity Pool Deployment

A walkthrough showing how to use the `cognito-identity-pool-deployer`
skill from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning a Cognito Identity Pool for an application that
federates from a Cognito User Pool with rules-based role mapping and
guest access. The setup needs:

- Identity pool: app-identity-pool
- Provider: Cognito User Pool us-east-1_AbCdEf123 (client: abc123def456)
- Guest access: enabled
- Role mapping: rules-based (admins → AdminRole, readers → ReaderRole)
- Default authenticated role: AppAuthenticatedRole
- Unauthenticated role: AppUnauthenticatedRole
- Account: 123456789012, Region: us-east-1

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-cognito-identity-pool
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create a Cognito Identity Pool federating from User Pool
      us-east-1_AbCdEf123. Guest access enabled. Rules-based
      mapping: admins get AdminRole, readers get ReaderRole.
      Default auth role: AppAuthenticatedRole."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create cognito identity pool"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
COGNITO_IDENTITY_POOL: app-identity-pool (us-east-1:abcdef-1234)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Identity pool: app-identity-pool (us-east-1:abcdef-1234)
  [✓] Providers: cognito-idp.us-east-1.amazonaws.com/us-east-1_AbCdEf123 (client: abc123def456)
  [✓] Authenticated role: arn:aws:iam::123456789012:role/AppAuthenticatedRole
  [✓] Unauthenticated role: arn:aws:iam::123456789012:role/AppUnauthenticatedRole
  [✓] Role mapping: Rules-based (2 rules: admins → AdminRole, readers → ReaderRole)
  [✓] ServerSideTokenCheck: true
  [✓] Authflow: GetId + GetCredentialsForIdentity
  [✓] Tags: Environment=production, Application=app
VERIFICATION_COMMANDS:
  aws cognito-identity describe-identity-pool --identity-pool-id us-east-1:abcdef-1234
  aws cognito-identity get-identity-pool-roles --identity-pool-id us-east-1:abcdef-1234
  aws iam get-role --role-name AppAuthenticatedRole
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Create the identity pool with User Pool provider
POOL_ID=$(aws cognito-identity create-identity-pool \
  --identity-pool-name "app-identity-pool" \
  --allow-unauthenticated-identities \
  --cognito-identity-providers \
    ProviderName=cognito-idp.us-east-1.amazonaws.com/us-east-1_AbCdEf123,ClientId=abc123def456,ServerSideTokenCheck=true \
  --query 'IdentityPoolId' --output text)

# Step 2: Set roles with rules-based mapping
aws cognito-identity set-identity-pool-roles \
  --identity-pool-id "$POOL_ID" \
  --roles authenticated=arn:aws:iam::123456789012:role/AppAuthenticatedRole,unauthenticated=arn:aws:iam::123456789012:role/AppUnauthenticatedRole \
  --role-mappings '{
    "cognito-idp.us-east-1.amazonaws.com/us-east-1_AbCdEf123": {
      "Type": "Rules",
      "AmbiguousRoleResolution": "AuthenticatedRole",
      "RulesConfiguration": {
        "Rules": [
          {"Claim":"cognito:groups","MatchType":"Contains","Value":"admins","RoleARN":"arn:aws:iam::123456789012:role/AdminRole"},
          {"Claim":"cognito:groups","MatchType":"Contains","Value":"readers","RoleARN":"arn:aws:iam::123456789012:role/ReaderRole"}
        ]
      }
    }
  }'
```

---

## Step 4 — Post-deployment verification

```bash
# Verify pool configuration
aws cognito-identity describe-identity-pool \
  --identity-pool-id "$POOL_ID"

# Verify role mapping
aws cognito-identity get-identity-pool-roles \
  --identity-pool-id "$POOL_ID"

# Test authflow (requires a valid User Pool ID token)
aws cognito-identity get-id \
  --identity-pool-id "$POOL_ID" \
  --logins '{"cognito-idp.us-east-1.amazonaws.com/us-east-1_AbCdEf123":"<id-token>"}'
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Role mapping | Token-based (one role for all) | Rules-based with JWT claim evaluation | Different user groups need different IAM permissions |
| Unauthenticated role | Skipped | Minimal role with correct trust policy | Guest users need a role if guest access is enabled |
| Trust policy | Missing aud/amr conditions | cognito-identity.amazonaws.com:aud + amr | Without conditions, any pool can assume the role |
| ServerSideTokenCheck | Disabled | Enabled (true) | Prevents forged token exchange |
| AmbiguousRoleResolution | Not set | AuthenticatedRole or Deny | Determines behavior when no rule matches |

---

## Related artifacts

- **Skill definition:** `skills/cognito-identity-pool-deployer/SKILL.md`
- **Role mapping guide:** `skills/cognito-identity-pool-deployer/references/role-mapping-and-jwt.md`
- **Providers guide:** `skills/cognito-identity-pool-deployer/references/providers-and-trust.md`
- **Slash command:** `commands/aws/deploy-cognito-identity-pool.md`
- **Eval suite:** `skills/cognito-identity-pool-deployer/evals/evals.json`
- **Legacy test cases:** `skills/cognito-identity-pool-deployer/eval/test-cases.yaml`
