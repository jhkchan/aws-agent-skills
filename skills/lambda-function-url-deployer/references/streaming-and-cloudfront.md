# Response Streaming and CloudFront — Lambda Function URL Deployer

Deep reference on RESPONSE_STREAM invoke mode (handler signature,
streaming mechanics, first-byte advantage, runtime support),
CloudFront integration (custom domain, origin configuration, caching
strategy, WAF, TLS via ACM), and cold start mitigation with
provisioned concurrency. Loaded on demand by the skill — kept out
of the main SKILL.md body so the provisioning procedure stays
scannable.

## Response streaming fundamentals

### BUFFERED vs RESPONSE_STREAM

| Aspect | BUFFERED | RESPONSE_STREAM |
|---|---|---|
| Response delivery | Full payload buffered before return | Streamed in chunks as generated |
| Time to first byte | Full handler execution time | Handler init + first chunk |
| Max response size | 6 MB | Bounded by 15s timeout |
| HTTP semantics | Standard request-response | HTTP chunked transfer encoding |
| Handler signature | `return { statusCode, body }` | Uses `responseStreamWriter` |
| Error reporting | Errors returned as HTTP status before body | Errors mid-stream are HTTP 200 with error in body |

### RESPONSE_STREAM handler signature (Node.js)

```javascript
const awslambda = require("aws-lambda");

exports.handler = awslambda.streamifyResponse(
  async (event, responseStream, context) => {
    // Set content type (must be called before writing)
    responseStream.setContentType("text/event-stream");

    // Write metadata (optional — sent before the body stream)
    const metadata = {
      statusCode: 200,
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
      },
    };

    // Stream data
    for (let i = 0; i < 10; i++) {
      responseStream.write(`data: chunk ${i}\n\n`);
      await new Promise((r) => setTimeout(r, 200));
    }

    // End the stream
    responseStream.end();
  }
);
```

### RESPONSE_STREAM handler signature (Python)

Python requires a wrapper for streaming support:

```python
from awslambdaric.lambda_context import LambdaContext

def handler(event, context):
    # Python streaming support via wrapper
    import io
    
    output = io.StringIO()
    output.write("data: first chunk\n\n")
    output.write("data: second chunk\n\n")
    output.write("data: final chunk\n\n")
    
    return {
        "statusCode": 200,
        "body": output.getvalue()
    }
```

Note: Python does not have native streaming support equivalent to
Node.js `streamifyResponse`. For true streaming, use Node.js or
Java. Python responses are buffered by the runtime.

### First-byte advantage for LLM token streaming

```text
BUFFERED (LLM token streaming):
  Client → Function URL → Lambda → LLM generates all tokens →
  200 OK + full response body
  Time to first byte = total generation time (e.g., 5-10 seconds)

RESPONSE_STREAM (LLM token streaming):
  Client → Function URL → Lambda → LLM generates first token →
  200 OK + first token chunk → next token chunk → ... → stream end
  Time to first byte = first token generation time (e.g., 200ms)
```

For LLM workloads (streaming completions), RESPONSE_STREAM reduces
perceived latency from the full generation time to the first-token
generation time. This is critical for user experience in chat
interfaces.

### RESPONSE_STREAM error handling

In RESPONSE_STREAM mode, the HTTP status code (200 OK) is sent
BEFORE the body stream begins. If an error occurs mid-stream:

- The HTTP status is already 200 (cannot change it).
- The error must be encoded in the response body (e.g., as an error
  event in SSE format).

```javascript
exports.handler = awslambda.streamifyResponse(
  async (event, responseStream, context) => {
    responseStream.setContentType("text/event-stream");
    try {
      // Stream LLM tokens
      for await (const token of llmStream(event.prompt)) {
        responseStream.write(`data: ${JSON.stringify({ token })}\n\n`);
      }
    } catch (error) {
      // Error mid-stream — send as event (status already 200)
      responseStream.write(
        `event: error\ndata: ${JSON.stringify({ error: error.message })}\n\n`
      );
    }
    responseStream.end();
  }
);
```

## CloudFront integration

### Why use CloudFront in front of a function URL

Lambda Function URLs do not natively support custom domains. To use
a custom domain (e.g., `api.example.com`), place CloudFront in
front:

```text
Client → CloudFront distribution (custom domain: api.example.com)
       → Edge location (global, low-latency)
       → Origin: https://<id>.lambda-url.<region>.on.aws/
       → Lambda function URL → Lambda handler
```

Benefits:
- Custom domain with TLS (via ACM certificate).
- Edge caching (if the response is cacheable).
- DDoS protection (AWS Shield Standard included).
- WAF integration (filter by IP, rate-limit, inspect patterns).
- IPv6 client support (enable on CloudFront distribution).

### CloudFront distribution configuration

```bash
aws cloudfront create-distribution \
  --distribution-config '{
    "CallerReference": "lambda-url-dist-'$(date +%s)'",
    "Origins": {
      "Quantity": 1,
      "Items": [
        {
          "Id": "lambda-url-origin",
          "DomainName": "abc123def456.lambda-url.us-east-1.on.aws",
          "CustomOriginConfig": {
            "HTTPPort": 443,
            "HTTPSPort": 443,
            "OriginProtocolPolicy": "https-only",
            "OriginSslProtocols": {
              "Quantity": 1,
              "Items": ["TLSv1.2"]
            }
          }
        }
      ]
    },
    "DefaultCacheBehavior": {
      "TargetOriginId": "lambda-url-origin",
      "ViewerProtocolPolicy": "redirect-to-https",
      "TrustedSigners": { "Enabled": false, "Quantity": 0 },
      "ForwardedValues": {
        "QueryString": true,
        "Cookies": { "Forward": "none" },
        "Headers": { "Quantity": 0 }
      },
      "MinTTL": 0,
      "DefaultTTL": 0,
      "MaxTTL": 0
    },
    "Enabled": true,
    "Comment": "CloudFront for Lambda Function URL"
  }' \
  --region us-east-1
```

### Caching strategy

For most function URL use cases (APIs, dynamic content), set
`DefaultTTL=0` (no caching):

```json
"MinTTL": 0,
"DefaultTTL": 0,
"MaxTTL": 0
```

For cacheable content (static responses, CDN-style use cases):

```json
"MinTTL": 60,
"DefaultTTL": 3600,
"MaxTTL": 86400
```

### Query string and header forwarding

If the handler reads query parameters, enable query string
forwarding:

```json
"ForwardedValues": {
  "QueryString": true,
  "Cookies": { "Forward": "none" },
  "Headers": { "Quantity": 0 }
}
```

If the handler reads specific headers (e.g., `Authorization`),
forward them:

```json
"ForwardedValues": {
  "QueryString": true,
  "Cookies": { "Forward": "all" },
  "Headers": {
    "Quantity": 2,
    "Items": ["Authorization", "Content-Type"]
  }
}
```

### Custom domain with ACM certificate

```bash
# Request ACM certificate (must be in us-east-1 for CloudFront)
aws acm request-certificate \
  --domain-name api.example.com \
  --validation-method DNS \
  --region us-east-1

# After DNS validation completes, get the certificate ARN
CERT_ARN=$(aws acm list-certificates \
  --output text \
  --query 'CertificateSummaryList[?DomainName==`api.example.com`].CertificateArn|[0]' \
  --region us-east-1)

# Update CloudFront distribution to use the custom domain + certificate
# (done via update-distribution with Aliases and ViewerCertificate)
```

### WAF integration

Attach a WAF Web ACL to the CloudFront distribution:

```bash
# Create a WAF Web ACL
aws wafv2 create-web-acl \
  --name lambda-url-waf \
  --scope CLOUDFRONT \
  --default-action '{"Allow":{}}' \
  --visibility-config '{
    "CloudWatchMetricsEnabled": true,
    "MetricName": "lambda-url-waf",
    "SampledRequestsEnabled": true
  }' \
  --rules '[
    {
      "Name": "rate-limit",
      "Priority": 1,
      "Action": { "Block": {} },
      "Statement": {
        "RateBasedStatement": {
          "Limit": 2000,
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

### CloudFront with IAM-auth function URLs

CloudFront cannot natively sign Lambda Function URL requests with
SigV4. Options:

1. **Use NONE auth + WAF + app-level auth** (simplest). The handler
   validates API keys or JWTs.

2. **Use Lambda@Edge to sign requests** (complex). A Lambda@Edge
   function on the `origin-request` event signs the request with
   SigV4 before forwarding to the function URL origin.

3. **Use CloudFront Functions to sign requests** (lightweight).
   CloudFront Functions (a lightweight JavaScript runtime) can
   sign requests, but implementing SigV4 in CloudFront Functions is
   non-trivial.

For most use cases, option 1 (NONE auth + WAF + app-level auth) is
recommended.

## Cold start mitigation with provisioned concurrency

### What is provisioned concurrency

Provisioned Concurrency pre-initializes execution environments so
that invocations do not incur cold start latency. When a request
arrives, the pre-initialized environment picks it up immediately.

### Enabling provisioned concurrency for function URLs

Function URLs benefit from provisioned concurrency when pointed at
an alias with a provisioned concurrency configuration:

```bash
# Create or update the alias
aws lambda publish-version \
  --function-name my-function \
  --region us-east-1

aws lambda update-alias \
  --function-name my-function \
  --name prod \
  --function-version 1 \
  --region us-east-1

# Set provisioned concurrency on the alias
aws lambda put-provisioned-concurrency-config \
  --function-name my-function \
  --qualifier prod \
  --provisioned-concurrent-executions 10 \
  --region us-east-1

# Point the function URL at the alias
aws lambda update-function-url-config \
  --function-name my-function \
  --qualifier prod \
  --auth-type AWS_IAM \
  --invoke-mode BUFFERED \
  --region us-east-1
```

**Critical:** the function URL must be pointed at the alias
(`--qualifier prod`) to benefit from provisioned concurrency. A
function URL pointing at `$LATEST` does NOT use provisioned
concurrency.

### RESPONSE_STREAM with provisioned concurrency

RESPONSE_STREAM + provisioned concurrency is the optimal
combination for latency-sensitive streaming workloads:

- Provisioned concurrency eliminates cold start (init time is zero).
- RESPONSE_STREAM sends the first byte as soon as the handler
  starts producing output.

This combination minimizes time-to-first-byte for LLM token
streaming and progressive rendering use cases.

## Terraform CloudFront + function URL example

```hcl
# Lambda function URL
resource "aws_lambda_function_url" "api" {
  function_name      = aws_lambda_function.api.function_name
  qualifier           = aws_lambda_alias.prod.name
  authorization_type = "NONE"
  invoke_mode        = "BUFFERED"

  cors {
    allow_origins     = ["https://api.example.com"]
    allow_methods     = ["GET", "POST", "PUT", "DELETE"]
    allow_headers     = ["content-type"]
  }
}

# CloudFront distribution
resource "aws_cloudfront_distribution" "api_cdn" {
  enabled             = true
  is_ipv6_enabled     = true
  comment             = "API CDN"
  default_root_object = ""

  aliases = ["api.example.com"]

  origin {
    domain_name = replace(aws_lambda_function_url.api.function_url, "https://", "")
    origin_id   = "lambda-url-origin"

    custom_origin_config {
      http_port              = 443
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    target_origin_id       = "lambda-url-origin"
    viewer_protocol_policy = "redirect-to-https"

    forwarded_values {
      query_string = true
      cookies {
        forward = "none"
      }
    }

    min_ttl     = 0
    default_ttl = 0
    max_ttl     = 0
  }

  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate.api_cert.arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }
}
```


## Step 4 detail: invoke-mode handlers and CLI (moved from SKILL.md)

**BUFFERED handler (Node.js):**

```javascript
exports.handler = async (event) => {
  return {
    statusCode: 200,
    body: JSON.stringify({ message: "Hello" })
  };
};
```

**RESPONSE_STREAM handler (Node.js):**

```javascript
exports.handler = awslambda.streamifyResponse(
  async (event, responseStream, context) => {
    responseStream.setContentType("text/plain");
    responseStream.write("First chunk\n");
    // Simulate incremental work
    await new Promise(r => setTimeout(r, 100));
    responseStream.write("Second chunk\n");
    responseStream.end();
  }
);
```

**Create a function URL with RESPONSE_STREAM:**

```bash
aws lambda create-function-url-config \
  --function-name my-streaming-function \
  --auth-type NONE \
  --invoke-mode RESPONSE_STREAM \
  --cors '{"AllowOrigins":["*"],"AllowMethods":["GET","POST"]}' \
  --region us-east-1
```


## Step 10 detail: custom domain via CloudFront (moved from SKILL.md)

```text
Client → CloudFront (custom domain: api.example.com)
       → Origin: https://<id>.lambda-url.<region>.on.aws/
       → Lambda function URL → Lambda handler
```

**CloudFront distribution for a function URL:**

```bash
# Create a CloudFront distribution with the function URL as origin
aws cloudfront create-distribution \
  --origin-domain-name "abc123def456.lambda-url.us-east-1.on.aws" \
  --default-cache-behavior '{
    "TargetOriginId": "lambda-url-origin",
    "ViewerProtocolPolicy": "redirect-to-https",
    "TrustedSigners": {"Enabled": false, "Quantity": 0},
    "ForwardedValues": {
      "QueryString": true,
      "Cookies": {"Forward": "none"},
      "Headers": {"Quantity": 0}
    },
    "MinTTL": 0,
    "DefaultTTL": 0,
    "MaxTTL": 0
  }' \
  --enabled \
  --region us-east-1
```

**Critical considerations for CloudFront + function URL:**
- Set `DefaultTTL=0` (no caching) unless the function returns
  cacheable content.
- Enable query string forwarding (`QueryString: true`) if the
  handler reads query parameters.
- For AWS_IAM auth function URLs, CloudFront cannot natively sign
  requests. Use NONE auth + CloudFront WAF + application-level auth,
  or use a Lambda@Edge / CloudFront Function to sign requests.
- For custom domain TLS, attach an ACM certificate to the CloudFront
  distribution.
- CloudFront adds latency (an extra hop) but provides edge caching,
  DDoS protection, and custom domain support.

**Attach a custom domain (ACM + CloudFront):**

```bash
# Request an ACM certificate (us-east-1 required for CloudFront)
aws acm request-certificate \
  --domain-name api.example.com \
  --validation-method DNS \
  --region us-east-1

# After validation, associate the certificate with CloudFront
# (done via CloudFront distribution update)
```

