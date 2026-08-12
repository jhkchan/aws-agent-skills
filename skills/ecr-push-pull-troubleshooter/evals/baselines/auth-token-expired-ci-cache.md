# Baseline (no-skill) response: auth-token-expired-ci-cache

---

Your docker login has expired. ECR tokens are only valid for 12 hours,
and your CI runner is caching the old credentials. Run:

```
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 111111111111.dkr.ecr.us-east-1.amazonaws.com
```

Then retry the push. If it still fails, check that your CI role has
`ecr:GetAuthorizationToken` and `ecr:PutImage` permissions.
