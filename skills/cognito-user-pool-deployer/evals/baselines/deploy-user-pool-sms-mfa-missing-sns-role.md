# Baseline (no-skill) response: deploy-user-pool-sms-mfa-missing-sns-role

This file captures what a generic assistant produces WITHOUT the
cognito-user-pool-deployer skill loaded.

---

To create your user pool with SMS MFA:

```bash
aws cognito-idp create-user-pool \
  --pool-name prod-b2c-pool \
  --mfa-configuration ON \
  --enabled-mfas '["SMS"]' \
  --sms-configuration 'SnsCallerArn=arn:aws:iam::111111111111:role/CognitoSmsCaller,ExternalId=pool-prod-b2c' \
  --username-attributes '["phone_number"]'
```

Make sure the SNS caller role has permission to publish to SNS.
