# Integrations and Routes Reference (HTTP API / v2)

Supplementary reference for the API Gateway HTTP API Deployer skill.
Use when picking an integration subtype, designing the route table,
wiring VPC link private integrations, or configuring direct AWS-service
integrations (Step Functions / SQS / Kinesis) without a Lambda in the
path.

## Route key grammar

HTTP API routes are flat `(method, path)` pairs. The full grammar:

| Route key | Matches | Notes |
|---|---|---|
| `METHOD /path` | exact method on exact path | e.g., `POST /users` |
| `METHOD /path/{param}` | path parameter | e.g., `GET /users/{userId}` |
| `METHOD /path/{proxy+}` | greedy under prefix | matches `/path/a/b/c` |
| `ANY /path` | every method on path | includes OPTIONS, HEAD |
| `ANY /{proxy+}` | every method on every sub-path | the catch-all |
| `$default` | any unmatched route | API-level fallback, not in route table |

**Precedence:** exact > parameterized > greedy > `ANY` > `$default`.
`ANY` is a method wildcard, not a path wildcard; `{proxy+}` is a path
wildcard, not a method wildcard. The two combine destructively.

**Most-specific match rule:** the route with the longest matching path
prefix wins. `GET /users/me` wins over `ANY /{proxy+}` even though both
match, because `/users/me` is more specific than `/{proxy+}`.

## Integration subtypes — full matrix

| Integration type | Subtype | Request shape | Response shape | Use when |
|---|---|---|---|---|
| `AWS_PROXY` | Lambda proxy | Full HTTP request as JSON event | Lambda returns `{statusCode, headers, body}` | Default for Lambda backends |
| `HTTP_PROXY` | — | Pass-through | Pass-through | External HTTP backend, including NLB via VPC link |
| `HTTP` | — | Header/path rewrite (limited) | Pass-through | External HTTP backend needing minor transform |
| `AWS` | `STEP_FUNCTION` `StartExecution` | API Gateway formats input | Execution ARN returned immediately | Async Standard Workflow trigger |
| `AWS` | `STEP_FUNCTION` `StartSyncExecution` | API Gateway formats input | Workflow output returned inline (≤5s) | Synchronous Express Workflow API |
| `AWS` | `SQS` `SendMessage` | API Gateway maps body to MessageBody | SendMessageResponse XML/JSON | Fire-and-forget queue drop |
| `AWS` | `KINESIS` `PutRecord` / `PutRecords` | API Gateway maps body to Data | PutRecordResponse | Stream ingestion without Lambda |

## VPC link private integration deep dive

VPC link lets HTTP API reach private backends (NLB, ALB-via-NLB, ECS
service, on-prem via Direct Connect). The link is a Hairpinier ENI in
your VPC, not a tunnel.

```text
HTTP API → VPC link (ENIs in subnets/SGs) → NLB → targets (ECS, EC2, ALB)
```

**Creation:**
```bash
aws apigatewayv2 create-vpc-link --name prod-nlb-link \
  --subnet-ids subnet-abc subnet-def \
  --security-group-ids sg-xyz
```

- Subnets MUST be in the API's region. Two or more AZs recommended.
- Security group applies to the ENIs API Gateway creates — must allow
  egress to the NLB listener port.
- The NLB must exist before the integration is created. The integration
  references the NLB DNS, not ARN.

**Common VPC link failures:**
- **ALB direct target.** ALB is not supported as a VPC link target. Use
  NLB in front of ALB, or use HTTP integration with the ALB DNS (which
  exposes the ALB to internet egress).
- **Single-AZ failure.** A VPC link with one subnet has no failover if
  that AZ is impaired. Always specify ≥2 subnets in different AZs.
- **Security group egress missing.** If the ENIs' SG lacks egress to
  the NLB listener port, requests time out (504) with no error in
  access logs.
- **NLB listener TLS mismatch.** The integration URI scheme (`https://`
  vs `http://`) must match the NLB listener protocol. A TLS integration
  against a TCP listener returns 502.

## Step Functions direct integration contract

API Gateway formats the Step Functions input from
`request-parameters`. The `Input` field is a JSON string template that
can reference `$request.body`, `$request.header.<name>`,
`$request.path.<name>`, and `$context.<var>`.

```json
{
  "StateMachineArn": "arn:aws:states:us-east-1:111111111111:stateMachine:orders",
  "Action": "StartSyncExecution",
  "Input": "$request.body",
  "Name": "$context.requestId"
}
```

- `StartSyncExecution` is for **Express Workflows only**. The API
  caller blocks until the workflow completes (max 5s for HTTP API, 1s
  for Express Workflow internal ceiling).
- `StartExecution` is for **Standard Workflows**. The API returns
  immediately with the execution ARN; the caller must poll separately
  for results.
- The execution `Name` SHOULD be `$context.requestId` for traceability
  — without it, every execution gets a UUID with no link to the API
  request.

**IAM role requirement:** API Gateway needs a `credentials-arn` role
with `states:StartExecution` / `states:StartSyncExecution` on the
state machine ARN. Scope tightly.

## SQS direct integration contract

```json
{
  "QueueUrl": "https://sqs.us-east-1.amazonaws.com/111111111111/orders",
  "MessageBody": "$request.body"
}
```

- `MessageBody` is the only required field. Other SendMessage
  parameters (`MessageAttributes`, `DelaySeconds`, `MessageDeduplicationId`)
  can be mapped from request headers or context.
- The `credentials-arn` role needs `sqs:SendMessage` on the exact queue
  ARN. Wildcard scope (`sqs:*` on `*`) is a privilege escalation path
  for public APIs.
- The API caller receives the SQS `SendMessageResponse` XML/JSON
  directly, including `MessageId`. There is no Lambda transform step.

## Kinesis direct integration contract

```json
{
  "StreamName": "events",
  "Data": "$request.body",
  "PartitionKey": "$context.requestId"
}
```

- `PartitionKey` determines which shard receives the record. Using
  `$context.requestId` distributes randomly; using a tenant-id JWT claim
  co-locates per-tenant records (better for downstream consumers).
- `PutRecord` is single-record. `PutRecords` (batched) requires the
  request body to already be a JSON array — wire carefully.
- The `credentials-arn` role needs `kinesis:PutRecord` /
  `kinesis:PutRecords` on the stream ARN.

## ANY and {proxy+} safe patterns

| Use case | Safe route | Authorizer |
|---|---|---|
| Lambda handles everything | `ANY /{proxy+}` | JWT (always) |
| Read-only SPA backend | `GET /{proxy+}` only | JWT |
| Specific verbs only | `GET /items`, `POST /items` (no ANY) | JWT |
| Public health probe | `GET /health` only | NONE (explicit) |

Anti-pattern: `ANY /{proxy+}` with `NONE` auth. This exposes every
method (GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS) on every
sub-path. Even if the backend Lambda rejects non-GET, the route itself
advertises exposure and trips security audits.

## Routes vs REST API resources

| Concept | REST API (v1) | HTTP API (v2) |
|---|---|---|
| Hierarchical resources | Yes (root → child → grandchild) | No |
| Methods on resources | Yes (per resource) | Flat routes |
| ANY method | Per resource | Per route |
| Greedy path | `{proxy+}` on a resource | `{proxy+}` in a route |
| Stage + Deployment | Snapshot model | Auto-deploy default |
| Mapping templates | Per method/integration | Not supported |

There is no in-place REST-to-HTTP conversion. Re-create the API.

## Lambda proxy event shape (reference)

When HTTP API invokes a Lambda via `AWS_PROXY`, the event includes:

```json
{
  "version": "2.0",
  "routeKey": "POST /users",
  "rawPath": "/users",
  "rawQueryString": "active=true",
  "headers": { /* lowercase keys */ },
  "requestContext": {
    "http": {
      "method": "POST",
      "path": "/users",
      "protocol": "HTTP/1.1",
      "sourceIp": "203.0.113.7",
      "userAgent": "curl/8.0"
    },
    "routeKey": "POST /users",
    "requestId": "abc-123",
    "stage": "$default",
    "authorizer": { "jwt": { "claims": { /* ... */ } } }
  },
  "body": "{\"name\":\"ada\"}",
  "isBase64Encoded": false
}
```

Lambda returns:
```json
{ "statusCode": 200, "headers": {"content-type": "application/json"}, "body": "{\"id\":1}" }
```

Note `version: 2.0` (vs `1.0` for REST API proxy events). The
`requestContext.http` shape differs — libraries using REST API event
parsers will mis-handle HTTP API events.

## Lambda add-permission scoping

Scope the source ARN tightly:

```bash
aws lambda add-permission --function-name users-handler \
  --statement-id apigw-v2-invoke \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:us-east-1:111111111111:abc123/*/POST/users"
```

The `*` in the source ARN matches the stage name (covers `$default` and
named stages). The trailing `/POST/users` scopes to one method-path —
use `/POST/users/*` for a prefix, or `/*/*` for the whole API.

Avoid `/*/*/*` (whole API) when only one route needs it. A wildcard
source ARN lets any route on the API invoke the function, which can
surprise operators who add a public `/health` route later.

## AWS documentation

- **Working with integrations for HTTP APIs** — https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-develop-integrations.html
- **Set up Lambda proxy integrations for HTTP APIs** — https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-develop-integrations-lambda.html
- **Set up HTTP proxy integrations for HTTP APIs** — https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-develop-integrations-http.html
- **Set up VPC links for HTTP APIs** — https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-vpc-links.html
- **Step Functions direct integration** — https://docs.aws.amazon.com/step-functions/latest/dg/connect-api-gateway.html

## Moved from SKILL.md Step 3 — per-integration create commands

**Lambda proxy:**
```bash
aws apigatewayv2 create-integration --api-id <id> \
  --integration-type AWS_PROXY --integration-method POST \
  --integration-uri arn:aws:apigateway:<region>:lambda:path/2015-03-31/functions/arn:aws:lambda:<region>:<account>:function:<name>/invocations

aws lambda add-permission --function-name <name> \
  --statement-id apigw-v2-invoke --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn arn:aws:execute-api:<region>:<account>:<api-id>/*/POST/users
```

**HTTP proxy via VPC link:**
```bash
aws apigatewayv2 create-vpc-link --name prod-nlb-link \
  --subnet-ids subnet-abc subnet-def --security-group-ids sg-xyz

aws apigatewayv2 create-integration --api-id <id> \
  --integration-type HTTP_PROXY --integration-method ANY \
  --integration-uri https://<nlb-dns>/api \
  --connection-id <vpc-link-id> --connection-type VPC_LINK
```

**Step Functions START_SYNC_EXECUTION (direct, no Lambda):** use
`StartSyncExecution` for Express Workflows (caller needs the result
inline, 5s ceiling); `StartExecution` for Standard Workflows (async —
API returns the execution ARN immediately).
```bash
aws apigatewayv2 create-integration --api-id <id> \
  --integration-type AWS --integration-method POST \
  --integration-subtype STEP_FUNCTION \
  --request-parameters '{"StateMachineArn":"arn:aws:states:<region>:<account>:stateMachine:<name>","Action":"StartSyncExecution","Input":"$request.body"}'
```

**SQS SendMessage (direct):** uses `credentials-arn` (IAM role trusting
`apigateway.amazonaws.com`) with `MessageBody` mapped from the request
body.

**Kinesis PutRecord (direct):** uses `credentials-arn` with `Data`
mapped from the request body and `PartitionKey` mapped from
`$context.requestId` (or a JWT claim for tenant-partitioned streams).

Direct AWS integrations need a `credentials-arn` (an IAM role trusting
`apigateway.amazonaws.com` with permission to call the target service).
This role is the blast radius — scope it tightly to the one queue,
state machine, or stream.
