# Baseline (no-skill) — code-repository-source

> This is the response a model produces **without** the skill definition.
> It produces a generic create-service call but misses the CodeConnection
> ARN requirement, the runtime specification, the build and start
> commands, the instance role for DynamoDB access, the health check
> policy, and the structured checklist.

---

You can deploy from GitHub by creating an App Runner service:

```bash
aws apprunner create-service \
  --service-name user-feedback-staging \
  --source-configuration '{
    "CodeRepository": {
      "RepositoryUrl": "https://github.com/acme/user-feedback"
    }
  }'
```

App Runner will build and deploy your Node.js app automatically.
Make sure your repository has a package.json.

You might need to set up a connection in the console first.
