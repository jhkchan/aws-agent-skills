# Eval prompt: cors-preflight-headers-missing

Diagnose the API Gateway HTTP API failure for the following API. Walk
the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: Browser console shows `Access to fetch at
'https://api.example.com/data' from origin 'https://app.example.com'
has been blocked by CORS policy: No 'Access-Control-Allow-Origin'
header`. The preflight `OPTIONS` request returns 404.

```text
ApiId: api-cors-preflight
ProtocolType: HTTP
Stage: $default
AutoDeploy: true
CorsConfiguration:
  AllowOrigins: ["https://app.example.com"]
  AllowMethods: ["GET", "POST"]
  AllowHeaders: ["Content-Type", "Authorization"]
  MaxAge: 300

RouteKey: ANY /data
IntegrationType: AWS_PROXY
IntegrationSubtype: Lambda
```

Note: `AllowMethods` does not include `OPTIONS`. The browser sends a
preflight `OPTIONS` request before the actual `GET`/`POST`. API
Gateway has no route for `OPTIONS` and returns 404. Identify the CORS
misconfiguration as the root cause.
