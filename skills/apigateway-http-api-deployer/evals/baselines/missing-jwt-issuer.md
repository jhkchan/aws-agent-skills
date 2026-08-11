# Baseline (no-skill) response: missing-jwt-issuer

This file captures what a generic assistant produces WITHOUT the
apigateway-http-api-deployer skill loaded. The contrast proves the
skill enforces the pre-flight specification gate (catches missing
JWT issuer and emits PREREQUISITES_MISSING with a specific citation
instead of inventing an issuer or producing a partial plan).

---

Here's a plan for your HTTP API with JWT auth.

Architecture:

- HTTP API in us-east-1
- Routes: GET /health (public), GET /users (JWT), POST /users (JWT)
- Lambda: users-handler

Steps:

1. Create the HTTP API.
2. Add routes.
3. Set up JWT authorizer (you'll need your Cognito pool details).
4. Configure Lambda proxy.
5. Deploy.

For the JWT authorizer, you'll need to provide the issuer URL and
audience. I've left placeholders.

Commands:

```
aws apigatewayv2 create-authorizer --jwt-configuration audience=TODO,issuer=TODO
```

Fill in the issuer and audience and you should be good to go.
