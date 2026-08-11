# Baseline (no-skill) response: missing-integration-target

This file captures what a generic assistant produces WITHOUT the
apigateway-http-api-deployer skill loaded. The contrast proves the
skill enforces the pre-flight specification gate (catches missing
integration target and emits PREREQUISITES_MISSING instead of
assuming Lambda proxy by default).

---

Here's a plan for your HTTP API.

Architecture:

- HTTP API in us-east-1
- Routes: GET /health, GET /users, POST /users, GET /users/{userId}
- JWT auth on /users routes

Steps:

1. Create the HTTP API.
2. Add routes.
3. Configure integration (Lambda proxy is typical).
4. Set up JWT authorizer.
5. Deploy.

Commands:

```
aws apigatewayv2 create-api ...
aws apigatewayv2 create-route ...
aws apigatewayv2 create-integration ...
```

You didn't specify the backend, so I've assumed Lambda proxy. Adjust
the integration type if you need HTTP proxy, VPC link, or another AWS
service.
