---
name: apigateway-websocket-deployer
description: 'Provisions Amazon API Gateway WebSocket APIs with production defaults: route selection expression ($request.body.action), connection routes ($connect, $disconnect), custom routes, route responses (two-way communication), integration types (Lambda, AWS Service, Mock, HTTP), deployment and stage management, connection-level throttling, CloudWatch Logs (execution + access logs), WAF integration, Lambda custom authorizers, backend connection management (DynamoDB ConnectionId table), ping/pong keepalive, cross-account backend invocation, and 128 KB message size limit. Emits a READY_TO_DEPLOY checklist with verification commands. Use when creating a WebSocket API, configuring route selection, managing WebSocket connections, setting up Lambda authorizers for WebSocket, deploying a. Triggers: create websocket api, configure route selection expression, websocket connection management, lambda authorizer websocket, websocket deployment stage, bidirectional communication api gateway, websocket ping pong keepalive.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with apigateway / lambda / dynamodb access. Works with Terraform aws_apigatewayv2_api / aws_apigatewayv2_route / aws_apigatewayv2_integration / aws_apigatewayv2_deployment resources and CloudFormation AWS::ApiGatewayV2::Api templates.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: AppIntegration
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, api-gateway, websocket, cloudops, deploy, appintegration, provisioning, route-selection, connection-management, lambda-authorizer, waf, real-time
  dependencies: aws-orchestrator
  keywords: aws, api gateway, websocket, cloudops, deploy, provisioning, route selection, connection management, lambda authorizer, waf, bidirectional, real-time, dynamodb connections, ping pong
  when_to_use: Invoke when the user wants to create an API Gateway WebSocket API, configure route selection expressions, manage WebSocket connections ($connect/$disconnect), set up Lambda custom authorizers for WebSocket auth, deploy a WebSocket stage, implement bidirectional real-time communication, configure connection management with DynamoDB, or integrate WAF with a WebSocket API. Do NOT invoke for API Gateway REST APIs or HTTP APIs (use apigateway-rest-deployer or apigateway-http-api-deployer), for AppSync subscriptions (use appsync skills), or for IoT Core (use iot skills).
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
| references/advanced-patterns.md | Heuristics + edge cases + recent features |
| references/error-handling.md | Symptom-to-cause remedies |

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

Deep dive: [advanced-patterns.md](references/advanced-patterns.md). The four-phase lifecycle — $connect stores the ConnectionId in DynamoDB, route-selection dispatch handles messages, $disconnect deletes it, and the 2-hour idle timeout fires $disconnect.
Without ConnectionId storage the server cannot push via PostToConnection — the #1 cause of "my WebSocket API can receive but not send".

## Expert heuristic: route selection expression mechanics

Deep dive: [advanced-patterns.md](references/advanced-patterns.md). The VTL expression (default `$request.body.action`) evaluates each message body to a route key; unmatched or null keys fall to `$default` or are rejected.
The expression MUST match the client's message format or custom routes never fire.

## Expert heuristic: idle disconnect and keepalive

Deep dive: [advanced-patterns.md](references/advanced-patterns.md). Connections idle-disconnect after 2 hours (hard limit); keepalive via client ping frames, application-level heartbeat every 30-60 s, or server-side PostToConnection heartbeats.
Any traffic on the connection resets the idle timer.

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

CLI walkthrough: [routes-and-integrations.md](references/routes-and-integrations.md). `create-api` sets the route selection expression at creation; `update-api` changes it, which requires a new deployment (auto-deploy stages excepted).
Common expressions: `$request.body.action`, `$request.body.type`, `$request.body.routeKey`.

## Step 2 — Connection routes ($connect, $disconnect)

CLI walkthrough: [connection-management-and-auth.md](references/connection-management-and-auth.md). `$connect` fires on open (store the ConnectionId; a non-2xx integration response rejects the connection) and `$disconnect` fires on close or idle timeout (delete the ConnectionId).
Event structures carry `requestContext.connectionId` — the key the backend must persist.

## Step 3 — Custom routes

CLI walkthrough: [routes-and-integrations.md](references/routes-and-integrations.md). Route keys must match what the selection expression evaluates (e.g., `action=sendMessage` → route `sendMessage`).
Add a `$default` route to catch unmatched messages.

## Step 4 — Route responses (bidirectional communication)

CLI walkthrough: [routes-and-integrations.md](references/routes-and-integrations.md). `create-route-response` enables synchronous two-way replies from the integration.
Route responses are NOT push notifications — server-initiated pushes use PostToConnection (Step 7).

## Step 5 — Integration types

CLI walkthrough: [routes-and-integrations.md](references/routes-and-integrations.md). Lambda (AWS_PROXY, 30 s max), AWS Service, Mock, and HTTP integrations.
Grant `lambda:InvokeFunction` to `apigateway.amazonaws.com` via `add-permission`, or integrations return 500.

## Step 6 — Deployment and stage

CLI walkthrough: [routes-and-integrations.md](references/routes-and-integrations.md). Deployments are immutable snapshots; the stage exposes `wss://{api-id}.execute-api.{region}.amazonaws.com/{stage}`.
Prefer `--auto-deploy` stages; throttle via stage route settings (WebSocket APIs do NOT support usage plans or API keys).

## Step 7 — Connection management (DynamoDB)

CLI walkthrough: [connection-management-and-auth.md](references/connection-management-and-auth.md). DynamoDB connections table + `$connect`/`$disconnect` handlers + PostToConnection via the ApiGatewayManagementApi SDK (NOT ApiGatewayV2).
Handle 410 Gone by deleting the stale ConnectionId; the SDK does NOT auto-detect the endpoint.

## Step 8 — Custom authorizer (Lambda)

CLI walkthrough: [connection-management-and-auth.md](references/connection-management-and-auth.md). REQUEST authorizer attached to `$connect` with an identity source (e.g., `$request.querystring.token`).
Returns `{ isAuthorized: boolean }` and runs BEFORE the $connect integration; `false` rejects the connection with 403.

## Step 9 — CloudWatch Logs

CLI walkthrough: [routes-and-integrations.md](references/routes-and-integrations.md). Execution logs via stage `LoggingLevel` (OFF/INFO/ERROR) and access logs via `--access-log-settings`.
`DataTraceEnabled` logs full request/response payloads — use with caution for sensitive data.

## Step 10 — WAF integration

CLI walkthrough: [connection-management-and-auth.md](references/connection-management-and-auth.md). Associate the Web ACL with the API stage ARN; WAF inspects ONLY the initial handshake.
Post-connection frames are NOT inspected — message-level filtering belongs in the backend.

## Step 11 — Ping/pong keepalive

CLI walkthrough: [connection-management-and-auth.md](references/connection-management-and-auth.md). Client-side heartbeat every 30-60 s (e.g., `{ "action": "ping" }`) with a pong route response.
Any traffic on the connection resets the 2-hour idle timer.

## Step 12 — Cross-account backend invocation

Deep dive: [advanced-patterns.md](references/advanced-patterns.md). Cross-account Lambda invocation needs `add-permission` in the Lambda account.
Scope `--source-arn` to the API account's ID: `arn:aws:execute-api:{region}:<api-account-id>:{api-id}/*/*`.

## Step 13 — Message size limit (128 KB)

Deep dive: [advanced-patterns.md](references/advanced-patterns.md). 128 KB per-frame limit (131,072 bytes); larger messages are rejected with 413.
Base64 inflates binary ~33% (~96 KB effective); chunk frames or offload to S3 and send a reference.

## Step 14 — Recent features

Deep dive: [advanced-patterns.md](references/advanced-patterns.md). Auto-deploy stages, VPC-link private integrations, WAF WebSocket conditions, batch PostToConnection, WebSocket CloudWatch metrics, tagging (2023-2026).
Loaded on demand when the task calls for the newest capabilities.

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

Deep dive: [error-handling.md](references/error-handling.md). Symptom-to-cause remedies for the six common failure modes.
No server push (ConnectionId not stored), routes never firing (expression mismatch), 500s (missing invoke permission), 410 Gone (stale connection), 2-hour drops (idle timeout), 413 (size limit).

## References (load on demand)

- [Routes and integrations](references/routes-and-integrations.md) — route selection expressions, route types, route responses, integration types, deployment/stage/throttling, CloudWatch log enablement (Steps 1, 3, 4, 5, 6, 9 CLI walkthroughs in detail)
- [Connection management and auth](references/connection-management-and-auth.md) — DynamoDB ConnectionId tracking, PostToConnection, Lambda authorizers, WAF, keepalive, 128 KB limit (Steps 2, 7, 8, 10, 11, 13 CLI walkthroughs in detail)
- [Advanced patterns](references/advanced-patterns.md) — connection-lifecycle / route-selection / keepalive expert heuristics, cross-account invocation (Step 12), recent AWS features 2023-2026 (Step 14)
- [Error handling](references/error-handling.md) — symptom-to-cause remedies: no server push, routes not firing, 500s, 410 Gone, 2-hour idle drops, 413 size rejections

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
