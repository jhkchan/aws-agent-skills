# Eval: custom-domain-third-party-dns

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — custom domain on GoDaddy (not Route 53); manual DNS CNAME validation required; cert PENDING_VALIDATION

## Prompt

Provision an Amplify app named "admin-portal" in us-east-1.
Framework is Angular 17 (SPA). Git provider is Bitbucket (repo
bitbucket.org/example/admin-portal, CodeConnections bitbucket-conn
AVAILABLE). amplify.yml committed. Custom domain portal.example.com
— but example.com is hosted on GoDaddy (NOT Route 53). ACM cert
arn:aws:acm:us-east-1:111:certificate/jkl in us-east-1, status
PENDING_VALIDATION. amplify.yml has SPA rewrite /<*> ->
/index.html status 200, security headers (HSTS, nosniff,
X-Frame-Options DENY). No backend. Environment variables:
API_BASE_URL, NODE_ENV. CI/CD on every push to main. Account ID:
123456789012.
