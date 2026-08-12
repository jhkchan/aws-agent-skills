# End-to-End Example: API Gateway WebSocket API Deployment

A walkthrough showing how to use the `apigateway-websocket-deployer`
skill from invocation through verification. Mirrors the
structured-eval pattern of shipping a concrete worked example per
skill.

---

## Scenario

You are provisioning an API Gateway WebSocket API for a real-time
chat application with $connect/$disconnect routes, custom message
routes, DynamoDB connection management, a Lambda custom authorizer,
and bidirectional communication. The deployment needs:

- API name: my-chat-api
- Region: us-east-1
- Route selection expression: $request.body.action
- $connect: Lambda ws-connect-handler (stores ConnectionId in
  DynamoDB WebSocketConnections)
- $disconnect: Lambda ws-disconnect-handler (deletes ConnectionId)
- Custom routes: sendMessage, joinRoom, leaveRoom
- Route response: enabled on sendMessage (bidirectional)
- Custom authorizer: ws-auth on $connect (token from query string)
- Keepalive: client-side heartbeat every 60 seconds
- Auto-deploy stage: prod

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-apigateway-websocket
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create a WebSocket API with $connect, $disconnect,
      sendMessage, and joinRoom routes. Store connection IDs
      in DynamoDB. Add a Lambda authorizer on $connect."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create a websocket api"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
WEBSOCKET_API: my-chat-api (abc123def4)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] WebSocket API: abc123def4 (my-chat-api)
  [✓] Route selection expression: $request.body.action
  [✓] $connect route: conn-route → Lambda: ws-connect-handler (stores ConnectionId)
  [✓] $disconnect route: disc-route → Lambda: ws-disconnect-handler (deletes ConnectionId)
  [✓] Custom routes: sendMessage, joinRoom, leaveRoom
  [✓] Route responses (bidirectional): enabled on sendMessage
  [✓] Integration type: Lambda (AWS_PROXY)
  [✓] Deployment: auto-deploy on stage prod
  [✓] Connection management: DynamoDB WebSocketConnections (store on $connect, delete on $disconnect)
  [✓] Custom authorizer: ws-auth on $connect (identity source: $request.querystring.token)
  [✓] Keepalive: client-side application heartbeat (interval: 60s)
  [✓] Lambda resource-based policy: grants lambda:InvokeFunction to apigateway.amazonaws.com
  [✓] Message size limit: 128 KB
  [✓] Tags: Environment=production, Service=chat
VERIFICATION_COMMANDS:
  aws apigatewayv2 get-api --api-id abc123def4 --region us-east-1
  aws apigatewayv2 get-routes --api-id abc123def4 --region us-east-1
  aws apigatewayv2 get-stage --api-id abc123def4 --stage-name prod --region us-east-1
  aws dynamodb describe-table --table-name WebSocketConnections --region us-east-1
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Create the WebSocket API
API_ID=$(aws apigatewayv2 create-api \
  --name my-chat-api \
  --protocol-type WEBSOCKET \
  --route-selection-expression '$request.body.action' \
  --query 'ApiId' --output text \
  --region us-east-1)

echo "API ID: $API_ID"

# Step 2: Create integrations for each route
CONNECT_INT=$(aws apigatewayv2 create-integration \
  --api-id "$API_ID" \
  --integration-type AWS_PROXY \
  --integration-uri arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/arn:aws:lambda:us-east-1:111122223333:function:ws-connect-handler/invocations \
  --query 'IntegrationId' --output text \
  --region us-east-1)

DISCONNECT_INT=$(aws apigatewayv2 create-integration \
  --api-id "$API_ID" \
  --integration-type AWS_PROXY \
  --integration-uri arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/arn:aws:lambda:us-east-1:111122223333:function:ws-disconnect-handler/invocations \
  --query 'IntegrationId' --output text \
  --region us-east-1)

MESSAGE_INT=$(aws apigatewayv2 create-integration \
  --api-id "$API_ID" \
  --integration-type AWS_PROXY \
  --integration-uri arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/arn:aws:lambda:us-east-1:111122223333:function:ws-message-handler/invocations \
  --query 'IntegrationId' --output text \
  --region us-east-1)

# Step 3: Create routes
aws apigatewayv2 create-route \
  --api-id "$API_ID" --route-key '$connect' \
  --target "integrations/$CONNECT_INT" --region us-east-1

aws apigatewayv2 create-route \
  --api-id "$API_ID" --route-key '$disconnect' \
  --target "integrations/$DISCONNECT_INT" --region us-east-1

SEND_MSG_ROUTE=$(aws apigatewayv2 create-route \
  --api-id "$API_ID" --route-key 'sendMessage' \
  --target "integrations/$MESSAGE_INT" \
  --query 'RouteId' --output text --region us-east-1)

aws apigatewayv2 create-route \
  --api-id "$API_ID" --route-key 'joinRoom' \
  --target "integrations/$MESSAGE_INT" --region us-east-1

# Step 4: Create route response for bidirectional communication
aws apigatewayv2 create-route-response \
  --api-id "$API_ID" \
  --route-id "$SEND_MSG_ROUTE" \
  --route-response-key '$default' \
  --region us-east-1

# Step 5: Grant API Gateway permission to invoke Lambda
for fn in ws-connect-handler ws-disconnect-handler ws-message-handler; do
  aws lambda add-permission \
    --function-name "$fn" \
    --statement-id "apigateway-ws-invoke-$fn" \
    --action lambda:InvokeFunction \
    --principal apigateway.amazonaws.com \
    --source-arn "arn:aws:execute-api:us-east-1:111122223333:$API_ID/*/*" \
    --region us-east-1
done

# Step 6: Create auto-deploy stage
aws apigatewayv2 create-stage \
  --api-id "$API_ID" \
  --stage-name prod \
  --auto-deploy \
  --region us-east-1

# Step 7: Create DynamoDB connections table
aws dynamodb create-table \
  --table-name WebSocketConnections \
  --attribute-definitions AttributeName=connectionId,AttributeType=S \
  --key-schema AttributeName=connectionId,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

---

## Step 4 — Post-deployment verification

```bash
# Verify the WebSocket API
aws apigatewayv2 get-api --api-id abc123def4 --region us-east-1

# Verify routes
aws apigatewayv2 get-routes --api-id abc123def4 --region us-east-1

# Verify stage
aws apigatewayv2 get-stage --api-id abc123def4 --stage-name prod --region us-east-1

# Verify DynamoDB connections table
aws dynamodb describe-table --table-name WebSocketConnections --region us-east-1

# Verify Lambda permission
aws lambda get-policy --function-name ws-connect-handler --region us-east-1

# Test the WebSocket URL
echo "WebSocket URL: wss://abc123def4.execute-api.us-east-1.amazonaws.com/prod"
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Connection management | Not addressed | DynamoDB ConnectionId table on $connect/$disconnect | Without ConnectionId storage, server cannot push messages |
| Route selection expression | Omitted or guessed | Explicit $request.body.action matching client format | Without it, custom routes never fire |
| PostToConnection SDK | Uses ApiGatewayV2 | Uses ApiGatewayManagementApi with constructed endpoint | ApiGatewayV2 does not have PostToConnection |
| Usage plans | Tries to attach usage plan | Stage-level throttling only | WebSocket APIs do not support usage plans |
| Keepalive | Not addressed | Client-side heartbeat every 60s | Idle connections disconnect after 2 hours |
| Message size | Not checked | 128 KB limit noted | Messages >128 KB are rejected |
| Route responses | Not configured | create-route-response for bidirectional | Without it, no synchronous response to client |
| Lambda permissions | Not configured | add-permission for each function | Without it, integrations return 500 |
| Stale connections | Not handled | 410 Gone cleanup + DynamoDB TTL | Stale ConnectionIds accumulate without cleanup |
| Deployment | Forgets after route changes | Auto-deploy stage | Route changes need new deployment to take effect |

---

## Related artifacts

- **Skill definition:** `skills/apigateway-websocket-deployer/SKILL.md`
- **Routes and integrations guide:** `skills/apigateway-websocket-deployer/references/routes-and-integrations.md`
- **Connection management and auth guide:** `skills/apigateway-websocket-deployer/references/connection-management-and-auth.md`
- **Slash command:** `commands/aws/deploy-apigateway-websocket.md`
- **Eval suite:** `skills/apigateway-websocket-deployer/evals/evals.json`
- **Legacy test cases:** `skills/apigateway-websocket-deployer/eval/test-cases.yaml`
