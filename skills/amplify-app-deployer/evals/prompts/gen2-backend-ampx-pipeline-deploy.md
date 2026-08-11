# Eval: gen2-backend-ampx-pipeline-deploy

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — Gen 2 pipeline-deploy in build phase, CDK bootstrap verified, AppSync + Lambda resolver

## Prompt

Provision an Amplify Gen 2 backend deployment for app "vue-ssr-shop"
in us-east-1. Frontend is Vue 3 (Nuxt) SSR. Git provider is GitLab
(repo gitlab.com/example/vue-ssr-shop, CodeConnections connection
gitlab-ampx AVAILABLE). amplify.yml committed with `npx ampx
pipeline-deploy --branch $AWS_BRANCH --app-id $AWS_APP_ID` in the
build phase. Backend is Gen 2 TypeScript CDK with AppSync GraphQL
data and a Lambda function resolver. CDK bootstrap CDKToolkit exists
in us-east-1. Custom domain shop.example.com via Route 53 hosted
zone Z333, ACM cert arn:aws:acm:us-east-1:111:certificate/ghi
ISSUED. Environment variables: VUE_APP_API_URL, NODE_ENV plaintext;
DB_PASSWORD via Secrets Manager. Custom headers: HSTS,
X-Content-Type-Options. Redirects: /<*> -> /index.html status 200.
CI/CD on every push; main=prod, staging=staging.shop. Account ID:
123456789012.
