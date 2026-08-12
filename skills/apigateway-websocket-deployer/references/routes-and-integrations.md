# Routes and Integrations — API Gateway WebSocket Deployer

Deep reference on route selection expressions (VTL evaluation,
matching message formats, $default fallback), route types
($connect, $disconnect, custom, $default), route responses for
bidirectional communication, integration types (Lambda, AWS
Service, Mock, HTTP), deployment and stage management, and
throttling. Loaded on demand by the skill — kept out of the main
SKILL.md body so the provisioning procedure stays scannable.

## Route selection expressions

### How the expression is evaluated

The route selection expression is a Velocity Template Language
(VTL) expression that API Gateway evaluates against the incoming
message body to produce a route key. The route key determines
which route (and its integration) handles the message.

```text
Expression: $request.body.action
Incoming message: { "action": "sendMessage", "data": "hello" }
Evaluation: $request.body.action → "sendMessage"
Route invoked: "sendMessage"
```

### Available variables

| Variable | Description |
|---|---|
| `$request.body` | The raw message body (JSON-parsed if Content-Type is application/json) |
| `$request.header.<name>` | A specific request header (on $connect) |

### Common expression patterns

```text
$request.body.action
  → { "action": "sendMessage" } → route "sendMessage"

$request.body.type
  → { "type": "chat" } → route "chat"

$request.body.routeKey
  → { "routeKey": "joinRoom" } → route "joinRoom"
```

### When the expression produces no match

If the expression evaluates to a value that does NOT match any
route key, the message goes to the `$default` route (if one
exists). If no `$default` route exists, the message is silently
dropped.

```text
Expression: $request.body.action
Message: { "message": "hello" }  (no "action" field)
Evaluation: $request.body.action → undefined
Route invoked: $default (if exists) | dropped (if no $default)
```

### Updating the route selection expression

```bash
aws apigatewayv2 update-api \
  --api-id abc123def4 \
  --route-selection-expression '$request.body.type' \
  --region us-east-1
```

After updating, create a new deployment (or use auto-deploy) for
the change to take effect.

## Route types

### $connect route

Fires when a client opens a WebSocket connection. This is the
entry point for the connection lifecycle.

- The `connectionId` is available in `event.requestContext.connectionId`.
- Query string parameters and headers from the connection request
  are available in `event.queryStringParameters` and `event.headers`.
- If the $connect integration returns a non-2xx status, the
  connection is REJECTED (client receives HTTP 4xx/5xx on the
  upgrade request).
- This is where custom authorizers run (before the integration).

### $disconnect route

Fires when the connection is closed — either by the client, by
the server, or by the idle timeout (2 hours).

- The `connectionId` is available in `event.requestContext.connectionId`.
- `disconnectReason` indicates why: `CLIENT_INITIATED`,
  `SERVER_INITIATED`, or idle timeout.
- The $disconnect handler should clean up resources (e.g., delete
  ConnectionId from DynamoDB).
- The return value of the $disconnect handler is IGNORED (the
  connection is already closing).

### Custom routes

Custom routes handle specific message types. The route key must
match what the route selection expression evaluates to.

```bash
# Create a custom route
aws apigatewayv2 create-route \
  --api-id abc123def4 \
  --route-key sendMessage \
  --target integrations/ghi789 \
  --region us-east-1
```

The incoming message body is available in `event.body` (as a JSON
string that must be parsed in the handler).

### $default route

The `$default` route handles any message that does not match a
custom route. It is optional but recommended for handling
unexpected message types gracefully.

```bash
aws apigatewayv2 create-route \
  --api-id abc123def4 \
  --route-key '$default' \
  --target integrations/mno345 \
  --region us-east-1
```

## Route responses (bidirectional communication)

### What route responses do

By default, a WebSocket route's integration processes the message
but does NOT return a response to the client. To enable the
integration to send a response back over the same WebSocket
connection, create a route response.

```bash
# Create a route response for the sendMessage route
aws apigatewayv2 create-route-response \
  --api-id abc123def4 \
  --route-id <sendMessage-route-id> \
  --route-response-key '$default' \
  --region us-east-1
```

### Handler returning a route response

```javascript
exports.handler = async (event) => {
  const body = JSON.parse(event.body);

  // Process the message...

  // This response is sent back to the client via route response
  return {
    statusCode: 200,
    body: JSON.stringify({
      type: 'ack',
      messageId: body.messageId,
      timestamp: Date.now()
    })
  };
};
```

### Route response vs PostToConnection

| Mechanism | Direction | When | SDK |
|---|---|---|---|
| Route response | Synchronous reply to sender | Immediately after processing the client's message | N/A (just return from handler) |
| PostToConnection | Server-initiated push to any client | Anytime, using stored ConnectionId | ApiGatewayManagementApi |

Route responses are for request-reply patterns. PostToConnection
is for push notifications and broadcasting.

## Integration types

### Lambda integration (AWS_PROXY)

The most common integration type. API Gateway invokes the Lambda
function with the event payload and waits for the response.

```bash
aws apigatewayv2 create-integration \
  --api-id abc123def4 \
  --integration-type AWS_PROXY \
  --integration-uri arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/arn:aws:lambda:us-east-1:111122223333:function:ws-handler/invocations \
  --region us-east-1
```

- Sync invocation (API Gateway waits for Lambda response).
- Max timeout: 30 seconds (regardless of Lambda function timeout).
- Grant permission: `aws lambda add-permission` with
  `--principal apigateway.amazonaws.com`.

### AWS Service integration

Direct integration with an AWS service (e.g., SQS, Kinesis,
DynamoDB) without a Lambda function.

```bash
aws apigatewayv2 create-integration \
  --api-id abc123def4 \
  --integration-type AWS \
  --integration-type AWS \
  --connection-type INTERNET \
  --integration-method POST \
  --integration-uri arn:aws:apigateway:us-east-1:sqs:path/111122223333/my-queue \
  --credentials-arn arn:aws:iam::111122223333:role/apigateway-sqs-role \
  --region us-east-1
```

### Mock integration

Returns a fixed response without calling a backend. Useful for
testing or for the $default route when you want to silently
acknowledge unmatched messages.

```bash
aws apigatewayv2 create-integration \
  --api-id abc123def4 \
  --integration-type MOCK \
  --region us-east-1
```

### HTTP integration

Forwards the message to an HTTP endpoint.

```bash
aws apigatewayv2 create-integration \
  --api-id abc123def4 \
  --integration-type HTTP_PROXY \
  --integration-uri https://backend.example.com/ws \
  --integration-method POST \
  --region us-east-1
```

## Deployment and stage

### Manual deployment

After creating or modifying routes, create a deployment:

```bash
DEPLOYMENT_ID=$(aws apigatewayv2 create-deployment \
  --api-id abc123def4 \
  --query 'DeploymentId' --output text \
  --region us-east-1)

# Create or update a stage with the deployment
aws apigatewayv2 create-stage \
  --api-id abc123def4 \
  --stage-name prod \
  --deployment-id "$DEPLOYMENT_ID" \
  --region us-east-1
```

### Auto-deploy stage (recommended)

Auto-deploy stages automatically deploy route and integration
changes without explicit deployment creation:

```bash
aws apigatewayv2 create-stage \
  --api-id abc123def4 \
  --stage-name prod \
  --auto-deploy \
  --region us-east-1
```

### Stage-level throttling

WebSocket APIs do NOT support usage plans or API keys. Throttling
is configured at the stage level:

```bash
aws apigatewayv2 update-stage \
  --api-id abc123def4 \
  --stage-name prod \
  --default-route-settings '{
    "ThrottlingBurstLimit": 500,
    "ThrottlingRateLimit": 1000
  }' \
  --region us-east-1
```

### Per-route throttling

Throttle specific routes differently:

```bash
aws apigatewayv2 update-stage \
  --api-id abc123def4 \
  --stage-name prod \
  --route-settings '{
    "sendMessage": {
      "ThrottlingBurstLimit": 100,
      "ThrottlingRateLimit": 200
    },
    "broadcast": {
      "ThrottlingBurstLimit": 10,
      "ThrottlingRateLimit": 20
    }
  }' \
  --region us-east-1
```

## Terraform example

```hcl
# WebSocket API
resource "aws_apigatewayv2_api" "websocket" {
  name                       = "my-websocket-api"
  protocol_type              = "WEBSOCKET"
  route_selection_expression = "$request.body.action"
}

# $connect integration
resource "aws_apigatewayv2_integration" "connect" {
  api_id           = aws_apigatewayv2_api.websocket.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.connect.invoke_arn
}

# $connect route
resource "aws_apigatewayv2_route" "connect" {
  api_id    = aws_apigatewayv2_api.websocket.id
  route_key = "$connect"
  target    = "integrations/${aws_apigatewayv2_integration.connect.id}"
}

# sendMessage route
resource "aws_apigatewayv2_integration" "message" {
  api_id           = aws_apigatewayv2_api.websocket.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.message.invoke_arn
}

resource "aws_apigatewayv2_route" "send_message" {
  api_id    = aws_apigatewayv2_api.websocket.id
  route_key = "sendMessage"
  target    = "integrations/${aws_apigatewayv2_integration.message.id}"
}

# Route response for bidirectional communication
resource "aws_apigatewayv2_route_response" "message_response" {
  api_id              = aws_apigatewayv2_api.websocket.id
  route_id            = aws_apigatewayv2_route.send_message.id
  route_response_key  = "$default"
}

# Auto-deploy stage
resource "aws_apigatewayv2_stage" "prod" {
  api_id      = aws_apigatewayv2_api.websocket.id
  name        = "prod"
  auto_deploy = true

  default_route_settings {
    throttling_burst_limit = 500
    throttling_rate_limit  = 1000
  }
}

# Lambda permission for API Gateway to invoke
resource "aws_lambda_permission" "apigateway_connect" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.connect.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.websocket.execution_arn}/*/$connect"
}
```
