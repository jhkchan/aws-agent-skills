# CORS and Auth — Lambda Function URL Deployer

Deep reference on CORS configuration at the function URL level
(why handler-level CORS alone fails, the five CORS fields, preflight
handling), auth modes (AWS_IAM SigV4 flow, NONE public exposure,
resource-based policy mechanics), and security best practices.
Loaded on demand by the skill — kept out of the main SKILL.md body
so the provisioning procedure stays scannable.

## CORS fundamentals for function URLs

### Why CORS is at the URL level, not the function level

CORS (Cross-Origin Resource Sharing) is a browser-enforced policy.
When a browser makes a cross-origin request, it first sends a
preflight `OPTIONS` request. The server must respond with the
appropriate `Access-Control-Allow-*` headers. For Lambda Function
URLs, the function URL infrastructure handles the preflight
response based on the `--cors` configuration. If CORS is not
configured on the function URL, the preflight response is empty
and the browser blocks the actual request.

```text
Browser → OPTIONS https://<id>.lambda-url.<region>.on.aws/
  Origin: https://app.example.com
  Access-Control-Request-Method: POST
  Access-Control-Request-Headers: content-type

  ↓

Function URL infrastructure checks --cors config:
  ├── CORS configured → responds with Access-Control-Allow-Origin,
  │   Access-Control-Allow-Methods, Access-Control-Allow-Headers
  │   → preflight passes → browser sends actual request
  └── CORS NOT configured → responds without CORS headers
      → preflight fails → browser blocks request (CORS error)
```

**Key point:** the Lambda handler is NOT invoked during preflight.
The function URL infrastructure handles the preflight response
based solely on the `--cors` configuration. Handler-level CORS
headers are for the actual response, not for preflight.

### The five CORS fields

| Field | Description | Required | Example |
|---|---|---|---|
| `AllowOrigins` | Origins permitted | Yes (for cross-origin) | `["https://app.example.com"]` |
| `AllowMethods` | HTTP methods permitted | Yes | `["GET", "POST", "PUT", "DELETE"]` |
| `AllowHeaders` | Request headers permitted | Recommended | `["content-type", "authorization"]` |
| `ExposeHeaders` | Response headers browser can read | Optional | `["x-request-id", "x-trace-id"]` |
| `MaxAgeSeconds` | Preflight cache duration | Optional | `86400` (24 hours) |

### Creating a function URL with full CORS

```bash
aws lambda create-function-url-config \
  --function-name my-function \
  --auth-type AWS_IAM \
  --invoke-mode BUFFERED \
  --cors '{
    "AllowOrigins": ["https://app.example.com", "https://admin.example.com"],
    "AllowMethods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    "AllowHeaders": ["content-type", "authorization", "x-api-key"],
    "ExposeHeaders": ["x-request-id", "x-trace-id"],
    "MaxAgeSeconds": 86400
  }' \
  --region us-east-1
```

### Updating CORS on an existing function URL

```bash
aws lambda update-function-url-config \
  --function-name my-function \
  --cors '{
    "AllowOrigins": ["https://app.example.com", "https://staging.example.com"],
    "AllowMethods": ["GET", "POST", "PUT", "DELETE"],
    "AllowHeaders": ["content-type", "authorization", "x-api-key"],
    "ExposeHeaders": ["x-request-id"],
    "MaxAgeSeconds": 3600
  }' \
  --region us-east-1
```

### Verifying CORS configuration

```bash
aws lambda get-function-url-config \
  --function-name my-function \
  --region us-east-1
```

Response includes the `Cors` object with all five fields.

### CORS with wildcard origins

For public APIs, you can use `*` as a wildcard:

```json
{
  "AllowOrigins": ["*"],
  "AllowMethods": ["GET"],
  "AllowHeaders": ["content-type"]
}
```

**Warning:** wildcard origins should only be used for genuinely
public read-only APIs. For authenticated APIs, specify exact
origins.

### Defense in depth: handler-level CORS

Even with CORS configured at the function URL level, the handler
should also return CORS headers in the actual response. This is
defense in depth — some HTTP clients (non-browser) and proxies
may strip or not evaluate the function URL's CORS headers.

```javascript
// Node.js handler with defense-in-depth CORS
exports.handler = async (event) => {
  return {
    statusCode: 200,
    headers: {
      "Access-Control-Allow-Origin": "https://app.example.com",
      "Access-Control-Allow-Methods": "GET, POST",
      "Access-Control-Allow-Headers": "content-type",
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ message: "Hello" })
  };
};
```

## Auth mode: AWS_IAM

### How IAM auth works for function URLs

When auth type is `AWS_IAM`, the caller must sign the HTTP request
with AWS Signature Version 4 (SigV4) using their IAM credentials.
The function URL infrastructure validates the signature before
invoking the Lambda function.

```text
Caller → builds SigV4-signed HTTP request
      → https://<id>.lambda-url.<region>.on.aws/
      → Function URL validates signature
      → IAM evaluates resource-based policy on the Lambda function
      → If allowed → Lambda handler invoked
      → If denied → 403 Forbidden (handler NOT invoked)
```

### Resource-based policy for function URL invocation

The Lambda function's resource-based policy must grant
`lambda:InvokeFunctionUrl` to the caller:

```bash
# Allow a specific IAM user to invoke the function URL
aws lambda add-permission \
  --function-name my-function \
  --statement-id function-url-invoke \
  --action lambda:InvokeFunctionUrl \
  --principal arn:aws:iam::111122223333:user/alice \
  --function-url-auth-type AWS_IAM \
  --region us-east-1
```

### Cross-account invocation

For cross-account access, set `--principal` to the other account's
ARN:

```bash
aws lambda add-permission \
  --function-name my-function \
  --statement-id cross-account-url-invoke \
  --action lambda:InvokeFunctionUrl \
  --principal arn:aws:iam::999999999999:root \
  --function-url-auth-type AWS_IAM \
  --region us-east-1
```

This allows any IAM principal in account 999999999999 with
`lambda:InvokeFunctionUrl` permission to call the function URL.

### Signing requests with the SDK

The AWS SDK automatically signs requests with SigV4 when using IAM
credentials:

```python
import boto3
import requests
from botocore.auth import SigV4Auth
from botocore.credentials import Credentials
from botocore.session import Session

# Using boto3 to sign a custom HTTP request
session = Session()
credentials = session.get_credentials().get_frozen_credentials()

url = "https://abc123def456.lambda-url.us-east-1.on.aws/"
request = requests.Request('GET', url)
prepared = request.prepare()

sigv4 = SigV4Auth(credentials, "lambda", "us-east-1")
sigv4.add_auth(prepared)

response = requests.get(url, headers=prepared.headers)
print(response.json())
```

For simpler setups, use a library like `aws-requests-auth`:

```python
from aws_requests_auth.aws_boto3 import Boto3AWSRequestsAuth
import requests

auth = Boto3AWSRequestsAuth(
    aws_host="abc123def456.lambda-url.us-east-1.on.aws",
    aws_region="us-east-1",
    aws_service="lambda"
)
response = requests.get(
    "https://abc123def456.lambda-url.us-east-1.on.aws/",
    auth=auth
)
```

## Auth mode: NONE

### What NONE auth means

NONE auth means the function URL endpoint is on the public internet
with zero authentication. The function URL infrastructure does NOT
validate any credentials. Anyone who knows the URL can invoke it.

The only protection is the unguessability of the URL endpoint ID
(a 32-character string). This is NOT a security boundary — it is
obscurity.

### Valid use cases for NONE auth

- **Public webhooks** — third-party services (Stripe, GitHub) need
  to call your endpoint without IAM credentials.
- **Public APIs with application-level auth** — the handler
  validates an API key, JWT, or other token from the request.
- **Static content / health checks** — endpoints that return
  non-sensitive data.

### Invalid use cases for NONE auth

- **Internal APIs** — use AWS_IAM auth.
- **Authenticated user endpoints** — use AWS_IAM auth or a custom
  auth proxy.
- **Sensitive data endpoints** — use AWS_IAM auth.

### Protecting NONE-auth endpoints

If you must use NONE auth, add layers:

1. **Application-level auth** — validate API keys, JWTs, or HMAC
   signatures in the handler.

2. **CloudFront + WAF** — place CloudFront in front and use AWS WAF
   to filter by IP, rate-limit, or inspect request patterns.

3. **Rate limiting** — implement rate limiting in the handler or
   via WAF rate-based rules.

4. **Monitoring** — set up CloudWatch alarms on `Url4xx` and
   `Url5xx` metrics to detect abuse.

## Common CORS and auth pitfalls

1. **Handler-only CORS.** Configuring CORS only in the handler
   response without the function URL `--cors` parameter. Preflight
   fails because the function URL does not handle the OPTIONS
   request with CORS headers.

2. **NONE auth for internal APIs.** Exposing internal APIs with
   NONE auth on the assumption that the URL is unguessable. The URL
   can be discovered via logs, browser history, DNS enumeration, or
   accidental exposure.

3. **Missing resource-based policy.** Creating a function URL with
   AWS_IAM auth but not adding `lambda:InvokeFunctionUrl` permission
   to the resource-based policy. Callers get 403 Forbidden.

4. **Wildcard CORS for authenticated APIs.** Using
   `AllowOrigins: ["*"]` for APIs that use cookies or
   authorization headers. This allows any website to make
   authenticated requests.

## Terraform examples

```hcl
# Lambda function URL with IAM auth and CORS
resource "aws_lambda_function_url" "api" {
  function_name      = aws_lambda_function.api.function_name
  authorization_type = "AWS_IAM"
  invoke_mode        = "BUFFERED"

  cors {
    allow_origins     = ["https://app.example.com"]
    allow_methods     = ["GET", "POST"]
    allow_headers     = ["content-type", "authorization"]
    expose_headers    = ["x-request-id"]
    max_age_seconds   = 86400
  }
}

# Resource-based policy for IAM auth
resource "aws_lambda_permission" "url_invoke" {
  statement_id        = "function-url-invoke"
  action              = "lambda:InvokeFunctionUrl"
  function_name       = aws_lambda_function.api.function_name
  principal           = "arn:aws:iam::111122223333:user/alice"
  function_url_auth_type = "AWS_IAM"
}

# Function URL with NONE auth (public)
resource "aws_lambda_function_url" "public" {
  function_name      = aws_lambda_function.api.function_name
  authorization_type = "NONE"
  invoke_mode        = "RESPONSE_STREAM"

  cors {
    allow_origins     = ["*"]
    allow_methods     = ["GET", "POST"]
    allow_headers     = ["content-type"]
    max_age_seconds   = 3600
  }
}
```


## Expert heuristic: CORS is at the function URL level

CORS for Lambda Function URLs is NOT set on the Lambda function or
in the handler alone. It is set on the function URL configuration
via the `--cors` parameter. This is a common provisioning mistake.

```text
WRONG (does not work alone):
  - Lambda handler returns Access-Control-Allow-Origin header
  - Function URL has NO CORS config
  → Browser preflight (OPTIONS) fails because the function URL
    does not return CORS headers for preflight

CORRECT:
  - Function URL config has --cors with allowOrigins, allowMethods,
    allowHeaders, exposeHeaders, maxAgeSeconds
  - Lambda handler ALSO returns Access-Control-Allow-Origin in the
    response (defense in depth)
  → Browser preflight succeeds (function URL handles OPTIONS with
    CORS headers); handler response includes CORS headers for the
    actual response
```

**Key implication:** always configure CORS at the function URL level
using the `--cors` parameter. The handler-level CORS header is a
secondary defense, not the primary CORS mechanism for function URLs.


## Step 2 detail: AWS_IAM resource-based policy CLI

**AWS_IAM auth requires a resource-based policy** on the Lambda
function that grants `lambda:InvokeFunctionUrl` to the intended
callers:

```bash
# Add a resource-based policy allowing a principal to invoke the URL
aws lambda add-permission \
  --function-name my-function \
  --statement-id function-url-invoke \
  --action lambda:InvokeFunctionUrl \
  --principal arn:aws:iam::111122223333:user/alice \
  --function-url-auth-type AWS_IAM \
  --region us-east-1
```

For cross-account access, set `--principal` to the other account's
ARN. For service access (e.g., API Gateway, CloudFront), use the
service principal.


## Step 3 detail: CORS create/update CLI (moved from SKILL.md)

**Create a function URL with full CORS:**

```bash
aws lambda create-function-url-config \
  --function-name my-function \
  --auth-type AWS_IAM \
  --invoke-mode BUFFERED \
  --cors '{
    "AllowOrigins": ["https://example.com"],
    "AllowMethods": ["GET", "POST"],
    "AllowHeaders": ["content-type", "authorization"],
    "ExposeHeaders": ["date", "x-request-id"],
    "MaxAgeSeconds": 86400
  }' \
  --region us-east-1
```

**Update CORS on an existing function URL:**

```bash
aws lambda update-function-url-config \
  --function-name my-function \
  --cors '{
    "AllowOrigins": ["https://example.com", "https://staging.example.com"],
    "AllowMethods": ["GET", "POST", "PUT", "DELETE"],
    "AllowHeaders": ["content-type", "authorization", "x-api-key"],
    "ExposeHeaders": ["date", "x-request-id", "x-trace-id"],
    "MaxAgeSeconds": 3600
  }' \
  --region us-east-1
```

