# Eval: react-spa-static-no-backend

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — SPA rendering, no backend, CodeCommit service role, custom domain via Route 53

## Prompt

Provision an Amplify app named "marketing-site" in us-east-1.
Framework is React 18 (Vite), rendering mode SPA (client-side,
CDN-served, no SSR). Git provider is CodeCommit (repo
codecommit::us-east-1://marketing-site, service role
AWSAmplifyServiceRole). amplify.yml committed. Custom domain
marketing.example.com via Route 53 hosted zone Z222 (same account),
ACM cert arn:aws:acm:us-east-1:111:certificate/def in us-east-1,
status ISSUED. No backend (static SPA, no Gen 2). Environment
variables: VITE_API_URL, NODE_ENV plaintext. Custom headers: HSTS,
X-Content-Type-Options nosniff. Redirects: /<*> -> /index.html
status 200 (SPA rewrite for React Router). CI/CD on every push to
main. Account ID: 123456789012.
