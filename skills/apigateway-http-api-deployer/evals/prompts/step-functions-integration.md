# Eval prompt: step-functions-integration

Design a deployment plan for an HTTP API with a direct Step Functions
integration (no Lambda in the path). Emit the standard VERDICT block.

Requirements:

- API type: HTTP (v2)
- Endpoint type: REGIONAL (us-east-1)
- Routes and authorization:
  - GET /health [NONE]
  - POST /orders [JWT] → Step Functions `StartSyncExecution` on
    Express Workflow `orders-workflow`
  - ANY /{proxy+} [JWT] → Lambda proxy fallback `orders-fallback`
- State machine:
  `arn:aws:states:us-east-1:111111111111:stateMachine:orders-workflow`
  (Express Workflow, max 5s ceiling)
- JWT authorizer: Cognito issuer
  `https://cognito-idp.us-east-1.amazonaws.com/us-east-1_xyz/`,
  audience `orders-client`
- CORS: allowOrigins=https://shop.example.com,
  allowMethods=GET,POST,OPTIONS, allowHeaders=Authorization,Content-Type,
  allowCredentials=true
- Auto-deploy: true on `$default` stage
- Access logging: JSON to CloudWatch
  `/aws/apigateway/prod-orders-http`
- Throttle: 500 rps / 200 burst default

Existing-account context: the Step Functions state machine exists
and has been tested via the SDK. An IAM role `apigw-sfn-role` exists
with `states:StartSyncExecution` scoped to this state machine. The
Lambda `orders-fallback` exists and already has the
`lambda:InvokeFunction` permission for API Gateway. The Cognito user
pool is configured and ISSUED.
