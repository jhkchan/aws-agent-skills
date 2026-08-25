# Domains, Redirects, and Auth — Amplify Branch Deployer

Deep reference on custom domains via Route 53 (domain association,
sub-domain mapping, DNS verification, SSL auto-provisioning), redirects
and rewrites (SPA rewrite vs SSR function routes, status code
semantics, custom rules), custom headers (security headers, cache
headers), basic auth per branch, and password protection. Loaded on
demand by the skill — kept out of the main SKILL.md body so the
provisioning procedure stays scannable.

## Custom domain fundamentals

### Domain association

A domain association maps a custom domain (and sub-domains) to Amplify
branches. Each sub-domain maps to exactly one branch.

```bash
aws amplify create-domain-association \
  --app-id d2y0lrmp1qq2tu \
  --domain-name example.com \
  --sub-domains \
    subDomainSetting=PRIMARY,branchName=main,prefix="" \
    subDomainSetting=PROD,branchName=staging,prefix="staging" \
    subDomainSetting=PROD,branchName=dev,prefix="dev"
```

This maps:
- `example.com` (apex) → `main` branch
- `staging.example.com` → `staging` branch
- `dev.example.com` → `dev` branch

### DNS verification

Amplify returns DNS records that must be added to your DNS provider:

```bash
aws amplify get-domain-association \
  --app-id d2y0lrmp1qq2tu \
  --domain-name example.com
```

The response includes:
- A CNAME record for domain ownership verification
- A CNAME record for the SSL certificate validation

### Route 53 hosted zone

For domains managed by Route 53, add the verification record:

```bash
aws route53 change-resource-record-sets \
  --hosted-zone-id Z1DXXXXXXXXXX \
  --change-batch '{
    "Changes": [{
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "_amplify.example.com",
        "Type": "CNAME",
        "TTL": 300,
        "ResourceRecords": [{"Value": "<verification-id>.amplify.app"}]
      }
    }]
  }'
```

Route 53 propagation: ~2-5 minutes. Third-party DNS (GoDaddy, Namecheap,
Cloudflare): 15-45 minutes.

### SSL auto-provisioning

Amplify auto-provisions an SSL certificate via AWS Certificate Manager
(ACM) once DNS verifies. The certificate covers:
- The apex domain (`example.com`)
- The `www` sub-domain (`www.example.com`)
- All configured sub-domains (`staging.example.com`, `dev.example.com`)

No manual CSR or cert upload is needed.

### Domain status lifecycle

```text
CREATING → DNS records returned, waiting for verification
    │
    ▼
AVAILABLE → DNS verified, SSL active, domain serving traffic
    │
    ├── (if DNS record removed) → PENDING_DELETION → DELETED
    └── (if SSL renewal fails) → PENDING_VERIFICATION
```

### Third-party DNS

For domains NOT in Route 53, add the CNAME records to your DNS
provider's management console. Amplify supports any DNS provider that
allows CNAME records.

**Wildcard sub-domains:** Amplify does NOT support wildcard sub-domains
(`*.example.com`). Each sub-domain must be explicitly configured in the
domain association.

## Redirects and rewrites

### customRules configuration

Redirects and rewrites are configured via `customRules` on the app (in
the console or via `update-app`) or in `amplify.yml`:

```yaml
customRules:
  - source: /<*>
    target: /index.html
    status: 200
```

### Status code semantics

| Status | Behavior | Use case |
|---|---|---|
| `200` | Rewrite (URL stays the same, content served from target) | SPA catch-all routing |
| `301` | Permanent redirect (URL changes in browser) | Domain migration, old→new URL |
| `302` | Temporary redirect (URL changes in browser) | A/B testing, temporary maintenance |
| `404` | Not found (display error page) | Explicit 404 pages |

### SPA catch-all rewrite (CRITICAL)

Single Page Applications (React, Vue, Angular) use client-side routing.
Without a catch-all rewrite, direct URL access or page refresh on a
client-side route returns 404.

```yaml
customRules:
  - source: /<*>
    target: /index.html
    status: 200    # MUST be 200 (rewrite), NOT 301 (redirect)
```

**Why 200, not 301?** A `200` rewrite serves `index.html` content at
the requested URL — the browser's URL bar stays the same, and the
client-side router handles the path. A `301` redirect changes the URL
bar to `/index.html`, losing the original path and breaking client-side
routing.

### SSR (Next.js) routes

For Next.js SSR, Amplify auto-detects the build output and provisions
Lambda functions for SSR routes. Custom redirect rules must not shadow
the function routes:

```yaml
customRules:
  # API routes to serverless function
  - source: /api/<*>
    target: /api/[...path]
    status: 200
  # SPA-style rewrite for static pages (NOT for SSR pages)
  - source: /<*>
    target: /index.html
    status: 200
```

**Note:** for full Next.js SSR, Amplify's auto-detection handles routing
without manual custom rules. Only add custom rules for edge cases.

### Common redirect patterns

```yaml
customRules:
  # Domain redirect (old → new)
  - source: old.example.com
    target: https://new.example.com
    status: 301
  # Path redirect with capture
  - source: /docs/<*>
    target: /documentation/<*>
    status: 301
  # HTTP to HTTPS (Amplify does this automatically, but explicit rule)
  - source: http://example.com/<*>
    target: https://example.com/<*>
    status: 301
  # SPA rewrite
  - source: /<*>
    target: /index.html
    status: 200
```

## Custom headers

### Security headers

```yaml
customHeaders:
  - pattern: '**/*'
    headers:
      - key: Strict-Transport-Security
        value: 'max-age=31536000; includeSubDomains; preload'
      - key: X-Frame-Options
        value: SAMEORIGIN
      - key: X-Content-Type-Options
        value: nosniff
      - key: Referrer-Policy
        value: strict-origin-when-cross-origin
      - key: Content-Security-Policy
        value: "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' https://api.example.com; frame-ancestors 'self'"
```

**Every production app should set at minimum:**
- `Strict-Transport-Security` (HSTS) — force HTTPS
- `X-Frame-Options: SAMEORIGIN` — prevent clickjacking
- `X-Content-Type-Options: nosniff` — prevent MIME-sniffing
- `Content-Security-Policy` — restrict resource loading

### Cache headers

For static assets with content hashing (`/static/`, `/_next/static/`):

```yaml
customHeaders:
  - pattern: '/_next/static/*'
    headers:
      - key: Cache-Control
        value: 'public, max-age=31536000, immutable'
  - pattern: '/static/*'
    headers:
      - key: Cache-Control
        value: 'public, max-age=31536000, immutable'
```

Immutable caching is safe for content-hashed assets: the filename
changes when content changes, so the cache naturally invalidates.

## Basic auth and password protection

### Per-branch basic auth

```bash
aws amplify update-branch \
  --app-id d2y0lrmp1qq2tu \
  --branch-name staging \
  --enable-basic-auth \
  --basic-auth-credentials "username:s3cr3t"
```

Basic auth is applied at the CDN edge. Anyone visiting the branch URL
sees a browser HTTP Basic Authentication prompt. It covers ALL paths
under the branch domain.

### Disable basic auth

```bash
aws amplify update-branch \
  --app-id d2y0lrmp1qq2tu \
  --branch-name staging \
  --no-enable-basic-auth
```

### Common use cases

- **Staging behind auth:** prevent public access during pre-launch
- **Preview branches:** internal review only
- **Compliance:** GDPR/HIPAA environments that must not be publicly
  accessible
- **Client review:** share credentials with stakeholders for feedback

### Limitations

- Basic auth is HTTP Basic (base64-encoded credentials) — NOT secure
  for sensitive data. Use it as a gate, not as the sole auth mechanism.
- For production apps with user accounts, use Cognito (via the Amplify
  backend) for proper authentication.
- Basic auth credentials are shared per branch (not per user). All
  reviewers share the same username/password.

## Terraform example

```hcl
resource "aws_amplify_app" "main" {
  name       = "my-web-app"
  repository = "https://github.com/org/my-web-app"

  # The OAuth token must be provided; the connection itself is
  # established via the console.
  access_token = var.github_access_token

  build_spec = <<-EOT
    version: 1
    frontend:
      phases:
        preBuild:
          - npm install
        build:
          - npm run build
      artifacts:
        baseDirectory: .next
        files:
          - '**/*'
      cache:
        paths:
          - node_modules/**/*
  EOT

  custom_rule {
    source = "/<*>"
    target = "/index.html"
    status = "200"
  }
}

resource "aws_amplify_branch" "main" {
  app_id              = aws_amplify_app.main.id
  branch_name         = "main"
  stage               = "PRODUCTION"
  enable_auto_build   = true
  enable_pull_request_preview = true
  pull_request_environment_name = "pr-preview"
}

resource "aws_amplify_domain_association" "main" {
  app_id      = aws_amplify_app.main.id
  domain_name = "example.com"

  sub_domain {
    branch_name = aws_amplify_branch.main.branch_name
    prefix      = ""
  }

  sub_domain {
    branch_name = "staging"
    prefix      = "staging"
  }
}
```

**Warning:** the Terraform `aws_amplify_app` requires `access_token` (a
GitHub personal access token). The console-based OAuth flow does NOT
work with Terraform. For console-connected apps, manage the app outside
Terraform and use Terraform only for branches and domain associations.

## Moved from SKILL.md Step 5 — custom headers YAML

```yaml
customHeaders:
  - pattern: '**/*'
    headers:
      - key: Strict-Transport-Security
        value: 'max-age=31536000; includeSubDomains'
      - key: X-Frame-Options
        value: SAMEORIGIN
      - key: X-Content-Type-Options
        value: nosniff
  - pattern: '/static/*'
    headers:
      - key: Cache-Control
        value: 'public, max-age=31536000, immutable'
```

## Moved from SKILL.md Step 6 — basic auth per branch

Basic auth protects a branch with HTTP Basic Authentication at the CDN
edge. Useful for staging/preview environments that should not be public.

```bash
aws amplify update-branch \
  --app-id d2y0lrmp1qq2tu \
  --branch-name staging \
  --enable-basic-auth \
  --basic-auth-credentials base64-encoded-credentials
```

**Format:** the credentials are `username:password` (the API accepts the
raw string; the SDK base64-encodes). Anyone visiting the branch URL sees
a browser auth prompt. Basic auth applies to all paths under the branch
domain.

**Common use cases:**
- Staging branch behind auth during pre-launch
- Preview branches for internal review
- Compliance: preventing public access to non-production environments
