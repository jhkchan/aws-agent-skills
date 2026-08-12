# Eval: ssr-nextjs-with-redirects

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — Next.js SSR auto-detected, SPA rewrite status 200, /api route to function, security headers, per-branch Lambda caveat (8 branches = 8 Lambda sets)

## Prompt

Configure Amplify for my Next.js 14 SSR app at
https://github.com/org/my-next-app. The app uses App Router with
SSR pages and API routes. Production branch "main". Build to
.next/. Redirects: catch-all SPA rewrite (status 200), /api route
to the serverless function. Security headers: HSTS, CSP, and
X-Frame-Options. Region us-east-1. The team has 8 active feature
branches.
