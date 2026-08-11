# Eval prompt: deploy-app-client-client-credentials-ready

Plan the following Cognito user pool extension (resource server +
machine-to-machine app client using client-credentials grant) and emit
the standard VERDICT block.

Operation: create
Pool name: prod-platform-pool (existing pool-id: us-east-1_abc123)
Region: us-east-1
Account: 111111111111
Existing pool MFA: ON TOTP, ASF ENFORCED, deletion protection ACTIVE

Resource server:
  Identifier: https://api.example.com
  Name: products-api
  Scopes:
    - products.read (Read products)
    - products.write (Write products)

New app client (M2M):
  Name: m2m-orders-service
  GenerateClientSecret: true
  ExplicitAuthFlows: ALLOW_CUSTOM_AUTH, ALLOW_REFRESH_TOKEN_AUTH
  AllowedOAuthFlows: client-credentials
  AllowedOAuthScopes: ["https://api.example.com/products.read"]
  AccessTokenValidity: 1 hour

```json
{
  "PreFlight": {
    "describe-user-pool.us-east-1_abc123": "OK (MfaConfiguration ON, AdvancedSecurityMode ENFORCED)",
    "list-resource-servers": "no resource server with identifier https://api.example.com",
    "iam.get-role.CognitoOperatorRole": "OK"
  }
}
```
