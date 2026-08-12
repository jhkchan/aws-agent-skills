---
name: apigateway-websocket-deployer
description: >-
  Provisions Amazon API Gateway WebSocket APIs with production
  defaults: route selection expression ($request.body.action),
  connection routes ($connect, $disconnect), custom routes,
  route responses (two-way communication), integration types
  (Lambda, AWS Service, Mock, HTTP), deployment and stage
  management, connection-level throttling, CloudWatch Logs
  (execution + access logs), WAF integration, Lambda custom
  authorizers, backend connection management (DynamoDB
  ConnectionId table), ping/pong keepalive, cross-account
  backend invocation, and 128 KB message size limit. Emits a
  READY_TO_DEPLOY checklist with verification commands. Use
  when creating a WebSocket API, configuring route selection,
  managing WebSocket connections, setting up Lambda authorizers
  for WebSocket, deploying a WebSocket stage, or implementing
  bidirectional real-time communication. Triggers: create
  websocket api, configure route selection expression,
  websocket connection management, lambda authorizer websocket,
  websocket deployment stage, bidirectional communication api
  gateway, websocket ping pong keepalive.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor,
  Windsurf, Codex, Gemini). For live deployment: AWS CLI v2
  with apigateway / lambda / dynamodb access. Works with
  Terraform aws_apigatewayv2_api / aws_apigatewayv2_route /
  aws_apigatewayv2_integration / aws_apigatewayv2_deployment
  resources and CloudFormation AWS::ApiGatewayV2::Api templates.
keywords:
  - aws
  - api gateway
  - websocket
  - cloudops
  - deploy
  - provisioning
  - route selection
  - connection management
  - lambda authorizer
  - waf
  - bidirectional
  - real-time
  - dynamodb connections
  - ping pong
tags:
  - aws
  - api-gateway
  - websocket
  - cloudops
  - deploy
  - appintegration
  - provisioning
  - route-selection
  - connection-management
  - lambda-authorizer
  - waf
  - real-time
dependencies:
  - aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: AppIntegration
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  version: 0.1.0
  author: "Jacky Chan — AWS Community Builder"
  tags:
    - aws
    - api-gateway
    - websocket
    - cloudops
    - deploy
    - appintegration
    - provisioning
    - route-selection
    - connection-management
    - lambda-authorizer
    - waf
    - real-time
  dependencies:
    - aws-orchestrator
  keywords:
    - create websocket api
    - configure route selection expression
    - websocket connection management
    - lambda authorizer websocket
    - websocket deployment stage
    - bidirectional communication api gateway
    - websocket ping pong keepalive
  when_to_use: >-
    Invoke when the user wants to create an API Gateway WebSocket
    API, configure route selection expressions, manage WebSocket
    connections ($connect/$disconnect), set up Lambda custom
    authorizers for WebSocket auth, deploy a WebSocket stage,
    implement bidirectional real-time communication, configure
    connection management with DynamoDB, or integrate WAF with a
    WebSocket API. Do NOT invoke for API Gateway REST APIs or HTTP
    APIs (use apigateway-rest-deployer or apigateway-http-api-deployer),
    for AppSync subscriptions (use appsync skills), or for IoT Core
    (use iot skills).
---

# API Gateway WebSocket Deployer

An AWS CloudOps agent skill that provisions Amazon API Gateway
WebSocket APIs with correct defaults. The skill walks the route
selection expression, connection routes ($connect/$disconnect),
custom routes, route responses for bidirectional communication,
integration types (Lambda, AWS Service, Mock, HTTP), deployment and
stage management, connection-level throttling, CloudWatch Logs, WAF
integration, Lambda custom authorizers, backend connection
management (DynamoDB ConnectionId table), ping/pong keepalive,
cross-account backend invocation, and the 128 KB message size
limit, captures architecture decisions, explains why each default
matters, and emits a READY_TO_DEPLOY checklist with copy-pasteable
verification commands.

## Activation keywords

create WebSocket API, configure route selection expression,
WebSocket connection management, Lambda authorizer WebSocket,
WebSocket deployment stage, bidirectional communication API Gateway,
WebSocket ping pong keepalive, WebSocket $connect $disconnect,
WebSocket DynamoDB connections.

## STRICT output contract

When this skill is invoked with a WebSocket-API-provisioning
request (create a WebSocket API, configure routes, set up
connection management, deploy a stage, configure authorizers, or a
partial configuration), the agent MUST respond with the
READY_TO_DEPLOY checklist defined in the "Output format" section
using the literal all-caps labels `WEBSOCKET_API:`, `VERDICT:`,
`CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT preface the
checklist with prose, headings, or disclaimers — emit the block as
the first lines of the response. This contract is what
assertion-based evals and downstream provisioning pipelines rely
on; deviating from the literal labels breaks automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Route selection expression | Core routing model |
| Step 2 — Connection routes ($connect, $disconnect) | Connection lifecycle |
| Step 3 — Custom routes | Message routing |
| Step 4 — Route responses (bidirectional) | Two-way communication |
| Step 5 — Integration types | Backend connection |
| Step 6 — Deployment and stage | Publishing the API |
| Step 7 — Connection management (DynamoDB) | Stateful connections |
| Step 8 — Custom authorizer (Lambda) | Authentication |
| Step 9 — CloudWatch Logs | Observability |
| Step 10 — WAF integration | Security |
| Step 11 — Ping/pong keepalive | Connection health |
| Step 12 — Cross-account backend invocation | Multi-account |
| Step 13 — Message size limit (128 KB) | Limits |
| Step 14 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/routes-and-integrations.md | Routes + integrations detail |
| references/connection-management-and-auth.md | Connections + auth detail |

## Mindset

**One-line takeaway:** An API Gateway WebSocket API is a
stateful, bidirectional, real-time communication endpoint. The
route selection expression evaluates each incoming message's body
to determine which route (and integration) handles it. Connection
management is YOUR application's responsibility — store the
ConnectionId on $connect, use it to send messages back via the
PostToConnection API, and delete it on $disconnect. Idle
connections auto-disconnect after 2 hours.

Five misconceptions dominate WebSocket API misdesign at provisioning
time:

- **"The WebSocket API manages connections for me."** It does not.
  API Gateway maintains the WebSocket connection at the transport
  level, but the APPLICATION is responsible for tracking
  ConnectionIds. On $connect, you must store the ConnectionId (e.g.,
  in DynamoDB). To send a message to a client, you use the
  ConnectionId with the PostToConnection API (via the
  ApiGatewayManagementApi SDK). On $disconnect, you delete the
  ConnectionId. A baseline model that skips connection management
  produces an API where clients can connect but the server cannot
  push messages back.

- **"Route selection expression is optional."** It is not. The
  route selection expression tells API Gateway which route to
  invoke for each incoming message. The default
  `$request.body.action` evaluates the `action` field in the JSON
  message body. Without a route selection expression, ALL messages
  go to the `$default` route (or are rejected if no `$default`
  exists). A baseline model that omits the route selection
  expression produces a WebSocket API where custom routes never
  fire.

- **"Usage plans and API keys work the same as REST APIs."** They
  do not. WebSocket APIs do not support usage plans or API keys
  directly. Throttling is done at the connection level via stage
  settings. For per-client throttling, implement it in the backend
  using the ConnectionId. A baseline model that tries to attach a
  usage plan to a WebSocket API will fail.

- **"WebSocket connections persist indefinitely."** They do not.
  API Gateway WebSocket connections idle-disconnect after **2 hours**
  (7200 seconds). Long-lived connections must implement ping/pong
  keepalive to prevent disconnection. The client or the server
  must send periodic ping frames or application-level heartbeat
  messages. A baseline model that does not implement keepalive
  will see connections drop after 2 hours of inactivity.

- **"Messages can be any size."** They cannot. The maximum message
  size for WebSocket API messages is **128 KB** (per frame).
  Messages larger than 128 KB are rejected. For large payloads,
  chunk them into multiple messages or offload to S3 and send a
  reference. A baseline model that sends large JSON payloads will
  hit the 128 KB limit silently.

## Configuration dependency graph (novel heuristic)

WebSocket API configurations are NOT independent. The API must be
created before routes. Routes must reference integrations.
Deployment requires at least one route. Stage references a
deployment. Connection management requires a backend data store.
Use this graph to sequence provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| WebSocket API creation | None (creates the API container) | API has no routes until routes are added; RouteSelectionExpression set at creation | the API container |
| Route selection expression | WebSocket API exists | set at API creation; changing requires update-api; without it ALL messages go to $default | message routing to custom routes |
| $connect route | WebSocket API exists; integration exists (Lambda/HTTP/AWS) | fires on every new WebSocket connection; ConnectionId available in event | connection lifecycle entry |
| $disconnect route | WebSocket API exists; integration exists | fires on connection close (clean or idle timeout); ConnectionId in event | connection lifecycle exit |
| Custom route | WebSocket API exists; route selection expression set; integration exists | route key must match what the selection expression evaluates to (e.g., action=sendMessage → route "sendMessage") | message-type-specific handling |
| Integration (Lambda) | Lambda function exists; resource-based policy grants apigateway invoke permission | Lambda invoked synchronously; timeout 30s max for WebSocket integrations | backend processing |
| Deployment | At least one route exists | deployment is immutable snapshot; must create new deployment after route changes | versioned API snapshot |
| Stage | Deployment exists | stage name becomes part of the WebSocket URL; auto-deploy stage does NOT auto-create on first deploy | the client-facing endpoint |
| Connection management | DynamoDB table (or equivalent) exists; $connect handler stores ConnectionId | without ConnectionId storage, server CANNOT push messages to clients | bidirectional communication |
| Custom authorizer | Authorizer Lambda function exists; attached to $connect route | fires BEFORE the $connect integration; if denied, connection rejected | authenticated connections |
| WAF Web ACL | WebSocket API stage exists | WAF inspects connection requests; does NOT inspect individual WebSocket frames after connection | connection-level filtering |

**The connection-management row is the one a baseline model misses.**
A baseline model creates the WebSocket API, routes, integrations,
deployment, and stage — but does not address how the backend tracks
ConnectionIds. Without storing ConnectionIds on $connect, the server
cannot send messages to specific clients via PostToConnection. The
procedure below forces an explicit connection-management decision.

**Cross-dependency gotchas:**
- Route changes require a new deployment. Without re-deploying, route
  changes are NOT live. Auto-deploy stages handle this automatically.
- The $connect route fires BEFORE the connection is fully
  established. If the $connect integration returns a non-2xx status,
  the connection is rejected. This is where custom authorizers run.
- PostToConnection uses the ApiGatewayManagementApi SDK (NOT the
  ApiGatewayV2 SDK). The endpoint URL format is
  `https://{api-id}.execute-api.{region}.amazonaws.com/{stage}`.
- Lambda integrations for WebSocket have a 30-second timeout
  (regardless of the function's configured timeout).
- The DynamoDB ConnectionId table must be in the same region as the
  WebSocket API for lowest latency.

## Expert heuristic: the connection management lifecycle

A baseline model says "create routes and deploy." The correct
heuristic recognizes that WebSocket communication is bidirectional,
and the server needs ConnectionIds to push messages to clients.

```text
WebSocket connection lifecycle:

1. Client connects:
   Client → wss://{api-id}.execute-api.{region}.amazonaws.com/{stage}
   → $connect route fires
   → Lambda integration stores ConnectionId in DynamoDB
   → Connection established (HTTP 101 Switching Protocols)

2. Client sends message:
   Client → { "action": "sendMessage", "data": "hello" }
   → Route selection expression evaluates: $request.body.action = "sendMessage"
   → "sendMessage" route fires → Lambda integration
   → Lambda reads ConnectionId(s) from DynamoDB
   → Lambda calls PostToConnection to deliver message to recipient(s)

3. Client or server disconnects:
   → $disconnect route fires
   → Lambda integration deletes ConnectionId from DynamoDB
   → Connection closed

4. Idle timeout (no traffic for 2 hours):
   → API Gateway auto-disconnects
   → $disconnect route fires
   → Lambda integration deletes ConnectionId from DynamoDB
```

**Key implication:** without storing ConnectionIds in DynamoDB (or
equivalent), the server CANNOT push messages to clients. This is
the #1 cause of "my WebSocket API can receive but not send" issues.

## Expert heuristic: route selection expression mechanics

The route selection expression is a Velocity Template Language (VTL)
expression that evaluates the incoming message body to produce a
route key. The route key determines which route handles the message.

```text
Default: $request.body.action
  Input: { "action": "sendMessage", "message": "hello" }
  Evaluation: $request.body.action → "sendMessage"
  Route invoked: "sendMessage"

Custom: $request.body.type
  Input: { "type": "chat", "payload": "hello" }
  Evaluation: $request.body.type → "chat"
  Route invoked: "chat"

No selection expression (or empty body without $default):
  Input: { "message": "hello" }
  Evaluation: no "action" field → null
  Route invoked: none → message rejected (or $default if configured)
```

**Key implication:** the route selection expression MUST match the
message format the client sends. If clients send `{ "type": "..." }`
but the expression evaluates `$request.body.action`, custom routes
never fire. Verify the expression matches the client message format.

## Expert heuristic: idle disconnect and keepalive

API Gateway WebSocket connections auto-disconnect after **2 hours**
(7200 seconds) of inactivity. This is a hard limit that cannot be
configured. To maintain long-lived connections, implement keepalive.

```text
Keepalive strategies:

1. Client-side ping (recommended):
   Client sends periodic ping frame (WebSocket protocol-level ping)
   every 30-60 seconds
   → API Gateway responds with pong frame (resetting idle timer)
   → Connection stays alive

2. Application-level heartbeat:
   Client sends { "action": "ping" } every 30-60 seconds
   → Server responds with { "type": "pong" }
   → Connection stays alive (any traffic resets idle timer)

3. Server-side heartbeat:
   Server calls PostToConnection with heartbeat message
   every 30-60 seconds per active ConnectionId
   → More expensive ( Lambda invocations + DynamoDB reads)
```

**Key implication:** without keepalive, connections drop after 2
hours. The $disconnect route fires (cleaning up DynamoDB), but the
client must reconnect. For chat/real-time applications, implement
client-side ping or application-level heartbeat.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites.
If any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Route selection expression designed | Determines message routing; must match client message format | Confirm the expression (e.g., `$request.body.action`) |
| Lambda function for integrations | Backend handler for $connect, $disconnect, custom routes | `aws lambda get-function --function-name <name>` |
| DynamoDB table for ConnectionId storage | Without ConnectionId tracking, server cannot push messages | `aws dynamodb describe-table --table-name <name>` |
| Lambda resource-based policy | API Gateway needs `lambda:InvokeFunction` permission | `aws lambda get-policy --function-name <name>` |
| Authorizer Lambda function (if custom auth) | For authenticated WebSocket connections | Verify function exists |
| IAM execution role for Lambda | Lambda needs DynamoDB + ApiGatewayManagementApi permissions | Verify role has required policies |
| Region identified | WebSocket API and DynamoDB should be co-located | Confirm region |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Route selection expression

The route selection expression is set at API creation time. It
determines which route handles each incoming message.

```bash
# Create a WebSocket API with route selection expression
aws apigatewayv2 create-api \
  --name "my-websocket-api" \
  --protocol-type WEBSOCKET \
  --route-selection-expression '$request.body.action' \
  --region us-east-1
```

The response includes the `ApiId`, which is used in all subsequent
commands.

**Common expressions:**

| Expression | Message format | Route key |
|---|---|---|
| `$request.body.action` | `{ "action": "sendMessage", ... }` | `sendMessage` |
| `$request.body.type` | `{ "type": "chat", ... }` | `chat` |
| `$request.body.routeKey` | `{ "routeKey": "joinRoom", ... }` | `joinRoom` |

**Update the route selection expression:**

```bash
aws apigatewayv2 update-api \
  --api-id abc123def4 \
  --route-selection-expression '$request.body.type' \
  --region us-east-1
```

**Critical:** changing the route selection expression requires a new
deployment for the change to take effect (unless using auto-deploy
stage).

## Step 2 — Connection routes ($connect, $disconnect)

WebSocket APIs have two built-in routes for connection lifecycle:

| Route | When it fires | Use case |
|---|---|---|
| `$connect` | Client opens WebSocket connection | Store ConnectionId, authenticate |
| `$disconnect` | Client or server closes connection | Delete ConnectionId, cleanup |

**Create the $connect route:**

```bash
aws apigatewayv2 create-route \
  --api-id abc123def4 \
  --route-key '$connect' \
  --target integrations/abc123 \
  --region us-east-1
```

**Create the $disconnect route:**

```bash
aws apigatewayv2 create-route \
  --api-id abc123def4 \
  --route-key '$disconnect' \
  --target integrations/def456 \
  --region us-east-1
```

**$connect event structure (Lambda):**

```json
{
  "requestContext": {
    "routeKey": "$connect",
    "connectionId": "abc123=-",
    "apiId": "abc123def4",
    "domainName": "abc123def4.execute-api.us-east-1.amazonaws.com",
    "stage": "prod"
  },
  "queryStringParameters": {
    "token": "user-auth-token"
  },
  "headers": {
    "Authorization": "Bearer ..."
  }
}
```

The `connectionId` is the unique identifier for this connection. It
must be stored on $connect and used for PostToConnection later.

**$disconnect event structure (Lambda):**

```json
{
  "requestContext": {
    "routeKey": "$disconnect",
    "connectionId": "abc123=-",
    "disconnectReason": "CLIENT_INITIATED",
    "eventType": "DISCONNECT"
  }
}
```

**Critical:** the $connect integration response determines whether
the connection is accepted. A 2xx status accepts the connection;
a non-2xx status rejects it. This is where custom authorizers or
authentication checks run.

## Step 3 — Custom routes

Custom routes handle specific message types based on the route
selection expression. Each route maps to an integration.

```bash
# Create a "sendMessage" route
aws apigatewayv2 create-route \
  --api-id abc123def4 \
  --route-key 'sendMessage' \
  --target integrations/ghi789 \
  --region us-east-1

# Create a "joinRoom" route
aws apigatewayv2 create-route \
  --api-id abc123def4 \
  --route-key 'joinRoom' \
  --target integrations/jkl012 \
  --region us-east-1

# Create a "$default" route (handles unmatched messages)
aws apigatewayv2 create-route \
  --api-id abc123def4 \
  --route-key '$default' \
  --target integrations/mno345 \
  --region us-east-1
```

When a client sends `{ "action": "sendMessage", "message": "hello" }`,
the route selection expression evaluates `$request.body.action` =
`sendMessage`, and the `sendMessage` route fires.

**Custom route event structure (Lambda):**

```json
{
  "requestContext": {
    "routeKey": "sendMessage",
    "connectionId": "abc123=-",
    "apiId": "abc123def4",
    "domainName": "abc123def4.execute-api.us-east-1.amazonaws.com",
    "stage": "prod"
  },
  "body": "{\"action\":\"sendMessage\",\"message\":\"hello\"}"
}
```

The `body` contains the raw message. Parse it in the Lambda handler.

## Step 4 — Route responses (bidirectional communication)

By default, WebSocket routes do NOT return responses to the client
(unless the integration returns a non-2xx status for $connect). To
enable two-way communication (route response), create a route
response.

```bash
# Create a route response for the "sendMessage" route
aws apigatewayv2 create-route-response \
  --api-id abc123def4 \
  --route-id xyz789 \
  --route-response-key '$default' \
  --region us-east-1
```

With a route response configured, the Lambda integration can return
a response that is sent back to the client over the same WebSocket
connection.

**Lambda handler returning a route response:**

```javascript
exports.handler = async (event) => {
  const body = JSON.parse(event.body);
  
  // Process the message...
  
  // Return response (sent back to client via route response)
  return {
    statusCode: 200,
    body: JSON.stringify({ type: "ack", messageId: body.messageId })
  };
};
```

**Key point:** route responses are NOT push notifications. They are
synchronous responses to the client's message. For server-initiated
push messages, use PostToConnection (Step 7).

## Step 5 — Integration types

WebSocket APIs support four integration types:

| Integration | Use case | Async/Sync | Timeout |
|---|---|---|---|
| Lambda | Custom backend logic | Sync | 30s max |
| AWS Service | Direct AWS service call (e.g., SQS, Kinesis) | Sync/Async | Service-dependent |
| Mock | Return a fixed response without backend | Sync | N/A |
| HTTP | Forward to an HTTP endpoint | Sync | 30s max |

**Create a Lambda integration:**

```bash
aws apigatewayv2 create-integration \
  --api-id abc123def4 \
  --integration-type AWS_PROXY \
  --integration-uri arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/arn:aws:lambda:us-east-1:111122223333:function:ws-handler/invocations \
  --region us-east-1
```

**Create an HTTP integration:**

```bash
aws apigatewayv2 create-integration \
  --api-id abc123def4 \
  --integration-type HTTP_PROXY \
  --integration-uri https://backend.example.com/websocket \
  --integration-method POST \
  --region us-east-1
```

**Create a Mock integration:**

```bash
aws apigatewayv2 create-integration \
  --api-id abc123def4 \
  --integration-type MOCK \
  --region us-east-1
```

**Grant API Gateway permission to invoke Lambda:**

```bash
aws lambda add-permission \
  --function-name ws-handler \
  --statement-id apigateway-ws-invoke \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn arn:aws:execute-api:us-east-1:111122223333:abc123def4/*/sendMessage \
  --region us-east-1
```

**Critical:** without the resource-based policy granting
`lambda:InvokeFunction` to `apigateway.amazonaws.com`, API Gateway
cannot invoke the Lambda function. Integration returns 500.

## Step 6 — Deployment and stage

After creating routes and integrations, create a deployment and
stage. The deployment is an immutable snapshot; the stage is the
client-facing environment.

```bash
# Create a deployment
aws apigatewayv2 create-deployment \
  --api-id abc123def4 \
  --region us-east-1

# Create a stage
aws apigatewayv2 create-stage \
  --api-id abc123def4 \
  --stage-name prod \
  --deployment-id <deployment-id-from-previous-command> \
  --region us-east-1
```

**WebSocket URL format:**

```text
wss://{api-id}.execute-api.{region}.amazonaws.com/{stage}
```

Example: `wss://abc123def4.execute-api.us-east-1.amazonaws.com/prod`

**Auto-deploy stage (recommended):**

```bash
aws apigatewayv2 create-stage \
  --api-id abc123def4 \
  --stage-name prod \
  --auto-deploy \
  --region us-east-1
```

With `--auto-deploy`, route and integration changes are automatically
deployed without creating explicit deployments.

**Stage-level throttling:**

```bash
aws apigatewayv2 update-stage \
  --api-id abc123def4 \
  --stage-name prod \
  --default-route-settings '{
    "ThrottlingBurstLimit": 500,
    "ThrottlingRateLimit": 1000,
    "DataTraceEnabled": false,
    "LoggingLevel": "INFO"
  }' \
  --region us-east-1
```

**Critical:** WebSocket APIs do NOT support usage plans or API keys.
Throttling is configured at the stage level via route settings.

## Step 7 — Connection management (DynamoDB)

Connection management is the APPLICATION'S responsibility. The
standard pattern uses DynamoDB to store ConnectionIds.

**DynamoDB table for connections:**

```bash
aws dynamodb create-table \
  --table-name WebSocketConnections \
  --attribute-definitions AttributeName=connectionId,AttributeType=S \
  --key-schema AttributeName=connectionId,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

**$connect handler (store ConnectionId):**

```javascript
const AWS = require('aws-sdk');
const dynamo = new AWS.DynamoDB.DocumentClient();
const TABLE_NAME = process.env.CONNECTIONS_TABLE;

exports.handler = async (event) => {
  const connectionId = event.requestContext.connectionId;
  
  // Store the connection
  await dynamo.put({
    TableName: TABLE_NAME,
    Item: {
      connectionId: connectionId,
      timestamp: Date.now(),
      userId: event.queryStringParameters.userId || 'anonymous'
    }
  }).promise();
  
  return { statusCode: 200 };
};
```

**$disconnect handler (delete ConnectionId):**

```javascript
exports.handler = async (event) => {
  const connectionId = event.requestContext.connectionId;
  
  await dynamo.delete({
    TableName: TABLE_NAME,
    Key: { connectionId: connectionId }
  }).promise();
  
  return { statusCode: 200 };
};
```

**Sending messages to clients (PostToConnection):**

```javascript
const AWS = require('aws-sdk');

// IMPORTANT: Use ApiGatewayManagementApi, NOT ApiGatewayV2
const endpoint = event.requestContext.domainName + '/' + event.requestContext.stage;
const managementApi = new AWS.ApiGatewayManagementApi({
  apiVersion: '2018-11-29',
  endpoint: endpoint
});

async function sendMessage(connectionId, data) {
  try {
    await managementApi.postToConnection({
      ConnectionId: connectionId,
      Data: JSON.stringify(data)
    }).promise();
  } catch (err) {
    if (err.statusCode === 410) {
      // Connection is gone (client disconnected without $disconnect)
      await dynamo.delete({
        TableName: TABLE_NAME,
        Key: { connectionId: connectionId }
      }).promise();
    } else {
      throw err;
    }
  }
}
```

**Critical:** the ApiGatewayManagementApi endpoint is
`https://{api-id}.execute-api.{region}.amazonaws.com/{stage}`. It
must be constructed from the event's `domainName` and `stage`. The
SDK does NOT auto-detect the endpoint.

## Step 8 — Custom authorizer (Lambda)

A Lambda custom authorizer authenticates WebSocket connections at
the $connect route. The authorizer runs BEFORE the $connect
integration.

**Create a Lambda authorizer:**

```bash
aws apigatewayv2 create-authorizer \
  --api-id abc123def4 \
  --authorizer-type REQUEST \
  --authorizer-uri arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/arn:aws:lambda:us-east-1:111122223333:function:ws-auth/invocations \
  --identity-source '$request.querystring.token' \
  --authorizer-result-ttl-in-seconds 300 \
  --name "ws-auth" \
  --region us-east-1
```

**Attach the authorizer to the $connect route:**

```bash
aws apigatewayv2 update-route \
  --api-id abc123def4 \
  --route-id <connect-route-id> \
  --authorizer-id <authorizer-id> \
  --authorization-type CUSTOM \
  --region us-east-1
```

**Authorizer Lambda handler:**

```javascript
exports.handler = async (event) => {
  const token = event.queryStringParameters.token;
  
  // Validate token
  const isValid = await validateToken(token);
  
  if (!isValid) {
    return {
      isAuthorized: false
    };
  }
  
  return {
    isAuthorized: true,
    context: {
      userId: token.userId
    }
  };
};
```

**Key point:** the authorizer returns `{ isAuthorized: boolean }`.
If `false`, the connection is rejected (HTTP 403 on $connect). If
`true`, the connection proceeds. The `context` object is available
in the $connect integration's event.

## Step 9 — CloudWatch Logs

WebSocket APIs support two types of CloudWatch Logs:

| Log type | Description | Configuration |
|---|---|---|
| Execution logs | Log API Gateway execution details (requests, responses) | Stage-level `--default-route-settings LoggingLevel` |
| Access logs | Log access information to CloudWatch Logs in JSON | Stage-level `--access-log-settings` |

**Enable execution logs:**

```bash
aws apigatewayv2 update-stage \
  --api-id abc123def4 \
  --stage-name prod \
  --default-route-settings '{
    "DataTraceEnabled": true,
    "LoggingLevel": "INFO"
  }' \
  --region us-east-1
```

`LoggingLevel` can be `OFF`, `INFO`, or `ERROR`. `DataTraceEnabled`
includes full request/response payloads (use with caution for
sensitive data).

**Enable access logs:**

```bash
aws apigatewayv2 update-stage \
  --api-id abc123def4 \
  --stage-name prod \
  --access-log-settings '{
    "DestinationArn": "arn:aws:logs:us-east-1:111122223333:log-group:/aws/apigateway/ws-api",
    "Format": "{\"requestId\":\"$context.requestId\",\"connectionId\":\"$context.connectionId\",\"routeKey\":\"$context.routeKey\",\"status\":$context.status,\"time\":$context.time}"
  }' \
  --region us-east-1
```

## Step 10 — WAF integration

AWS WAF can be attached to a WebSocket API to filter connection
requests. WAF inspects the initial HTTP upgrade request (the
WebSocket handshake) but does NOT inspect individual WebSocket
frames after the connection is established.

**Attach WAF to the WebSocket API:**

```bash
# Associate WAF Web ACL with the API (via the API stage ARN)
aws wafv2 associate-web-acl \
  --web-acl-arn arn:aws:wafv2:us-east-1:111122223333:regional/webacl/ws-waf/abc123 \
  --resource-arn arn:aws:apigateway:us-east-1::/restapis/abc123def4/stages/prod \
  --region us-east-1
```

**WAF rule examples for WebSocket:**

- IP-based filtering (allow/block specific IPs for connections)
- Rate-based rules (limit connections per IP)
- Geographic restrictions (allow/block countries)
- Header inspection (validate auth headers on connection)

**Key limitation:** WAF only inspects the initial connection
request (HTTP upgrade). Messages sent after connection are NOT
inspected by WAF. For message-level filtering, implement it in the
backend.

## Step 11 — Ping/pong keepalive

API Gateway WebSocket connections auto-disconnect after 2 hours of
inactivity. Implement keepalive to maintain long-lived connections.

**Client-side WebSocket ping (recommended):**

```javascript
// Browser WebSocket API automatically handles ping/pong at protocol level
// But not all browsers send periodic pings. Implement application-level heartbeat:

const ws = new WebSocket('wss://abc123def4.execute-api.us-east-1.amazonaws.com/prod');

// Send heartbeat every 60 seconds
setInterval(() => {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ action: 'ping' }));
  }
}, 60000);
```

**Server-side heartbeat response:**

```javascript
// In the "ping" route handler
exports.handler = async (event) => {
  return {
    statusCode: 200,
    body: JSON.stringify({ type: 'pong', timestamp: Date.now() })
  };
};
```

**Important:** any traffic on the connection resets the idle timer.
This includes the client sending a message, the server sending a
message via PostToConnection, or protocol-level ping/pong frames.

## Step 12 — Cross-account backend invocation

If the Lambda function (or other backend) is in a different AWS
account from the WebSocket API, configure cross-account invocation.

```bash
# In the Lambda account: grant API Gateway account permission to invoke
aws lambda add-permission \
  --function-name ws-handler \
  --statement-id apigateway-cross-account \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn arn:aws:execute-api:us-east-1:<api-account-id>:abc123def4/*/* \
  --region us-east-1
```

The `--source-arn` must include the API account's account ID to
scope the permission to this specific API.

## Step 13 — Message size limit (128 KB)

The maximum message size for WebSocket API messages is **128 KB**
(131,072 bytes) per frame. Messages larger than 128 KB are rejected
with a 413 Payload Too Large error.

**Implications:**
- JSON payloads must be under 128 KB. Large objects should be
  offloaded to S3 and a reference (URL) sent via WebSocket.
- Binary data must be base64-encoded (which increases size by ~33%),
  effectively limiting binary payloads to ~96 KB pre-encoding.
- For large data transfers, chunk messages into multiple frames
  under 128 KB each.

**Message size verification:**

```javascript
// Client-side check before sending
const message = JSON.stringify({ action: 'sendData', data: largePayload });
if (message.length > 128 * 1024) {
  // Chunk or offload to S3
  console.error('Message exceeds 128 KB limit');
}
```

## Step 14 — Recent features

**Recent AWS features (2023-2026):**

- **Auto-deploy stages (2023-2024):** WebSocket stages now support
  `--auto-deploy`, eliminating the need to create explicit
  deployments after route or integration changes. Changes are
  deployed automatically within seconds.

- **WebSocket API private integrations (2023-2024):** Enhanced
  support for private integrations (VPC link) allowing WebSocket
  APIs to route to backends in private VPCs without public
  internet exposure.

- **WAF WebSocket enhancements (2024-2025):** AWS WAF added
  WebSocket-specific rule conditions, allowing finer-grained
  connection-request filtering (header-based, query-parameter-based,
  and body inspection for the initial handshake).

- **ApiGatewayManagementApi SDK improvements (2024-2025):** The
  SDK now supports batch PostToConnection calls, reducing per-
  connection Lambda invocations for broadcast scenarios.

- **CloudWatch metrics for WebSocket APIs (2024-2025):** Enhanced
  metrics including `ConnectCount`, `DisconnectCount`,
  `MessageCount`, `ExecutionErrorCount`, and `ClientErrorCount`
  for better observability of WebSocket API health.

- **WebSocket API tagging and cost allocation (2024-2025):**
  WebSocket APIs now support resource-level tagging for cost
  allocation and governance across multiple APIs and stages.

## NEVER do these things

1. **NEVER skip connection management.** The APPLICATION must store
   ConnectionIds (e.g., in DynamoDB) on $connect and delete them on
   $disconnect. Without this, the server cannot push messages to
   clients via PostToConnection.

2. **NEVER omit the route selection expression.** Without it, ALL
   messages go to $default (or are rejected). The expression must
   match the client's message format (e.g., `$request.body.action`
   requires an `action` field in the message body).

3. **NEVER try to attach a usage plan to a WebSocket API.** WebSocket
   APIs do not support usage plans or API keys. Throttling is done
   at the stage level via route settings.

4. **NEVER forget to re-deploy after route changes.** Route and
   integration changes require a new deployment (unless using
   auto-deploy stages). Without re-deployment, changes are NOT live.

5. **NEVER use the ApiGatewayV2 SDK for PostToConnection.** Use the
   `ApiGatewayManagementApi` SDK (`AWS.ApiGatewayManagementApi`).
   The ApiGatewayV2 SDK does not have PostToConnection. The endpoint
   must be constructed from `event.requestContext.domainName + '/' +
   event.requestContext.stage`.

6. **NEVER assume WebSocket connections persist indefinitely.** Idle
   connections auto-disconnect after 2 hours (7200 seconds).
   Implement keepalive (client-side ping or application-level
   heartbeat) for long-lived connections.

7. **NEVER send messages larger than 128 KB.** The per-frame limit
   is 128 KB. Messages exceeding this are rejected (413). Chunk
   large payloads or offload to S3.

8. **NEVER forget to grant `lambda:InvokeFunction` to
   `apigateway.amazonaws.com`.** Without the resource-based policy,
   API Gateway cannot invoke the Lambda function and integrations
   return 500.

9. **NEVER confuse route responses with push notifications.** Route
   responses are synchronous replies to the client's message. For
   server-initiated push messages, use PostToConnection with the
   stored ConnectionId.

10. **NEVER skip the 410 Gone handling in PostToConnection.** A 410
    status means the connection is gone (client disconnected without
    $disconnect firing). Delete the stale ConnectionId from DynamoDB.
    Without this handling, stale connections accumulate.

## Output format

```text
WEBSOCKET_API: <api-name> (<api-id>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] WebSocket API: <api-id> (<name>)
  [✓|✗] Route selection expression: $request.body.<field>
  [✓|✗] $connect route: <route-id> → <integration> (Lambda: <function-name>)
  [✓|✗] $disconnect route: <route-id> → <integration> (Lambda: <function-name>)
  [✓|✗] Custom routes: <route-key-list>
  [✓|✗] Route responses (bidirectional): enabled on <route-key-list> | disabled
  [✓|✗] Integration type: Lambda | AWS Service | Mock | HTTP
  [✓|✗] Deployment: <deployment-id> on stage <stage-name>
  [✓|✗] Connection management: DynamoDB <table-name> (store on $connect, delete on $disconnect)
  [✓|✗] Custom authorizer (if applicable): <authorizer-name> on $connect
  [✓|✗] CloudWatch Logs: execution (INFO), access (log group: <name>)
  [✓|✗] WAF (if applicable): <web-acl-name> on stage <stage-name>
  [✓|✗] Keepalive: <strategy> (interval: <n>s)
  [✓|✗] Lambda resource-based policy: grants lambda:InvokeFunction to apigateway.amazonaws.com
  [✓|✗] Message size limit: 128 KB
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws apigatewayv2 get-api --api-id <api-id> --region <region>
  aws apigatewayv2 get-routes --api-id <api-id> --region <region>
  aws apigatewayv2 get-stage --api-id <api-id> --stage-name <stage> --region <region>
  aws lambda get-policy --function-name <function-name> --region <region>
  aws dynamodb describe-table --table-name <connections-table> --region <region>
```

### Worked example — chat WebSocket API with Lambda, DynamoDB, and authorizer

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
  [✓] Custom authorizer: ws-auth on $connect (token from query string)
  [✓] CloudWatch Logs: execution (INFO), access (log group: /aws/apigateway/ws-chat)
  [✓] Keepalive: client-side application heartbeat (interval: 60s)
  [✓] Lambda resource-based policy: grants lambda:InvokeFunction to apigateway.amazonaws.com
  [✓] Message size limit: 128 KB
  [✓] Tags: Environment=production, Service=chat
VERIFICATION_COMMANDS:
  aws apigatewayv2 get-api --api-id abc123def4 --region us-east-1
  aws apigatewayv2 get-routes --api-id abc123def4 --region us-east-1
  aws apigatewayv2 get-stage --api-id abc123def4 --stage-name prod --region us-east-1
  aws lambda get-policy --function-name ws-connect-handler --region us-east-1
  aws dynamodb describe-table --table-name WebSocketConnections --region us-east-1
```

## Error handling

### Connections not receiving server-pushed messages
- ConnectionId not stored in DynamoDB on $connect. Verify the
  $connect handler stores the ConnectionId. Check DynamoDB for the
  connection.

### Custom routes never fire
- Route selection expression does not match the client message
  format. If clients send `{ "type": "..." }` but the expression
  evaluates `$request.body.action`, routes never match. Verify the
  expression.

### Integrations return 500
- Lambda resource-based policy missing. Verify
  `lambda:InvokeFunction` is granted to `apigateway.amazonaws.com`
  with the correct source ARN. Use `aws lambda get-policy`.

### PostToConnection returns 410 Gone
- The client disconnected without $disconnect firing (e.g.,
  network failure). Delete the stale ConnectionId from DynamoDB.
  The 410 is expected; handle it gracefully.

### Connections drop after 2 hours
- Idle timeout. Implement keepalive (client-side ping or
  application-level heartbeat every 30-60 seconds).

### Large messages rejected (413)
- Message exceeds the 128 KB limit. Chunk the payload or offload
  to S3 and send a reference URL via WebSocket.

## Domain

AWS CloudOps / Amazon API Gateway WebSocket API Provisioning &
Real-Time Communication.

## AWS documentation

- **API Gateway WebSocket APIs** — https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-websocket-api.html
- **Creating a WebSocket API** — https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-create-websocket-api.html
- **Route selection expressions** — https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-websocket-api-route-expressions.html
- **WebSocket API routes** — https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-websocket-api-routes.html
- **WebSocket API integrations** — https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-websocket-api-integrations.html
- **Managing WebSocket connections** — https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-how-to-call-websocket-api.html
- **ApiGatewayManagementApi** — https://docs.aws.amazon.com/AWSJavaScriptSDK/latest/AWS/ApiGatewayManagementApi.html
- **WebSocket API deployment** — https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-websocket-api-deploy.html
- **WebSocket API limits** — https://docs.aws.amazon.com/apigateway/latest/developerguide/limits.html
- **WAF and API Gateway** — https://docs.aws.amazon.com/waf/latest/developerguide/cloudfront-managed-rule-groups.html
