# Worked Examples - wafv2-web-acl-deployer

## Step 6 - rate-based rule JSON example (moved from SKILL.md)

```json
{
  "Name": "rate-limit-api",
  "Priority": 5000,
  "Action": { "Block": {} },
  "Statement": {
    "RateBasedStatement": {
      "Limit": 2000,
      "AggregateKeyType": "IP",
      "ScopeDownStatement": {
        "ByteMatchStatement": {
          "SearchString": "/api/",
          "FieldToMatch": { "UriPath": {} },
          "PositionalConstraint": "STARTS_WITH"
        }
      }
    }
  },
  "VisibilityConfig": { "SampledRequestsEnabled": true, "CloudWatchMetricsEnabled": true, "MetricName": "rate-limit-api" }
}
```

## Step 9 - CAPTCHA rule JSON (moved from SKILL.md)

**CAPTCHA rule:**

```json
{
  "Name": "captcha-signup",
  "Priority": 1000,
  "Action": { "Captcha": {} },
  "Statement": {
    "ByteMatchStatement": {
      "SearchString": "/signup",
      "FieldToMatch": { "UriPath": {} },
      "PositionalConstraint": "STARTS_WITH"
    }
  },
  "VisibilityConfig": { "SampledRequestsEnabled": true, "CloudWatchMetricsEnabled": true, "MetricName": "captcha-signup" }
}
```
