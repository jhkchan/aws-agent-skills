# Build and Domain Reference — Amplify App Deployer

Deep reference on the `amplify.yml` buildspec format, build phases,
caching, custom headers, redirects (SPA rewrite, legacy 301s), ACM
certificate validation for custom domains, Route 53 vs third-party
DNS, CloudFront-in-front-of-Amplify patterns, and the build image
versions. Loaded on demand by the skill — kept out of the main
SKILL.md body so the provisioning procedure stays scannable.

## Full amplify.yml field reference

```yaml
version: 1
env:
  variables:
    NODE_ENV: production
frontend:
  phases:
    preBuild:
      commands:
        - npm ci
    build:
      commands:
        - npx ampx pipeline-deploy --branch $AWS_BRANCH --app-id $AWS_APP_ID
        - npm run build
    postBuild:
      commands:
        - echo "Build complete"
  artifacts:
    baseDirectory: .next       # Next.js SSR; use 'out' for SSG, 'dist' for Vite
    files:
      - '**/*'
  cache:
    paths:
      - node_modules/**/*
      - .next/cache/**/*       # Next.js build cache
  customHeaders:
    - pattern: '**/*'
      headers:
        - key: Strict-Transport-Security
          value: 'max-age=31536000; includeSubDomains'
        - key: X-Content-Type-Options
          value: 'nosniff'
        - key: X-Frame-Options
          value: 'DENY'
        - key: Content-Security-Policy
          value: "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'"
        - key: Referrer-Policy
          value: 'strict-origin-when-cross-origin'
  redirects:
    - source: '/old-blog/<*>'
      target: '/blog/<*>'
      status: '301'
    - source: '/<*>'
      target: '/index.html'
      status: '200'
      condition: null
test:
  phases:
    preTest:
      commands:
        - npm install
    test:
      commands:
        - npm run test
```

### Amplify-provided environment variables

| Variable | Meaning |
|---|---|
| `AWS_APP_ID` | The Amplify app ID (dXXXXXXXXXXXX) |
| `AWS_BRANCH` | The git branch being built (main, staging, pr123) |
| `AWS_COMMIT_ID` | The git commit SHA |
| `AWS_REGION` | The Amplify app region |
| `AWS_EXECUTION_ENV` | `AWS_AMPLIFY_CONSOLE` |
| `AMPLIFY_GIT_REF` | The git ref being built |

Use these in `amplify.yml` for branch-specific build logic:

```yaml
build:
  commands:
    - if [ "$AWS_BRANCH" = "main" ]; then npm run build:prod; else npm run build:staging; fi
```

## Redirect patterns (SPA rewrite vs legacy)

**SPA rewrite (React Router / Vue Router):**

```yaml
redirects:
  - source: '/<*>'
    target: '/index.html'
    status: '200'    # 200 = rewrite (URL stays the same in browser)
```

Without this, refreshing `/users/123` returns 404 — Amplify's CDN looks
for a literal `/users/123/index.html` that does not exist.

**Legacy redirect (URL migration):**

```yaml
redirects:
  - source: '/old-path'
    target: '/new-path'
    status: '301'    # 301 = permanent redirect (URL changes in browser)
```

**Conditional redirect (per-locale):**

```yaml
redirects:
  - source: '/</^[a-z]{2}$/>'
    target: '/index.html'
    status: '200'
    condition: '/^(en|fr|de|es)$/'
```

## ACM certificate validation by DNS provider

### Route 53 (same account) — automatic

```bash
# 1. Request the cert
aws acm request-certificate \
  --domain-name app.example.com \
  --validation-method DNS \
  --region us-east-1 \
  --output json
# Returns the CNAME record to add

# 2. If Route 53 hosts example.com in the same account, ACM auto-writes
#    the validation record. Wait for status ISSUED.
aws acm describe-certificate \
  --certificate-arn arn:aws:acm:us-east-1:111:certificate/abc \
  --region us-east-1 \
  --query 'Certificate.Status'
```

### Third-party DNS (GoDaddy, Namecheap, Cloudflare) — manual

```bash
# 1. Request the cert (same as above)
# 2. Read the validation CNAME from the cert record
aws acm describe-certificate \
  --certificate-arn arn:aws:acm:us-east-1:111:certificate/abc \
  --region us-east-1 \
  --query 'Certificate.DomainValidationOptions[].ResourceRecord'

# 3. Copy the CNAME name + value to the third-party DNS provider's
#    management console. Wait for DNS propagation (minutes to hours).

# 4. Once validated, the cert status becomes ISSUED. Then associate:
aws amplify create-domain-association \
  --app-id dXXXX \
  --domain-name example.com \
  --sub-domain-settings '[{"prefix":"app","branchName":"main"}]'
```

## Build image versions

| Build image | Node | Python | Notes |
|---|---|---|---|
| `amplify:nodejs-20` | 20.x | 3.12 | Latest; recommended for new apps |
| `amplify:nodejs-18` | 18.x | 3.10 | LTS; supported but EOL approaching |
| `amplify:nodejs-16` | 16.x | 3.9 | EOL — do not use for new apps |

Pin via the app setting:

```bash
aws amplify update-app \
  --app-id dXXXX \
  --build-spec-content "buildImage: amplify:nodejs-20" \
  --output json
```

## CloudFront in front of Amplify (rare pattern)

Amplify already fronts the app with a managed CloudFront distribution.
A second CloudFront in front is only for:

- **Custom WAF rules** that Amplify does not expose.
- **Origin selection** (Amplify as one of several origins).
- **Geo restriction** at the edge.

If you must, configure:

```yaml
# CloudFront distribution with Amplify as origin
Origins:
  - DomainName: dXXXX.amplifyapp.com
    Id: AmplifyOrigin
    CustomOriginConfig:
      HTTPPort: 443
      OriginProtocolPolicy: https-only
```

Note: this adds latency (extra hop) and cost (second CF distribution).
Document the reason in the project README.

## Moved from SKILL.md Step 5 — custom headers + redirects YAML

```yaml
customHeaders:
  - pattern: '**/*'
    headers:
      - key: Strict-Transport-Security
        value: 'max-age=31536000; includeSubDomains'
      - key: Content-Security-Policy
        value: "default-src 'self'; script-src 'self'"
redirects:
  - source: '/old-path'
    target: '/new-path'
    status: '301'
  - source: '/<*>'
    target: '/index.html'
    status: '200'
```

## Moved from SKILL.md Step 6 — ACM cert + domain association commands

```bash
# Request an ACM cert in us-east-1 (Amplify requires us-east-1)
aws acm request-certificate \
  --domain-name app.example.com \
  --validation-method DNS \
  --region us-east-1 \
  --output json
# Add the validation CNAME to Route 53 / third-party DNS

# Associate the domain with the Amplify app
aws amplify create-domain-association \
  --app-id dXXXX \
  --domain-name example.com \
  --sub-domain-settings '[{"prefix":"app","branchName":"main"}]' \
  --output json
```
