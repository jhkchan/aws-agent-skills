# Response headers policy IaC templates

Loaded on demand when the skill needs the full CloudFormation or
Terraform template for a custom or managed response headers policy.

## CloudFormation — custom policy with security + CORS

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Parameters:
  PolicyName:
    Type: String
    Default: prod-security-headers
Resources:
  ResponseHeadersPolicy:
    Type: AWS::CloudFront::ResponseHeadersPolicy
    Properties:
      ResponseHeadersPolicyConfig:
        Name: !Ref PolicyName
        SecurityHeadersConfig:
          ContentSecurityPolicy:
            Content: "default-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'self'"
            Override: true
          StrictTransportSecurity:
            AccessControlMaxAgeSec: 63072000
            IncludeSubdomains: true
            Preload: true
            Override: true
          XFrameOptions:
            FrameOption: DENY
            Override: true
          XContentTypeOptions:
            Override: true
          ReferrerPolicy:
            ReferrerPolicy: "strict-origin-when-cross-origin"
            Override: true
          PermissionsPolicy:
            Content: "camera=(), microphone=(), geolocation=(), payment=()"
            Override: true
        CorsConfig:
          AccessControlAllowOrigins:
            Items:
              - "https://app.example.com"
            Quantity: 1
          AccessControlAllowMethods:
            Items:
              - GET
              - POST
              - OPTIONS
            Quantity: 3
          AccessControlAllowHeaders:
            Items:
              - Authorization
              - Content-Type
            Quantity: 2
          AccessControlAllowCredentials: true
          AccessControlExposeHeaders:
            Items:
              - X-Total-Count
            Quantity: 1
          AccessControlMaxAgeSec: 86400
          OriginOverride: true
        CustomHeadersConfig:
          Items:
            - Header: X-Content-Classification
              Value: Restricted
              Override: true
            - Header: X-Service-Version
              Value: "1.2.3"
              Override: true
        RemoveHeadersConfig:
          Items:
            - Header: X-Powered-By
            - Header: X-AspNet-Version
            - Header: X-AspNetMvc-Version
```

## CloudFormation — managed policy attachment (Distribution update)

```yaml
DistributionUpdate:
  Type: AWS::CloudFront::Distribution
  Properties:
    DistributionConfig:
      # ... existing distribution config ...
      DefaultCacheBehavior:
        # ... existing behavior config ...
        ResponseHeadersPolicyId: "0857826db9cffff310d5ad62955c9c26"  # SecurityHeadersPolicy
```

Managed policy IDs (region-agnostic, account-agnostic):

| Managed policy | ID |
|---|---|
| `SecurityHeadersPolicy` | `0857826db9cffff310d5ad62955c9c26` |
| `SimpleCORS` | `608323ce734e4449839d234493be9c7c` |
| `CORS-with-preflight-and-SecurityHeadersPolicy` | `5cc3b908-e619-4b99-88e5-2ca770afe08f` |
| `CORSAndHTTPSecurityHeadersPolicy` | `e0bbb029-0798-45b7-9b86-9e6a1c2670e4` |

## Terraform — custom policy

```hcl
resource "aws_cloudfront_response_headers_policy" "security" {
  name = var.policy_name

  security_headers_config {
    content_security_policy {
      content   = "default-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'self'"
      override  = true
    }
    strict_transport_security {
      access_control_max_age_sec = 63072000
      include_subdomains         = true
      preload                    = true
      override                   = true
    }
    frame_options {
      frame_option = "DENY"
      override     = true
    }
    content_type_options {
      override = true
    }
    referrer_policy {
      referrer_policy = "strict-origin-when-cross-origin"
      override        = true
    }
    permissions_policy {
      content  = "camera=(), microphone=(), geolocation=(), payment=()"
      override = true
    }
  }

  cors_config {
    access_control_allow_credentials = true

    access_control_allow_origins {
      items = ["https://app.example.com"]
    }
    access_control_allow_methods {
      items = ["GET", "POST", "OPTIONS"]
    }
    access_control_allow_headers {
      items = ["Authorization", "Content-Type"]
    }
    access_control_expose_headers {
      items = ["X-Total-Count"]
    }
    access_control_max_age_sec = 86400
    origin_override            = true
  }

  custom_headers_config {
    items {
      header   = "X-Content-Classification"
      value    = "Restricted"
      override = true
    }
  }

  remove_headers_config {
    items {
      header = "X-Powered-By"
    }
    items {
      header = "X-AspNet-Version"
    }
  }
}

# Attach to distribution
resource "aws_cloudfront_distribution" "this" {
  # ... existing distribution config ...
  default_cache_behavior {
    # ... existing behavior config ...
    response_headers_policy_id = aws_cloudfront_response_headers_policy.security.id
  }
}
```

## CLI — attach policy to existing distribution

```bash
# 1. Snapshot the current distribution config
aws cloudfront get-distribution-config --id <distribution-id> \
  --output json > /tmp/dist-backup.json

# 2. Extract the ETag
ETAG=$(jq -r '.ETag' /tmp/dist-backup.json)

# 3. Modify the DistributionConfig to set ResponseHeadersPolicyId
#    on the target cache behavior
jq '.DistributionConfig.DefaultCacheBehavior.ResponseHeadersPolicyId = "<policy-id>"' \
  /tmp/dist-backup.json > /tmp/dist-updated.json

# 4. Apply the update
aws cloudfront update-distribution --id <distribution-id> \
  --if-match "$ETAG" \
  --distribution-config file:///tmp/dist-updated.json

# 5. Wait for Deployed state
aws cloudfront wait distribution-deployed --id <distribution-id>
```

## CSP Report-Only testing pattern

Before enforcing CSP, test in Report-Only mode (browsers log violations
but do not block). CloudFront does NOT support Report-Only natively —
use a Lambda@Edge or CloudFront Function:

```javascript
// CloudFront Function (viewer-response)
function handler(event) {
  var response = event.response;
  response.headers['content-security-policy-report-only'] = {
    value: "default-src 'self'; report-uri https://app.example.com/csp-report"
  };
  return response;
}
```

Once the report endpoint shows zero violations over a week, switch to
the enforced CSP in the response headers policy.
