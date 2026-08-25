# Worked examples - Amplify App Deployer

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.
### Worked example — React SPA with S3 + CloudFront-equivalent

```text
APP: marketing-site
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Git provider: CodeCommit (connection: service role AWSAmplifyServiceRole)
  [✓] Repository: codecommit::us-east-1://marketing-site (amplify.yml committed: YES)
  [✓] Framework: React 18 (Vite)
  [✓] Rendering mode: SPA (client-side render, CDN-served)
  [✓] Build settings: amplify.yml (preBuild: npm ci; build: npm run build; artifacts: dist/**/*)
  [✓] Environment variables: 2 plaintext (VITE_API_URL, NODE_ENV)
  [✓] Custom headers: HSTS, X-Content-Type-Options nosniff
  [✓] Redirects: /<*> -> /index.html status 200 (SPA rewrite for React Router)
  [✓] Custom domain: marketing.example.com (ACM cert in us-east-1; DNS validated via Route 53)
  [✓] Backend (Gen 2): N/A (static SPA, no backend)
  [✓] CI/CD: branch builds on every push; main = production
  [✓] Branch environments: main=marketing.example.com, PR=pr<N>.dXXXX.amplifyapp.com
VERIFICATION_COMMANDS:
  aws amplify get-app --app-id dXXXX
  aws amplify list-branches --app-id dXXXX
  aws amplify get-domain-association --app-id dXXXX --domain-name example.com
```

### Worked example — PREREQUISITES_MISSING (no Git provider, no amplify.yml)

```text
APP: new-app
VERDICT: PREREQUISITES_MISSING
CHECKLIST:
  [✗] Git provider: NOT specified — need CodeCommit / GitHub / GitLab / Bitbucket + connection
  [✗] Repository: NOT specified — need repo URL with amplify.yml committed
  [✗] Framework: NOT specified — need Next.js / React / Vue / Angular / Svelte
  [✗] Rendering mode: NOT specified — need SSR / SSG / SPA / ISR
  [✗] ACM certificate: NOT specified — custom domain needs a cert in us-east-1
VERIFICATION_COMMANDS:
  aws codeconnections list-connections
  aws acm list-certificates --region us-east-1
  aws route53 list-hosted-zones
```
