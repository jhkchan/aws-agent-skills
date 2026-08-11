# Eval: nextjs-ssr-gen2-backend

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — GitHub CodeConnections, SSR rendering, Gen 2 backend with auth/data/storage, custom domain via Route 53, Secrets Manager for Stripe

## Prompt

Provision a production Amplify app named "prod-web" in us-east-1.
Framework is Next.js 14 with SSR rendering. Git provider is GitHub
(repo github.com/example/prod-web, CodeConnections connection
github-amplify in AVAILABLE state). amplify.yml is committed.
Custom domain app.example.com via Route 53 hosted zone Z111 (same
account), ACM cert
arn:aws:acm:us-east-1:111:certificate/abc in us-east-1, status
ISSUED. Backend is Amplify Gen 2 with Cognito auth, AppSync GraphQL
data, S3 storage (per-user prefixes). Environment variables: API_URL,
NODE_ENV, NEXT_PUBLIC_API_URL plaintext; STRIPE_SECRET_KEY via
Secrets Manager ref. Custom headers: HSTS, X-Content-Type-Options
nosniff, X-Frame-Options DENY, CSP default-src 'self'. Redirects:
SPA rewrite /<*> -> /index.html status 200. CI/CD on every push;
main=prod, staging=staging.example.com, PR previews. Account ID:
123456789012.
