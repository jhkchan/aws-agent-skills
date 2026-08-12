---
description: Provision an Amazon API Gateway WebSocket API with production-grade defaults (route selection expression, $connect/$disconnect routes, custom routes, route responses for bidirectional communication, Lambda integrations, DynamoDB connection management, Lambda custom authorizer, WAF, CloudWatch Logs, ping/pong keepalive). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create websocket api"
  - "deploy websocket api"
  - "websocket route selection"
  - "websocket connection management"
  - "lambda authorizer websocket"
  - "websocket deployment stage"
  - "bidirectional websocket"
  - "websocket ping pong"
  - "websocket dynamodb connections"
  - "websocket api gateway"
routes_to: apigateway-websocket-deployer
---

# /aws:deploy-apigateway-websocket

Activate the `apigateway-websocket-deployer` skill and provision an
Amazon API Gateway WebSocket API with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Route selection expression ($request.body.action)
2. Connection routes ($connect, $disconnect)
3. Custom routes (sendMessage, joinRoom, etc.)
4. Route responses (bidirectional communication)
5. Integration types (Lambda, AWS Service, Mock, HTTP)
6. Deployment and stage (auto-deploy)
7. Connection management (DynamoDB ConnectionId table)
8. Custom authorizer (Lambda on $connect)
9. CloudWatch Logs (execution + access logs)
10. WAF integration (connection-request filtering)
11. Ping/pong keepalive (2-hour idle disconnect)
12. Cross-account backend invocation
13. Message size limit (128 KB)

## When to use

- You need to create a WebSocket API for real-time communication.
- You need to configure route selection for message routing.
- You need to manage WebSocket connections (store/delete ConnectionIds).
- You need a Lambda custom authorizer for WebSocket auth.
- You need bidirectional communication via route responses.
- You need to deploy a WebSocket stage with throttling.
- You need WAF protection for WebSocket connections.

## When NOT to use

- **API Gateway REST API** — use apigateway-rest-deployer.
- **API Gateway HTTP API** — use apigateway-http-api-deployer.
- **AppSync subscriptions** — use AppSync skills for GraphQL
  subscriptions.
- **IoT Core** — use IoT skills for MQTT-based real-time.
- **SNS/SQS** — use messaging skills for async pub/sub.

## How to invoke

### Slash command

```
/aws:deploy-apigateway-websocket
```

Then provide: API name, route selection expression, route keys
($connect, $disconnect, custom), integration type (Lambda/HTTP/Mock),
connection management table (DynamoDB), authorizer Lambda (if auth),
keepalive strategy, stage name, tags.

### Natural language

Any of these routes to the same skill:

- "create a websocket api for real-time chat"
- "set up websocket connection management with dynamodb"
- "configure route selection expression for websocket"
- "add a lambda authorizer to my websocket api"
- "enable bidirectional communication on my websocket"

### CLI routing

```bash
node cli/bin/cli.js route "create a websocket api"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps
pipeline. The orchestrator routes to it when the user wants to
create WebSocket APIs. The output checklist feeds into verification
pipelines and downstream monitoring skills.

## Example

```
You: /aws:deploy-apigateway-websocket

     Create a WebSocket API named my-chat-api with $connect,
     $disconnect, and sendMessage routes. Store connection IDs
     in DynamoDB WebSocketConnections. Route selection
     $request.body.action. Auto-deploy to prod stage.

Skill:
  WEBSOCKET_API: my-chat-api (abc123def4)
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Route selection: $request.body.action
    [✓] $connect: stores ConnectionId in DynamoDB
    [✓] $disconnect: deletes ConnectionId from DynamoDB
    [✓] sendMessage: Lambda integration
    [✓] Auto-deploy stage: prod
  VERIFICATION_COMMANDS:
    aws apigatewayv2 get-api --api-id abc123def4 --region us-east-1
    aws apigatewayv2 get-routes --api-id abc123def4 --region us-east-1
```

## References

- Skill definition: `skills/apigateway-websocket-deployer/SKILL.md`
- Routes and integrations guide: `skills/apigateway-websocket-deployer/references/routes-and-integrations.md`
- Connection management and auth guide: `skills/apigateway-websocket-deployer/references/connection-management-and-auth.md`
- Eval suite: `skills/apigateway-websocket-deployer/evals/evals.json`
