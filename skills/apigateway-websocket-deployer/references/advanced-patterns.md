# Advanced Patterns — API Gateway WebSocket Deployer

Expert heuristics, cross-account edge cases, and recent AWS features
moved verbatim from the SKILL.md body for progressive disclosure
(agentskills.io). Loaded on demand by the skill.

---

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
