# Baseline (no-skill) response: lambda-proxy-jwt-cors

This file captures what a generic assistant produces WITHOUT the
apigateway-http-api-deployer skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, enumerated CHECKLIST,
auto-deploy on $default, JWT issuer trailing slash, CORS
allowCredentials + Authorization header, lambda:AddPermission for the
v2 principal).

---

Here's a plan for your HTTP API with Lambda proxy integration.

Architecture:

- HTTP API in us-east-1
- Routes: GET /health, GET /users, POST /users, GET /users/{userId},
  ANY /{proxy+}
- Lambda proxy: user-service-handler
- JWT auth via Cognito
- CORS enabled
- Custom domain: api.example.com

Steps:

1. Create the HTTP API.
2. Add routes.
3. Configure Lambda integration.
4. Set up JWT authorizer with Cognito.
5. Enable CORS.
6. Deploy.

You'll need to give API Gateway permission to invoke your Lambda. The
Cognito user pool should be linked via the authorizer.

For the custom domain, you'll need an ACM cert and an API mapping.

Commands:

```
aws apigatewayv2 create-api ...
aws apigatewayv2 create-route ...
aws apigatewayv2 create-integration ...
```

This should give you a working API. Let me know if anything is unclear.
