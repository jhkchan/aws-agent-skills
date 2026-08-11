# Eval prompt: jwt-authorizer-audience-mismatch

Diagnose the API Gateway HTTP API failure for the following API. Walk
the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: HTTP API `api-jwt-audience` returns `403 Forbidden` with
`{"message": "User is not authorized"}}` on every request to
`GET /profile`. The client sends a valid JWT from Cognito.

```text
ApiId: api-jwt-audience
ProtocolType: HTTP
Stage: prod
AutoDeploy: true
RouteKey: GET /profile
AuthorizerId: auth-abc
AuthorizerType: JWT
IdentitySource: $request.header.Authorization
JwtConfiguration:
  Issuer: https://cognito-idp.us-east-1.amazonaws.com/us-east-1_abc123
  Audience: ["orders-api-client"]

Client token decoded (payload):
  iss: https://cognito-idp.us-east-1.amazonaws.com/us-east-1_abc123
  aud: ["profile-api-client"]
  exp: 1799900000
  sub: user-xyz
```

The issuer matches but the Audience in the authorizer config
(`orders-api-client`) does not match the `aud` claim in the token
(`profile-api-client`). Identify the JWT audience mismatch as the
root cause.
