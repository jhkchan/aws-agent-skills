# End-to-End Example: CodeArtifact Domain Deployment

A walkthrough showing how to use the `codeartifact-domain-deployer`
skill from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning a CodeArtifact domain with an npm repository, an
internal upstream, and an external connection to npmjs.com. The domain
needs:

- Domain: my-domain (owner account 123456789012)
- Repository: my-team-packages (format: npm)
- Upstream cascade: shared-team-packages (internal) then npmjs (external)
- KMS encryption: customer-managed key
- Cross-account: read access for consumer account 999999999999
- Tags: Environment=production, Team=platform

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-codeartifact-domain
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create a CodeArtifact domain called my-domain with an npm
      repository, internal upstream, and npmjs external connection.
      Use CMK encryption. Grant read access to account 999999999999."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create a codeartifact domain"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
CODEARTIFACT_DOMAIN: my-domain (123456789012)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Domain: my-domain — encryption: CMK arn:aws:kms:us-east-1:123456789012:key/abcd1234
  [✓] Repository: my-team-packages (format: npm)
  [✓] Upstream cascade: my-team-packages → shared-team-packages → ext:npmjs
  [✓] External connection: npmjs (domain-scoped)
  [✓] Authorization token: aws codeartifact login (12-hour expiry — CI refresh required)
  [✓] Package ingest: npm publish — immutability enforced
  [✓] Cross-account repository policy: 999999999999 (read)
  [✓] KMS encryption: CMK — immutable at domain creation
  [✓] Package immutability: enforced (published versions cannot be overwritten)
  [✓] CloudWatch metrics: DownloadPackageVersion, PublishPackageVersion
  [✓] Tags: Environment=production, Team=platform
VERIFICATION_COMMANDS:
  aws codeartifact describe-domain --domain my-domain --region us-east-1
  aws codeartifact describe-repository --domain my-domain --repository my-team-packages --region us-east-1
  aws codeartifact list-repositories-in-domain --domain my-domain --region us-east-1
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Create the domain with CMK encryption
aws codeartifact create-domain \
  --domain my-domain \
  --encryption-key arn:aws:kms:us-east-1:123456789012:key/abcd1234-ef56-7890-abcd-ef1234567890 \
  --region us-east-1

# Step 2: Create the npm repository
aws codeartifact create-repository \
  --domain my-domain \
  --repository my-team-packages \
  --description "Internal npm packages for my team" \
  --region us-east-1

# Step 3: Configure upstream cascade (internal FIRST, external LAST)
aws codeartifact update-repository \
  --domain my-domain \
  --repository my-team-packages \
  --upstreams repository=shared-team-packages \
  --upstreams external-connection=npmjs \
  --region us-east-1

# Step 4: Set cross-account repository policy
aws codeartifact put-repository-permissions-policy \
  --domain my-domain \
  --repository my-team-packages \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": { "AWS": "arn:aws:iam::999999999999:root" },
        "Action": [
          "codeartifact:ReadFromRepository",
          "codeartifact:GetAuthorizationToken",
          "codeartifact:GetRepositoryEndpoint"
        ],
        "Resource": "*"
      }
    ]
  }' \
  --region us-east-1

# Step 5: Configure auth token (npm login — 12-hour expiry)
aws codeartifact login \
  --tool npm \
  --domain my-domain \
  --domain-owner 123456789012 \
  --repository my-team-packages \
  --region us-east-1

# Step 6: Publish a package
cd my-package/
npm publish
```

---

## Step 4 — Post-deployment verification

```bash
# Verify domain exists with CMK
aws codeartifact describe-domain \
  --domain my-domain \
  --query 'domain.{Name:name,EncryptionKey:encryptionKey}' \
  --region us-east-1

# Verify repository and upstream configuration
aws codeartifact describe-repository \
  --domain my-domain \
  --repository my-team-packages \
  --query 'repository.{Name:name,Upstreams:upstreams}' \
  --region us-east-1

# Verify cross-account policy
aws codeartifact get-repository-permissions-policy \
  --domain my-domain \
  --repository my-team-packages \
  --region us-east-1

# Consumer account login (uses DOMAIN OWNER account ID)
aws codeartifact login \
  --tool npm \
  --domain my-domain \
  --domain-owner 123456789012 \
  --repository my-team-packages \
  --region us-east-1
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Upstream cascade | External before internal | Internal first, external last | Supply-chain security: prevents dependency confusion attacks |
| Auth token | Cached permanently | 12-hour expiry noted, CI refresh required | Token expires; cached tokens cause silent CI failures |
| KMS encryption | Default key, change later | CMK at creation, immutability noted | Encryption key is immutable; cannot change post-creation |
| Cross-account | Login without policy | Repository policy + domain owner ID in login | Consumer needs explicit policy grant + correct domain-owner ID |
| VPC endpoint | Single endpoint | Both API and repositories endpoints | Two endpoints needed; missing either breaks login or download |
| Package immutability | Not mentioned | Enforced, lifecycle for cleanup | Immutability is a supply-chain guarantee; lifecycle controls costs |

---

## Related artifacts

- **Skill definition:** `skills/codeartifact-domain-deployer/SKILL.md`
- **Upstream cascade and auth tokens guide:** `skills/codeartifact-domain-deployer/references/upstream-cascade-and-auth-tokens.md`
- **Encryption, VPC endpoint, and metrics guide:** `skills/codeartifact-domain-deployer/references/encryption-vpc-endpoint-and-metrics.md`
- **Slash command:** `commands/aws/deploy-codeartifact-domain.md`
- **Eval suite:** `skills/codeartifact-domain-deployer/evals/evals.json`
- **Legacy test cases:** `skills/codeartifact-domain-deployer/eval/test-cases.yaml`
