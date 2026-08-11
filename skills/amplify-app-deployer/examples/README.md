# End-to-End Example: Amplify App Deployment

A walkthrough showing how to use the `amplify-app-deployer` skill from
invocation through verification. Mirrors the structured-eval pattern of
shipping a concrete worked example per skill.

---

## Scenario

You are provisioning a production Next.js 14 SSR app with an Amplify
Gen 2 backend. The app needs:

- Framework: Next.js 14 (SSR rendering)
- Git provider: GitHub (CodeConnections, repo github.com/example/prod-web)
- Build settings: `amplify.yml` committed, `npx ampx pipeline-deploy` in build phase
- Backend: Amplify Gen 2 (Cognito auth, AppSync GraphQL, S3 storage)
- Custom domain: app.example.com (Route 53 hosted zone Z111, ACM cert in us-east-1)
- Environment variables: API_URL, NODE_ENV, NEXT_PUBLIC_API_URL (plaintext) + STRIPE_SECRET_KEY (Secrets Manager)
- Custom headers: HSTS, CSP, X-Frame-Options DENY
- Redirects: SPA rewrite /<*> -> /index.html status 200
- CI/CD: branch builds on every push; main=prod, staging, PR previews

App name: `prod-web`
Region: `us-east-1`
Account: `123456789012`

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-amplify-app
```

Then paste the requirements.

### Option B: Natural language

```
You: "Provision a production Amplify app named prod-web. Next.js 14
      SSR with Gen 2 backend (Cognito, AppSync, S3). GitHub repo
      example/prod-web with CodeConnections. Custom domain
      app.example.com via Route 53. Secrets Manager for Stripe key.
      Account 123456789012."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create an amplify app"
```

Output:

```
[Phase: Deploy | Skills routed: amplify-app-deployer]

Primary route: amplify-app-deployer (score: 22)
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
APP: prod-web
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Git provider: GitHub (CodeConnections github-amplify AVAILABLE)
  [✓] Repository: github.com/example/prod-web (amplify.yml committed)
  [✓] Framework: Next.js 14
  [✓] Rendering mode: SSR
  [✓] Build settings: ampx pipeline-deploy + npm run build
  [✓] Environment variables: 3 plaintext, 1 Secrets Manager ref
  [✓] Custom headers: HSTS, nosniff, X-Frame-Options DENY, CSP
  [✓] Redirects: /<*> -> /index.html status 200
  [✓] Custom domain: app.example.com (ACM cert ISSUED, Route 53)
  [✓] Backend (Gen 2): Cognito auth, AppSync GraphQL, S3 storage
  [✓] CI/CD: branch builds; main=prod, staging=staging, PR=preview
VERIFICATION_COMMANDS:
  aws amplify get-app --app-id dXXXX
  aws amplify list-branches --app-id dXXXX
  aws amplify get-domain-association --app-id dXXXX --domain-name example.com
  aws acm describe-certificate --certificate-arn <arn> --region us-east-1
```

---

## Step 3 — Provisioning commands

```bash
# 1. Create the Amplify app with GitHub CodeConnections
aws amplify create-app \
  --name prod-web \
  --repository github.com/example/prod-web \
  --platform WEB \
  --iam-service-role arn:aws:iam::123456789012:role/AmplifyServiceRole \
  --build-spec-content file://amplify.yml \
  --environment-variables \
    NODE_ENV=production,API_URL=https://api.example.com,NEXT_PUBLIC_API_URL=https://api.example.com \
  --custom-rules \
    source=STRIPE_SECRET_KEY,target=arn:aws:secretsmanager:us-east-1:123456789012:secret:stripe-XXX \
  --output json

# 2. Create the main branch (triggers first build)
aws amplify create-branch \
  --app-id dXXXX \
  --branch-name main \
  --stage PRODUCTION \
  --output json

# 3. Associate the custom domain
aws amplify create-domain-association \
  --app-id dXXXX \
  --domain-name example.com \
  --sub-domain-settings '[{"prefix":"app","branchName":"main"}]' \
  --output json

# 4. Create the staging branch
aws amplify create-branch \
  --app-id dXXXX \
  --branch-name staging \
  --stage BETA \
  --output json
```

---

## Step 4 — Post-deployment verification

```bash
# App state, build config, environment variables
aws amplify get-app --app-id dXXXX

# Branches and their URLs
aws amplify list-branches --app-id dXXXX

# Domain association (DNS records, cert status)
aws amplify get-domain-association \
  --app-id dXXXX --domain-name example.com

# ACM certificate status (must be ISSUED in us-east-1)
aws acm describe-certificate \
  --certificate-arn arn:aws:acm:us-east-1:111:certificate/abc \
  --region us-east-1

# Verify the latest build succeeded
aws amplify list-jobs \
  --app-id dXXXX --branch-name main \
  --query 'jobs[0].{Status:status,Summary:summary}'
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Rendering mode | Defaults to SPA | SSR (Amplify auto-provisions SSR compute) | SSR-as-SPA = 404 on dynamic Next.js routes |
| Backend deploy | `amplify push` (Gen 1) | `npx ampx pipeline-deploy` (Gen 2) | Gen 1 is legacy; Gen 2 is CDK-based, branch-aware |
| Secrets | Plaintext env var | Secrets Manager reference | Plaintext env vars are visible in Console and `amplify.yml` |
| ACM region | us-east-2 | us-east-1 | Amplify custom domains require the cert in us-east-1 |
| Redirects | Console-configured | Committed in `amplify.yml` | Console values are overwritten on the next push |
| Build image | Default (Node 16, EOL) | `amplify:nodejs-20` | Node 16 is EOL; pin a supported image |
| CDK bootstrap | Skipped | Verified `CDKToolkit` stack exists | First Gen 2 deploy fails without the CDK bootstrap |
| Branch envs | One big `main` | main + staging + PR previews | Loses preview-URL workflow; main/staging/PR is the superpower |
| Headers | Console-configured | Committed in `amplify.yml` | Console values overwritten on next push |

---

## Related artifacts

- **Skill definition:** `skills/amplify-app-deployer/SKILL.md`
- **Build and domain guide:** `skills/amplify-app-deployer/references/build-and-domain-reference.md`
- **Gen 2 backend guide:** `skills/amplify-app-deployer/references/backend-gen2-reference.md`
- **Slash command:** `commands/aws/deploy-amplify-app.md`
- **Eval suite:** `skills/amplify-app-deployer/evals/evals.json`
- **Legacy test cases:** `skills/amplify-app-deployer/eval/test-cases.yaml`
