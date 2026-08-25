# Connection Management and Auth — API Gateway WebSocket Deployer

Deep reference on backend connection management (DynamoDB
ConnectionId table, PostToConnection via ApiGatewayManagementApi,
broadcast patterns, stale connection cleanup), Lambda custom
authorizers for WebSocket (identity source, isAuthorized response,
TTL caching), WAF integration (connection-request filtering,
rate-based rules), ping/pong keepalive strategies, and the 128 KB
message size limit. Loaded on demand by the skill — kept out of
the main SKILL.md body so the provisioning procedure stays
scannable.

## Connection management fundamentals

### Why the application must manage ConnectionIds

API Gateway maintains the WebSocket connection at the transport
level, but it does NOT provide a registry of active connections.
The APPLICATION is responsible for:

1. **Storing** the ConnectionId when $connect fires.
2. **Using** the ConnectionId to send messages via PostToConnection.
3. **Deleting** the ConnectionId when $disconnect fires.
4. **Cleaning up** stale ConnectionIds (410 Gone on PostToConnection).

Without this, the server cannot push messages to clients.

### DynamoDB table schema

The standard pattern uses DynamoDB with the ConnectionId as the
partition key:

```bash
aws dynamodb create-table \
  --table-name WebSocketConnections \
  --attribute-definitions AttributeName=connectionId,AttributeType=S \
  --key-schema AttributeName=connectionId,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

Optional additional attributes:

| Attribute | Type | Purpose |
|---|---|---|
| `connectionId` | String (partition key) | Unique connection identifier |
| `userId` | String | Authenticated user (from authorizer context) |
| `roomId` | String | Chat room or channel (for room-based routing) |
| `timestamp` | Number | Connection time (for TTL cleanup) |
| `ttl` | Number | TTL attribute (auto-expire stale entries) |

### TTL for stale connection cleanup

Set a TTL attribute to auto-expire connections that were not
properly disconnected (e.g., network failures where $disconnect
did not fire):

```bash
# Enable TTL on the connections table
aws dynamodb update-time-to-live \
  --table-name WebSocketConnections \
  --time-to-live-specification Enabled=true,AttributeName=ttl \
  --region us-east-1
```

In the $connect handler, set TTL to 2 hours + buffer:

```javascript
await dynamo.put({
  TableName: TABLE_NAME,
  Item: {
    connectionId: connectionId,
    ttl: Math.floor(Date.now() / 1000) + 7500 // ~2 hours + 5 min buffer
  }
}).promise();
```

### $connect handler (store ConnectionId)

```javascript
const AWS = require('aws-sdk');
const dynamo = new AWS.DynamoDB.DocumentClient();

exports.handler = async (event) => {
  const connectionId = event.requestContext.connectionId;
  const userId = event.requestContext.authorizer
    ? event.requestContext.authorizer.userId
    : 'anonymous';

  await dynamo.put({
    TableName: process.env.CONNECTIONS_TABLE,
    Item: {
      connectionId: connectionId,
      userId: userId,
      timestamp: Date.now(),
      ttl: Math.floor(Date.now() / 1000) + 7500
    }
  }).promise();

  return { statusCode: 200 };
};
```

### $disconnect handler (delete ConnectionId)

```javascript
exports.handler = async (event) => {
  const connectionId = event.requestContext.connectionId;

  await dynamo.delete({
    TableName: process.env.CONNECTIONS_TABLE,
    Key: { connectionId: connectionId }
  }).promise();

  return { statusCode: 200 };
};
```

### Sending messages to a client (PostToConnection)

```javascript
const AWS = require('aws-sdk');

exports.handler = async (event) => {
  const body = JSON.parse(event.body);
  const domain = event.requestContext.domainName;
  const stage = event.requestContext.stage;

  // CRITICAL: Use ApiGatewayManagementApi, not ApiGatewayV2
  // The endpoint must be constructed manually
  const managementApi = new AWS.ApiGatewayManagementApi({
    apiVersion: '2018-11-29',
    endpoint: `${domain}/${stage}`
  });

  // Get the target connection from DynamoDB
  const result = await dynamo.get({
    TableName: process.env.CONNECTIONS_TABLE,
    Key: { connectionId: body.targetConnectionId }
  }).promise();

  if (!result.Item) {
    return { statusCode: 404, body: 'Connection not found' };
  }

  try {
    await managementApi.postToConnection({
      ConnectionId: result.Item.connectionId,
      Data: JSON.stringify({
        type: 'message',
        from: event.requestContext.connectionId,
        message: body.message
      })
    }).promise();
  } catch (err) {
    if (err.statusCode === 410) {
      // Connection is gone — clean up
      await dynamo.delete({
        TableName: process.env.CONNECTIONS_TABLE,
        Key: { connectionId: result.Item.connectionId }
      }).promise();
    } else {
      throw err;
    }
  }

  return { statusCode: 200 };
};
```

### Broadcasting to all connections

```javascript
exports.handler = async (event) => {
  const managementApi = new AWS.ApiGatewayManagementApi({
    apiVersion: '2018-11-29',
    endpoint: `${event.requestContext.domainName}/${event.requestContext.stage}`
  });

  // Scan all connections (use pagination for large tables)
  const connections = await dynamo.scan({
    TableName: process.env.CONNECTIONS_TABLE,
    ProjectionExpression: 'connectionId'
  }).promise();

  const message = JSON.stringify({ type: 'broadcast', data: 'Hello all' });

  // Send to each connection (handle 410 Gone for stale connections)
  await Promise.all(
    connections.Items.map(async (conn) => {
      try {
        await managementApi.postToConnection({
          ConnectionId: conn.connectionId,
          Data: message
        }).promise();
      } catch (err) {
        if (err.statusCode === 410) {
          await dynamo.delete({
            TableName: process.env.CONNECTIONS_TABLE,
            Key: { connectionId: conn.connectionId }
          }).promise();
        }
      }
    })
  );

  return { statusCode: 200 };
};
```

## Lambda custom authorizer

### How WebSocket authorizers work

A Lambda custom authorizer authenticates the $connect request. It
runs BEFORE the $connect integration. If the authorizer returns
`isAuthorized: false`, the connection is rejected (HTTP 403 on
the upgrade request).

```text
Client → WebSocket connect request (with auth token in query string)
  → $connect route → authorizer fires first
    ├── isAuthorized: true → connection proceeds → $connect integration fires
    └── isAuthorized: false → connection rejected (403)
```

### Creating the authorizer

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

### Attaching the authorizer to $connect

```bash
aws apigatewayv2 update-route \
  --api-id abc123def4 \
  --route-id <connect-route-id> \
  --authorizer-id <authorizer-id> \
  --authorization-type CUSTOM \
  --region us-east-1
```

### Authorizer Lambda handler

```javascript
exports.handler = async (event) => {
  // For WebSocket, the identity source is in queryStringParameters
  const token = event.queryStringParameters
    ? event.queryStringParameters.token
    : null;

  if (!token) {
    return { isAuthorized: false };
  }

  try {
    // Validate token (JWT verification, database lookup, etc.)
    const decoded = await verifyToken(token);

    return {
      isAuthorized: true,
      context: {
        userId: decoded.userId,
        role: decoded.role
      }
    };
  } catch (err) {
    return { isAuthorized: false };
  }
};
```

### Authorizer TTL caching

The `authorizer-result-ttl-in-seconds` setting caches the
authorizer's response for the specified duration. This means
repeated connections from the same identity source (same token)
within the TTL window do NOT re-invoke the authorizer Lambda.

- Default: 300 seconds (5 minutes).
- Set to 0 to disable caching (every connection invokes the
  authorizer).
- For security-sensitive applications, use a short TTL or disable
  caching.

### Identity source

The identity source specifies where API Gateway looks for the
auth token. Common patterns:

| Identity source | Client sends token in | Access in authorizer |
|---|---|---|
| `$request.querystring.token` | `wss://...?token=abc123` | `event.queryStringParameters.token` |
| `$request.header.Authorization` | `Authorization: Bearer abc123` | `event.headers.Authorization` |

**Important:** WebSocket clients cannot set custom headers on the
initial connection request (browser limitation). Query string
parameters are the standard way to pass auth tokens for WebSocket
connections. Use `wss://api.example.com/prod?token=abc123`.

## WAF integration

### What WAF inspects for WebSocket

WAF inspects the initial HTTP upgrade request (the WebSocket
handshake) but does NOT inspect individual WebSocket frames after
the connection is established. WAF rules apply to connection
requests only.

### Common WAF rules for WebSocket

1. **IP-based filtering** — allow or block specific IPs.
2. **Rate-based limiting** — limit connections per IP per time
   window.
3. **Geographic restrictions** — allow or block countries.
4. **Header inspection** — validate auth headers on connection.

### Creating a WAF Web ACL

```bash
aws wafv2 create-web-acl \
  --name ws-waf \
  --scope REGIONAL \
  --default-action '{"Allow":{}}' \
  --visibility-config '{
    "CloudWatchMetricsEnabled": true,
    "MetricName": "ws-waf",
    "SampledRequestsEnabled": true
  }' \
  --rules '[
    {
      "Name": "rate-limit",
      "Priority": 1,
      "Action": { "Block": {} },
      "Statement": {
        "RateBasedStatement": {
          "Limit": 100,
          "AggregateKeyType": "IP"
        }
      },
      "VisibilityConfig": {
        "CloudWatchMetricsEnabled": true,
        "MetricName": "rate-limit",
        "SampledRequestsEnabled": true
      }
    }
  ]' \
  --region us-east-1
```

### Associating WAF with the WebSocket stage

```bash
aws wafv2 associate-web-acl \
  --web-acl-arn arn:aws:wafv2:us-east-1:111122223333:regional/webacl/ws-waf/abc123 \
  --resource-arn arn:aws:apigateway:us-east-1::/restapis/abc123def4/stages/prod \
  --region us-east-1
```

## Ping/pong keepalive

### The 2-hour idle disconnect

API Gateway WebSocket connections auto-disconnect after 2 hours
(7200 seconds) of inactivity. This is a hard limit that cannot be
configured. Any traffic on the connection resets the idle timer:
client messages, server PostToConnection, or protocol-level
ping/pong frames.

### Keepalive strategies

#### Client-side application heartbeat (recommended)

The client sends a periodic heartbeat message:

```javascript
// Browser client
const ws = new WebSocket('wss://abc123def4.execute-api.us-east-1.amazonaws.com/prod?token=abc');

setInterval(() => {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ action: 'ping' }));
  }
}, 60000); // Every 60 seconds
```

Server responds:

```javascript
// In the "ping" route handler
exports.handler = async (event) => {
  return {
    statusCode: 200,
    body: JSON.stringify({ type: 'pong', timestamp: Date.now() })
  };
};
```

#### Protocol-level ping/pong

WebSocket protocol supports ping/pong frames at the transport
level. Browsers handle this automatically in most cases, but not
all browsers send periodic pings. For non-browser clients (Node.js,
Python), implement protocol-level pings:

```javascript
// Node.js ws library
const WebSocket = require('ws');
const ws = new WebSocket('wss://...');

// Enable built-in keepalive
ws.on('open', () => {
  // ws library has a built-in ping option
  setInterval(() => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.ping();
    }
  }, 30000);
});
```

## Message size limit (128 KB)

### The limit

The maximum message size for WebSocket API messages is 128 KB
(131,072 bytes) per frame. Messages exceeding this limit are
rejected with HTTP 413 Payload Too Large.

### Implications

- JSON payloads must be under 128 KB. A typical JSON object with
  100 fields is ~5-10 KB, so most messages are fine.
- Binary data must be base64-encoded (increases size by ~33%),
  effectively limiting binary to ~96 KB pre-encoding.
- For large payloads, chunk them into multiple messages under 128
  KB each, or offload to S3 and send a presigned URL via WebSocket.

### Handling large payloads

```javascript
// Client: chunk large messages
function sendLargeMessage(ws, data) {
  const json = JSON.stringify(data);
  if (json.length > 128 * 1024) {
    // Offload to S3
    const s3Url = uploadToS3(data);
    ws.send(JSON.stringify({ action: 'largeDataRef', url: s3Url }));
  } else {
    ws.send(JSON.stringify({ action: 'sendData', data: data }));
  }
}
```

## IAM role for Lambda integration

The Lambda function handling WebSocket routes needs an IAM
execution role with permissions for:

1. **DynamoDB** — read/write the connections table.
2. **ApiGatewayManagementApi** — PostToConnection (via
   `execute-api:ManageConnections`).
3. **CloudWatch Logs** — logging.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:DeleteItem",
        "dynamodb:Scan",
        "dynamodb:Query"
      ],
      "Resource": "arn:aws:dynamodb:us-east-1:111122223333:table/WebSocketConnections"
    },
    {
      "Effect": "Allow",
      "Action": "execute-api:ManageConnections",
      "Resource": "arn:aws:execute-api:us-east-1:111122223333:abc123def4/prod/POST/@connections/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "*"
    }
  ]
}
```

**Critical:** the `execute-api:ManageConnections` permission is
required for PostToConnection. The resource ARN format is:
`arn:aws:execute-api:{region}:{account}:{api-id}/{stage}/POST/@connections/*`

---

## Step-by-step CLI walkthroughs (moved verbatim from SKILL.md)

The SKILL.md body keeps only step stubs under progressive disclosure
(agentskills.io); the original step sections below were moved verbatim
so no content is lost.

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
