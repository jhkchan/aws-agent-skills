# Custom Rules, Rate-Based Rules, and Label Chaining — WAF Rule Deployer

Deep reference on custom rule authoring (statement types, field
matching, transforms), rate-based rule configuration (aggregation
keys, forwarded IP, custom keys), label-based rule chaining
(emitting labels, matching labels, priority constraints), and
action types (COUNT for safe rollout, CAPTCHA vs Challenge).
Loaded on demand by the skill — kept out of the main SKILL.md body
so the provisioning procedure stays scannable.

## Custom rule statement types

### ByteMatchStatement

Matches a string pattern in a request component.

```json
{
  "ByteMatchStatement": {
    "SearchString": "BadBot",
    "FieldToMatch": {
      "SingleHeader": { "Name": "User-Agent" }
    },
    "TextTransformations": [
      { "Priority": 0, "Type": "NONE" }
    ],
    "PositionalConstraint": "CONTAINS"
  }
}
```

**PositionalConstraint values:** EXACTLY, STARTS_WITH, ENDS_WITH,
CONTAINS, CONTAINS_WORD, EXACTLY_PREFIX (prefix match).

**FieldToMatch options:** SingleHeader, SingleQueryArgument,
AllQueryArguments, UriPath, QueryString, Body, JsonBody,
Method, Cookie.

**TextTransformations:** apply transforms before matching. Types:
NONE, LOWERCASE, UPPERCASE, URL_DECODE, HTML_ENTITY_DECODE,
BASE64_DECODE, COMPRESS_WHITE_SPACE, CMD_LINE, HEX_DECODE.

**WCU cost:** 1 per condition. Multiple conditions in OrStatement
or AndStatement cost 1 + nested costs.

### GeoMatchStatement

Matches by country (ISO 3166-1 alpha-2 codes).

```json
{
  "GeoMatchStatement": {
    "CountryCodes": ["RU", "KP", "IR", "SY"]
  }
}
```

**WCU cost:** 3.

**Forwarded IP config (optional):** if traffic goes through a proxy,
configure `ForwardedIPConfig` to inspect `X-Forwarded-For` for the
original client country.

### IPSetReferenceStatement

Matches against a reusable IP set resource.

```json
{
  "IPSetReferenceStatement": {
    "ARN": "arn:aws:wafv2:us-east-1:123456789012:global-ipset/partner-cidrs/..."
  }
}
```

**WCU cost:** 1.

**Constraint:** the IP set must be in the same scope and region as
the Web ACL.

### RegexPatternSetReferenceStatement

Matches against a reusable regex pattern set.

```json
{
  "RegexPatternSetReferenceStatement": {
    "ARN": "arn:aws:wafv2:us-east-1:123456789012:global-regexpatternset/sqli-patterns/...",
    "FieldToMatch": { "UriPath": {} },
    "TextTransformations": [
      { "Priority": 0, "Type": "URL_DECODE" },
      { "Priority": 1, "Type": "LOWERCASE" }
    ]
  }
}
```

**WCU cost:** 25 (high — use sparingly).

### SizeConstraintStatement

Matches by request component size (bytes).

```json
{
  "SizeConstraintStatement": {
    "ComparisonOperator": "GT",
    "Size": 8192,
    "FieldToMatch": { "Body": {} },
    "TextTransformations": [
      { "Priority": 0, "Type": "NONE" }
    ]
  }
}
```

**ComparisonOperator:** EQ, NE, LE, LT, GE, GT.

**WCU cost:** 1.

### Compound statements

```json
{
  "AndStatement": {
    "Statements": [
      { "GeoMatchStatement": { "CountryCodes": ["RU"] } },
      { "ByteMatchStatement": { ... } }
    ]
  }
}
```

`OrStatement` and `NotStatement` follow the same pattern.

**WCU cost:** 1 + sum of nested statement costs.

## Rate-based rules

Rate-based rules limit requests from a single aggregation key in a
5-minute window.

### Configuration

```json
{
  "RateBasedStatement": {
    "Limit": 100,
    "AggregateKeyType": "IP",
    "EvaluationWindowSec": 300,
    "ScopeDownStatement": {
      "ByteMatchStatement": {
        "SearchString": "/login",
        "FieldToMatch": { "UriPath": {} },
        "TextTransformations": [{ "Priority": 0, "Type": "NONE" }],
        "PositionalConstraint": "STARTS_WITH"
      }
    }
  }
}
```

### AggregateKeyType

| Key Type | Description | Use case |
|---|---|---|
| IP | Source IP address | Default; rate-limit by client IP |
| FORWARDED_IP | IP from X-Forwarded-For | Rate-limit behind proxy/CDN |
| CUSTOM | Custom key (header, query, etc.) | Rate-limit per user/session |
| CONSTANT | Single bucket for all | Global rate cap |

### FORWARDED_IP configuration

```json
{
  "RateBasedStatement": {
    "Limit": 100,
    "AggregateKeyType": "FORWARDED_IP",
    "ForwardedIPConfig": {
      "HeaderName": "X-Forwarded-For",
      "FallbackBehavior": "MATCH"
    }
  }
}
```

**FallbackBehavior:** `MATCH` (treat as match if header missing) or
`NO_MATCH` (skip if header missing).

### Custom keys (2024-2025 feature)

Custom keys allow rate-limiting by header value, query parameter, or
JSON body field — enabling per-user or per-session rate limiting
behind a proxy.

```json
{
  "RateBasedStatement": {
    "Limit": 50,
    "AggregateKeyType": "CUSTOM",
    "CustomKeys": [
      {
        "ForwardedIP": {}
      },
      {
        "Header": {
          "Name": "X-Session-ID",
          "TextTransformations": [{ "Priority": 0, "Type": "NONE" }]
        }
      }
    ]
  }
}
```

### ScopeDownStatement

A `ScopeDownStatement` limits the rate-based rule to a subset of
traffic. For example, rate-limit only `/login` requests, not all
traffic.

**WCU cost:** 1 + scope-down statement cost + any forwarded IP
config overhead.

## Label-based rule chaining

Labels allow rules to communicate. A rule with `RuleLabels` in its
action adds labels to the request metadata. A downstream rule
matches via `LabelMatchStatement`.

### Emitting a label

```json
{
  "Name": "detect-suspicious-header",
  "Priority": 10,
  "Action": {
    "Count": {},
    "RuleLabels": [
      { "Name": "suspicious-header-detected" }
    ]
  },
  "Statement": {
    "ByteMatchStatement": {
      "SearchString": "scanner",
      "FieldToMatch": { "SingleHeader": { "Name": "X-Bot-Type" } },
      "TextTransformations": [{ "Priority": 0, "Type": "LOWERCASE" }],
      "PositionalConstraint": "CONTAINS"
    }
  },
  "VisibilityConfig": { ... }
}
```

**Important:** labels are emitted only when the rule's action
matches. A rule with action ALLOW that matches emits its labels and
stops evaluation (the request is allowed). A rule with action COUNT
emits labels and continues evaluation. Use COUNT for labeling rules
so downstream rules can act on the label.

### Matching a label

```json
{
  "Name": "block-suspicious-and-geo",
  "Priority": 20,
  "Action": { "Block": {} },
  "Statement": {
    "AndStatement": {
      "Statements": [
        {
          "LabelMatchStatement": {
            "Scope": "LABEL",
            "Key": "awswaf:suspicious-header-detected"
          }
        },
        {
          "GeoMatchStatement": { "CountryCodes": ["RU", "KP"] }
        }
      ]
    }
  },
  "VisibilityConfig": { ... }
}
```

**Label namespace:** all labels are automatically prefixed with
`awswaf:`. The full key is `awswaf:<label-name>`.

**Label scope:** `LABEL` (rule-level labels) or `NAMESPACE` (match
all labels under a namespace prefix).

### Priority constraint

A label emitted by a rule at priority N is visible ONLY to rules
with priority > N. The upstream rule MUST be evaluated before the
downstream rule. WAF evaluates in priority order (lowest first),
so the labeling rule must have a lower priority number.

```text
Priority 10: detect-suspicious (COUNT, emits label)
  → label added to request metadata
Priority 20: block-suspicious-and-geo (BLOCK, matches label)
  → can see the label because 20 > 10
Priority 5: some-other-rule
  → CANNOT see the label because 5 < 10 (evaluated before label emitted)
```

## Action types

### ALLOW

Request passes to the protected resource. No further rules are
evaluated. Labels emitted by this rule are available to downstream
rules (but the request already passed).

### BLOCK

Request is dropped with HTTP 403 (default) or a custom response.
No further rules are evaluated.

**Custom block response:**

```json
{
  "Block": {
    "CustomResponse": {
      "ResponseCode": 403,
      "CustomResponseBodyKey": "blocked-page",
      "ResponseHeaders": [
        { "Name": "X-Block-Reason", "Value": "waf-rule" }
      ]
    }
  }
}
```

### COUNT

Request passes but is counted in CloudWatch metrics and sampled
requests. Evaluation continues to the next rule. Labels are emitted.

**Use case:** test a new rule before switching to BLOCK. Monitor
the COUNT metric to assess impact.

### CAPTCHA

Requires the client to solve a CAPTCHA. If solved, the request
proceeds with a token. If not, a CAPTCHA challenge page is returned.

**Use case:** bot mitigation on specific endpoints (login, form
submission). Not suitable for general traffic (disrupts UX).

```json
{
  "Captcha": {
    "CustomRequestHandling": {
      "InsertHeaders": [
        { "Name": "x-captcha-token", "Value": "verified" }
      ]
    }
  }
}
```

### Challenge

A silent browser challenge that requires JavaScript execution (no
puzzle). The browser solves a proof-of-work token automatically.

**Use case:** bot mitigation on general traffic without UX
disruption. Headless browsers and simple bots fail the challenge.

```json
{
  "Challenge": {
    "CustomRequestHandling": { ... }
  }
}
```

**Immunity time:** after a client passes a CAPTCHA or Challenge, a
token is issued that grants immunity for a configurable period
(default: 5 minutes). Subsequent requests with a valid token bypass
the CAPTCHA/Challenge action.

## Terraform custom rule example

```hcl
resource "aws_wafv2_web_acl" "production" {
  # ... (scope, default_action, etc.)

  rule {
    name     = "allow-partner-ip"
    priority = 0
    action {
      allow {}
    }
    statement {
      ip_set_reference_statement {
        arn = aws_wafv2_ip_set.partner_cidrs.arn
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "allow-partner-ip"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "rate-limit-login"
    priority = 100
    action {
      block {}
    }
    statement {
      rate_based_statement {
        limit              = 100
        aggregate_key_type = "IP"

        scope_down_statement {
          byte_match_statement {
            search_string         = "/login"
            field_to_match {
              uri_path {}
            }
            text_transformation {
              priority = 0
              type     = "NONE"
            }
            positional_constraint = "STARTS_WITH"
          }
        }
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "rate-limit-login"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "label-suspicious-header"
    priority = 10
    action {
      count {}
    }
    rule_label {
      name = "suspicious-header-detected"
    }
    statement {
      byte_match_statement {
        search_string         = "scanner"
        field_to_match {
          single_header {
            name = "X-Bot-Type"
          }
        }
        text_transformation {
          priority = 0
          type     = "LOWERCASE"
        }
        positional_constraint = "CONTAINS"
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "label-suspicious-header"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "block-suspicious-and-geo"
    priority = 20
    action {
      block {}
    }
    statement {
      and_statement {
        statement {
          label_match_statement {
            scope = "LABEL"
            key   = "awswaf:suspicious-header-detected"
          }
        }
        statement {
          geo_match_statement {
            country_codes = ["RU", "KP"]
          }
        }
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "block-suspicious-and-geo"
      sampled_requests_enabled   = true
    }
  }
}
```

## Common pitfalls

1. **Broad block before specific allow.** If the geo block (priority
   0) runs before the partner IP allow (priority 1), the partner IP
   in a blocked geo is denied. Always put specific allows at lower
   priority numbers.

2. **Rate-limiting on source IP behind a proxy.** All clients behind
   the proxy share one rate bucket. Use `FORWARDED_IP` with
   `X-Forwarded-For`.

3. **Label not visible to downstream rule.** The labeling rule must
   have a lower priority number than the label-matching rule.

4. **Using COUNT and forgetting to switch to BLOCK.** A rule left on
   COUNT forever provides no protection. Set a reminder to review
   COUNT metrics and switch to BLOCK.

5. **Regex pattern set match WCU explosion.** Each regex pattern set
   reference costs 25 WCU. Five references = 125 WCU. Use byte-match
   (1 WCU) where possible.

6. **CAPTCHA on general traffic.** CAPTCHA disrupts UX. Use Challenge
   (silent) for general traffic; reserve CAPTCHA for specific
   endpoints (login, registration).
