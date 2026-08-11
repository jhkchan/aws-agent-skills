# End-to-End Example: CodeArtifact npm Repository Provisioning

A walkthrough showing how to use the `codeartifact-repository-deployer`
skill from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning a CodeArtifact npm repository named `shared-npm`
for the organization. The goal:

- Domain: `shared` (existing, owner `123456789012`)
- Repository: `shared-npm`
- External connection: `public:npmjs`
- Upstream chain: `shared-internal` (an internal npm mirror) then the
  external connection
- CI consume access for the `ci-build` IAM role
- Publish access for the `release-pipeline` IAM role
- CI builds use `codeartifact login` for npm

Region: `us-east-1`
Account: `123456789012`

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-codeartifact-repository
```

Then paste the repository requirements.

### Option B: Natural language

```
You: "Provision a CodeArtifact npm repository named shared-npm in
      us-east-1. Domain shared (existing). Associate public:npmjs
      external connection. Upstream to shared-internal. CI consume
      for ci-build role, publish for release-pipeline role. Use
      codeartifact login for npm. Account: 123456789012."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "deploy codeartifact repository"
```

Output:

```
[Phase: Deploy | Skills routed: codeartifact-repository-deployer]

Primary route: codeartifact-repository-deployer (score: 18)
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
REPOSITORY: shared-npm
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓]      Domain — shared (existing, owner 123456789012)
  [✓]      Repository — shared-npm
  [✓]      Format — npm
  [✓]      Upstream chain — shared-internal -> external:npmjs
  [✓]      External connection — public:npmjs (CodeArtifact managed)
  [✓]      Connection — arn:aws:codeartifact:us-east-1:123456789012:repository/shared/shared-npm
  [✓]      Domain owner IAM — arn:aws:iam::123456789012:role/devops-admin (codeartifact:* on domain)
  [✓]      Repository consume policy — arn:aws:iam::123456789012:role/ci-build (ReadFromRepository, GetAuthorizationToken, GetPackageVersionAsset)
  [✓]      Repository publish policy — arn:aws:iam::123456789012:role/release-pipeline (PublishPackageVersion, PutPackageMetadata)
VERIFICATION_COMMANDS:
  aws codeartifact describe-domain --domain shared --domain-owner 123456789012
  aws codeartifact describe-repository --domain shared --repository shared-npm
  aws codeartifact list-repositories-in-domain --domain shared
  aws codeartifact list-external-connections --domain shared
  aws codeartifact get-repository-endpoint --domain shared --repository shared-npm --format npm
  aws codeartifact login --tool npm --repository shared-npm --domain shared --domain-owner 123456789012
```

---

## Step 3 — Create the repository and wire upstreams

```bash
# Step 2: Create the repository
aws codeartifact create-repository \
  --domain shared \
  --repository shared-npm \
  --description "Shared npm packages with npmjs public upstream" \
  --tags '[{"Key":"Environment","Value":"production"},{"Key":"Format","Value":"npm"}]'

# Step 3: Associate the external connection
aws codeartifact associate-external-connection \
  --domain shared \
  --repository shared-npm \
  --external-connection public:npmjs

# Step 4: Chain upstream to shared-internal (internal-first ordering)
aws codeartifact update-repository \
  --domain shared \
  --repository shared-npm \
  --upstreams repository=shared-internal
```

---

## Step 4 — Configure IAM policies

The skill produces three scoped IAM policies:

```bash
# CI build consume policy
cat > /tmp/ci-consume-policy.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "Login",
      "Effect": "Allow",
      "Action": ["codeartifact:GetAuthorizationToken", "codeartifact:ReadFromRepository"],
      "Resource": "arn:aws:codeartifact:us-east-1:123456789012:domain/shared"
    },
    {
      "Sid": "ReadPackages",
      "Effect": "Allow",
      "Action": [
        "codeartifact:ReadFromRepository",
        "codeartifact:GetPackageVersionAsset",
        "codeartifact:ListPackageVersionAssets",
        "codeartifact:DescribePackageVersion"
      ],
      "Resource": "arn:aws:codeartifact:us-east-1:123456789012:repository/shared/shared-npm/*"
    }
  ]
}
EOF

aws iam put-role-policy \
  --role-name ci-build \
  --policy-name codeartifact-consume \
  --policy-document file:///tmp/ci-consume-policy.json

# Release pipeline publish policy
cat > /tmp/release-publish-policy.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "Publish",
      "Effect": "Allow",
      "Action": [
        "codeartifact:PublishPackageVersion",
        "codeartifact:PutPackageMetadata",
        "codeartifact:UpdatePackageVersionsStatus",
        "codeartifact:ReadFromRepository"
      ],
      "Resource": "arn:aws:codeartifact:us-east-1:123456789012:repository/shared/shared-npm/*"
    }
  ]
}
EOF

aws iam put-role-policy \
  --role-name release-pipeline \
  --policy-name codeartifact-publish \
  --policy-document file:///tmp/release-publish-policy.json
```

---

## Step 5 — Wire CI builds via `codeartifact login`

```bash
# CI pipeline (run at the start of every build)
aws codeartifact login \
  --tool npm \
  --domain shared \
  --domain-owner 123456789012 \
  --repository shared-npm

# Smoke test
npm install lodash
```

The `codeartifact login` command updates `~/.npmrc` with the
repository endpoint and a short-lived (12-hour) authorization token.

---

## Step 6 — Post-provisioning verification

```bash
# Domain
aws codeartifact describe-domain --domain shared --domain-owner 123456789012

# Repository (verify upstreams + external connections)
aws codeartifact describe-repository --domain shared --repository shared-npm

# All repositories in domain
aws codeartifact list-repositories-in-domain --domain shared

# Repository endpoint URL
aws codeartifact get-repository-endpoint \
  --domain shared --repository shared-npm --format npm

# Packages in repository
aws codeartifact list-packages --domain shared --repository shared-npm
```

---

## What the skill catches that a naive deployment misses

| Configuration | Naive deployment | Skill output | Why the skill is right |
|---|---|---|---|
| Upstream chain order | External connection upstream of internal mirror | Internal-first, external-last ordering | Public packages with the same name would shadow internal packages — supply-chain attack vector. |
| External connection placement | Associated on every repo in the chain | Associated on the terminal repo only | Avoids redundant external fetches and simplifies governance. |
| Consume vs publish IAM | Single broad `codeartifact:*` policy | Separated consume (ReadFromRepository) and publish (PublishPackageVersion) | Least privilege: CI cannot publish, release pipeline cannot create repositories. |
| `codeartifact login` | Manual `.npmrc` editing | `--tool npm` CLI auto-configures `.npmrc` | Removes manual token handling errors; token is short-lived. |
| Token expiry | Long-lived tokens in CI secrets | `codeartifact login` at the start of each build | Tokens expire in 12h; long-lived tokens are a credential leak risk. |
| Domain verification | Assumes domain exists | `describe-domain` first | Repository creation fails silently with `ResourceNotFoundException` if the domain does not exist. |
| External connection Region | Assumes all connections available everywhere | Verifies via `list-external-connections` | Swift and Cargo external connections are Region-limited. |

---

## Related artifacts

- **Skill definition:** `skills/codeartifact-repository-deployer/SKILL.md`
- **Deployment CLI commands:** `skills/codeartifact-repository-deployer/references/deployment-cli-commands.md`
- **Upstreams and cross-account guide:** `skills/codeartifact-repository-deployer/references/upstreams-and-cross-account-guide.md`
- **Slash command:** `commands/aws/deploy-codeartifact-repository.md`
- **Eval suite:** `skills/codeartifact-repository-deployer/evals/evals.json`
- **Legacy test cases:** `skills/codeartifact-repository-deployer/eval/test-cases.yaml`
