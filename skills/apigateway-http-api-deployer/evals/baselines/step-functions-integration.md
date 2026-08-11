# Baseline (no-skill) response: step-functions-integration

This file captures what a generic assistant produces WITHOUT the
apigateway-http-api-deployer skill loaded. The contrast proves the
skill adds the direct Step Functions integration contract
(integration-subtype STEP_FUNCTION, Action=StartSyncExecution,
credentials-arn role, 5s Express ceiling), JWT issuer details, and
auto-deploy stage handling.

---

Here's a plan for integrating Step Functions with your HTTP API.

Architecture:

- HTTP API in us-east-1
- POST /orders triggers the orders-workflow Step Function
- ANY /{proxy+} falls back to a Lambda

Steps:

1. Create the HTTP API.
2. Add routes.
3. For POST /orders, create a Lambda that calls Step Functions.
4. For ANY /{proxy+}, configure the Lambda proxy.
5. Set up JWT authorizer.
6. Deploy.

The Lambda for POST /orders would call StartSyncExecution on the
Express Workflow and return the result.

Commands:

```
aws apigatewayv2 create-api ...
aws apigatewayv2 create-route ...
aws apigatewayv2 create-integration --integration-type AWS_PROXY ...
```

This should work for your synchronous workflow API.
