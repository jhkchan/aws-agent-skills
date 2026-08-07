# Baseline (no-skill) response: lambda-proxy-rest-api

This file captures what a generic assistant produces WITHOUT the
apigateway-rest-deployer skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, enumerated CHECKLIST,
create-deployment as the final step, usage plan + API key linkage,
Cognito authorizer with caching TTL, canary 10 percent traffic).

---

Here's a plan for your REST API with Lambda proxy integration.

Architecture:

- REST API in us-east-1
- Resources: /users, /users/{userId}
- Lambda proxy: user-service-handler
- Cognito auth
- Usage plan with rate limiting
- WAF attached
- Custom domain: api.example.com

Steps:

1. Create the REST API.
2. Add resources and methods.
3. Configure Lambda integration.
4. Set up Cognito authorizer.
5. Create usage plan and API keys.
6. Deploy.

You'll need to give API Gateway permission to invoke your Lambda. The
Cognito user pool should be linked via the authorizer.

For the custom domain, you'll need an ACM cert and a base path mapping.

Commands:

```
aws apigateway create-rest-api ...
aws apigateway create-resource ...
aws apigateway put-method ...
aws apigateway put-integration ...
aws apigateway create-deployment ...
```

This should give you a working API. Let me know if anything is unclear.
