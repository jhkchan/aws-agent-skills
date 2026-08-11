# Eval prompt: missing-jwt-issuer

Design a deployment plan for an HTTP API. Emit the standard VERDICT
block.

Requirements:

- API type: HTTP (v2)
- Endpoint type: REGIONAL (us-east-1)
- Routes and authorization:
  - GET /health [NONE]
  - GET /users [JWT]
  - POST /users [JWT]
- Integration: AWS_PROXY to Lambda `users-handler`
- Authorization: JWT (the user expects JWT protection on /users but
  did NOT specify the issuer URL or audience — they expect the skill
  to flag this as a missing prerequisite)
- CORS: allowOrigins=https://app.example.com
- Stage: `$default` with auto-deploy=true

The user said "JWT auth on /users" but provided no issuer URL, no
audience, and no Cognito user pool id. The skill must catch this
during the pre-flight specification gate and emit
PREREQUISITES_MISSING citing the missing issuer field.
