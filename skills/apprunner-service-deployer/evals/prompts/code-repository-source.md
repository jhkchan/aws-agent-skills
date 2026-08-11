# Eval: code-repository-source

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — source code repository, Node.js runtime, CodeConnection

## Prompt

Deploy an App Runner service named "user-feedback-staging" in
us-east-1. Source: GitHub repository
https://github.com/acme/user-feedback, branch main, Node.js 20
runtime. Build command: npm install. Start command: node
server.js. Port 3000 with health check GET /healthz. Instance:
1 vCPU / 2048 MB. CodeConnection ARN
arn:aws:codeconnections:us-east-1:123456789012:connection/feedback-conn.
Instance role feedback-instance with DynamoDB scoped. Environment
vars ENV=staging. Auto-scaling default. Deployment trigger
automatic. Account: 123456789012.
