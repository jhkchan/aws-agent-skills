# Eval prompt: missing-integration-target

Design a deployment plan for an HTTP API. Emit the standard VERDICT
block.

Requirements:

- API type: HTTP (v2)
- Endpoint type: REGIONAL (us-east-1)
- Routes and authorization:
  - GET /health [NONE]
  - GET /users [JWT]
  - POST /users [JWT]
  - GET /users/{userId} [JWT]
- Authorization: NONE for /health, JWT for the rest
- CORS: allowOrigins=https://app.example.com

The user did NOT specify: integration type (Lambda proxy, HTTP proxy,
VPC link, Step Functions, SQS, Kinesis), any backend target ARN/URI,
or any details about how requests reach the backend. The skill must
catch this during the pre-flight specification gate and emit
PREREQUISITES_MISSING citing the missing integration_type field.
