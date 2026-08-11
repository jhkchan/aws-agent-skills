# Eval prompt: deploy-user-pool-sms-mfa-missing-sns-role

Plan the following Cognito user pool creation (SMS MFA) and emit the
standard VERDICT block. The SNS caller IAM role does not exist.

Operation: create
Pool name: prod-b2c-pool
Region: us-east-1
Account: 111111111111
Username attributes: ["phone_number"]
Schema:
  - Name: phone_number, Type: String, Required: true
  - Name: email, Type: String, Required: true
PasswordPolicy: MinLength=12, all classes=true
MfaConfiguration: ON
EnabledMfas: ["SMS"]
SmsConfiguration:
  SnsCallerArn: arn:aws:iam::111111111111:role/CognitoSmsCaller
  ExternalId: pool-prod-b2c
AdvancedSecurityMode: ENFORCED
DeletionProtection: ACTIVE
PreventUserExistenceErrors: ENABLED

```json
{
  "PreFlight": {
    "iam.get-role.CognitoSmsCaller": "NoSuchEntity (role does not exist)",
    "list-user-pools": "no pool named prod-b2c-pool",
    "iam.get-role.CognitoOperatorRole": "OK"
  }
}
```
