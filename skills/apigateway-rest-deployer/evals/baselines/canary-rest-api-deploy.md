# Baseline (no-skill) response: canary-rest-api-deploy

This file captures what a generic assistant produces WITHOUT the
apigateway-rest-deployer skill loaded — the contrast that proves the
skill adds structure (canary percentage configuration, per-method
throttle overrides distinct from stage defaults, JSON access log format
with $context variables, stage variables for per-canary backend).

---

Here's a plan for your products REST API with canary deployment.

Architecture:

- REST API in us-east-1
- Resources: /products, /products/{id}
- Lambda proxy: products-handler
- Cognito auth
- Stage throttling
- Canary at 10 percent

Steps:

1. Create the REST API and resources.
2. Configure Lambda proxy integration.
3. Set up Cognito authorizer.
4. Configure stage throttling.
5. Set up canary deployment.
6. Deploy.

The canary will route 10 percent of traffic to the new version. You can
promote it to 100 percent once you're confident.

For the new v2 schema, you can use stage variables to point at the
correct Lambda version.

Commands:

```
aws apigateway create-deployment --canary-settings percentTraffic=10
```

Let me know if you need help with the promotion process.
