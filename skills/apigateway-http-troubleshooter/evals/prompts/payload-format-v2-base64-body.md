# Eval prompt: payload-format-v2-base64-body

Diagnose the API Gateway HTTP API failure for the following API. Walk
the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: HTTP API `api-payload-v2` returns `502 Bad Gateway` on
`POST /orders` when the request body exceeds 1 KB or contains
non-ASCII characters. GET requests to the same route succeed. Lambda
logs show `SyntaxError: Unexpected token in JSON` at the line
`JSON.parse(event.body)`.

```text
ApiId: api-payload-v2
ProtocolType: HTTP
Stage: $default
AutoDeploy: true
RouteKey: POST /orders
IntegrationType: AWS_PROXY
IntegrationSubtype: Lambda
PayloadFormatVersion: "2.0"
LambdaFunctionArn: arn:aws:lambda:us-east-1:111111111111:function:fn-orders

Lambda log excerpt:
  INFO  Received request on POST /orders
  SyntaxError: Unexpected token in JSON at position 0
  event.isBase64Encoded: true
  event.body: "eyJvcmRlcklkIjoi...
  END RequestId: ... Duration: 12 ms
```

The handler expects PayloadFormatVersion 1.0 (raw JSON string body).
On v2.0, binary/large bodies arrive base64-encoded. Identify the
payload format version mismatch as the root cause.
