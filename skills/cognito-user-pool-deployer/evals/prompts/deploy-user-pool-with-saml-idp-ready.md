# Eval prompt: deploy-user-pool-with-saml-idp-ready

Plan the following Cognito user pool creation with SAML federation and
emit the standard VERDICT block.

Operation: create
Pool name: corp-workforce-pool
Region: us-east-1
Account: 111111111111
Username attributes: ["email"]
Schema:
  - Name: email, Type: String, Required: true
  - Name: given_name, Type: String
  - Name: family_name, Type: String
PasswordPolicy: MinLength=14, all classes=true
MfaConfiguration: ON
EnabledMfas: ["TOTP"]
AdvancedSecurityMode: ENFORCED
DeletionProtection: ACTIVE
PreventUserExistenceErrors: ENABLED
Identity providers:
  - Name: CorpOkta
    Type: SAML
    MetadataURL: https://corp.okta.com/app/abc123/sso/saml
    AttributeMapping:
      email: http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress
      given_name: http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname
App client:
  Name: corp-web-app
  GenerateClientSecret: true
  ExplicitAuthFlows: ALLOW_USER_SRP_AUTH, ALLOW_REFRESH_TOKEN_AUTH
  AllowedOAuthFlows: code
  AllowedOAuthScopes: openid email profile
  CallbackURLs: ["https://workforce.example.com/auth/callback"]

```json
{
  "PreFlight": {
    "curl.corp.okta.com.MetadataURL": "200 OK, returns XML with EntityDescriptor",
    "iam.get-role.CognitoOperatorRole": "OK"
  }
}
```
