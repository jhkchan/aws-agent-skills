# End-to-End Example: Amplify Branch Deployment

A walkthrough showing how to use the `amplify-branch-deployer` skill
from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are deploying a Next.js web app via AWS Amplify with a production
branch, custom domain, PR preview, and security headers. The app is a
monorepo (Turborepo) where the web app lives at `packages/web-app`. The
deployment needs:

- App: my-web-app from https://github.com/org/my-monorepo
- Monorepo: appRoot=packages/web-app (Turborepo workspace)
- Production branch: main (stage PRODUCTION, auto-build)
- Build spec: amplify.yml at packages/web-app/amplify.yml (NOT buildspec.yml)
- Custom domain: example.com → main, staging.example.com → staging
- Route 53 hosted zone: Z1DXXXXXXXXXX
- Security headers: HSTS, X-Frame-Options, X-Content-Type-Options
- Redirects: SPA rewrite catch-all (status 200)
- PR preview: enabled with fixed environment "pr-preview"
- SSR: Next.js 14 (Lambda serverless functions auto-provisioned)
- Build instance: medium

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-amplify-branch
```

Then paste the requirements.

### Option B: Natural language

```
You: "Set up Amplify for my Next.js monorepo app at
      packages/web-app. Production branch main with custom
      domain example.com via Route 53. Enable PR preview
      with cost control. Add security headers and SPA rewrite."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create amplify app from git"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
AMPLIFY: my-web-app (d2y0lrmp1qq2tu)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Git provider connection: GitHub (OAuth via console)
  [✓] Repository: https://github.com/org/my-monorepo
  [✓] App created: d2y0lrmp1qq2tu (appRoot: packages/web-app — monorepo)
  [✓] Build spec: amplify.yml at packages/web-app/amplify.yml
  [✓] Branch: main (stage: PRODUCTION, auto-build: true)
  [✓] Build instance: medium
  [✓] Environment variables: NEXT_PUBLIC_API_URL (app), NODE_ENV=production (branch)
  [✓] Redirects: SPA rewrite (/<*> → /index.html 200)
  [✓] Custom headers: HSTS, X-Frame-Options, X-Content-Type-Options
  [✓] Basic auth: disabled on main; enabled on staging
  [✓] Custom domain: example.com → main (DNS verified, SSL active)
  [✓] PR preview: enabled (environment: pr-preview, reuses single env)
  [✓] Monorepo: appRoot=packages/web-app
  [✓] SSR/SSG: SSR (Next.js 14, Lambda functions auto-provisioned)
  [✓] Serverless functions: 3 (per branch)
  [✓] Notifications: SNS → Slack on build result
VERIFICATION_COMMANDS:
  aws amplify get-app --app-id d2y0lrmp1qq2tu
  aws amplify list-branches --app-id d2y0lrmp1qq2tu
  aws amplify get-domain-association --app-id d2y0lrmp1qq2tu --domain-name example.com
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Create the app with monorepo appRoot
aws amplify create-app \
  --name my-web-app \
  --repository https://github.com/org/my-monorepo \
  --app-root packages/web-app \
  --platform WEB \
  --iam-service-role-arn arn:aws:iam::123456789012:role/amplify-service-role \
  --custom-rules '[{"source":"/<*>","target":"/index.html","status":"200"}]'

# Step 2: Create the production branch
aws amplify create-branch \
  --app-id d2y0lrmp1qq2tu \
  --branch-name main \
  --stage PRODUCTION \
  --enable-auto-build \
  --enable-pull-request-preview \
  --pull-request-environment-name pr-preview \
  --environment-variables NODE_ENV=production

# Step 3: Create the staging branch with basic auth
aws amplify create-branch \
  --app-id d2y0lrmp1qq2tu \
  --branch-name staging \
  --stage BETA \
  --enable-auto-build \
  --enable-basic-auth \
  --basic-auth-credentials "reviewer:s3cr3t"

# Step 4: Domain association
aws amplify create-domain-association \
  --app-id d2y0lrmp1qq2tu \
  --domain-name example.com \
  --sub-domains \
    subDomainSetting=PRIMARY,branchName=main,prefix="" \
    subDomainSetting=PROD,branchName=staging,prefix="staging"

# Step 5: Add Route 53 CNAME for DNS verification
VERIFICATION_CNAME=$(aws amplify get-domain-association \
  --app-id d2y0lrmp1qq2tu --domain-name example.com \
  --query 'domainAssociation.subDomains[0].dnsRecord' --output text)

aws route53 change-resource-record-sets \
  --hosted-zone-id Z1DXXXXXXXXXX \
  --change-batch "{\"Changes\":[{\"Action\":\"CREATE\",\"ResourceRecordSet\":{\"Name\":\"_amplify.example.com\",\"Type\":\"CNAME\",\"TTL\":300,\"ResourceRecords\":[{\"Value\":\"$VERIFICATION_CNAME\"}]}}]}"
```

---

## Step 4 — Post-deployment verification

```bash
# App status
aws amplify get-app --app-id d2y0lrmp1qq2tu \
  --query 'app.{Name:name,DefaultDomain:defaultDomain,Repository:repository}'

# Branches
aws amplify list-branches --app-id d2y0lrmp1qq2tu \
  --query 'branches[*].{Branch:branchName,Stage:stage,AutoBuild:enableAutoBuild,PRPreview:enablePullRequestPreview}'

# Domain status (wait for AVAILABLE)
aws amplify get-domain-association \
  --app-id d2y0lrmp1qq2tu \
  --domain-name example.com \
  --query 'domainAssociation.{Status:domainStatus,SSLCert:certificateVerificationDNSRecord}'

# Latest build status
aws amplify list-jobs \
  --app-id d2y0lrmp1qq2tu \
  --branch-name main \
  --max-results 1 \
  --query 'jobSummaries[0].{Status:status,StartTime:startTime,EndTime:endTime}'
```

---

## What the skill catches that a naive deployment misses

| Configuration | Naive deployment | Skill output | Why the skill is right |
|---|---|---|---|
| Build spec | `buildspec.yml` | `amplify.yml` | Amplify ignores `buildspec.yml`; this is the #1 build-silent-failure cause |
| SPA rewrite | status 301 | status 200 | 301 redirects to literal `/index.html`; 200 rewrites preserving the URL for client-side routing |
| Monorepo | Builds from root | appRoot=packages/web-app | Without appRoot, Amplify misses the subdir app entirely |
| PR preview | One env per PR | Fixed env name (cost control) | Each PR env consumes build minutes; fixed name reuses one |
| Custom domain | Forgets DNS verification | CNAME in Route 53 | Without verification, SSL never provisions; domain stuck in CREATING |
| Security headers | None | HSTS, X-Frame-Options, CSP | Production apps without security headers are vulnerable |
| SSR cost | Ignores per-branch Lambda | Notes 8 branches = 8 Lambda sets | SSR deploys Lambda per branch; costs scale with branch count |
| Git connection | Assumes CLI can auth | Flags console OAuth requirement | The one-time OAuth handshake requires console interaction |

---

## Related artifacts

- **Skill definition:** `skills/amplify-branch-deployer/SKILL.md`
- **Branch + PR preview guide:** `skills/amplify-branch-deployer/references/branch-builds-and-preview.md`
- **Domain + redirect + auth guide:** `skills/amplify-branch-deployer/references/domains-redirects-and-auth.md`
- **Slash command:** `commands/aws/deploy-amplify-branch.md`
- **Eval suite:** `skills/amplify-branch-deployer/evals/evals.json`
- **Legacy test cases:** `skills/amplify-branch-deployer/eval/test-cases.yaml`
