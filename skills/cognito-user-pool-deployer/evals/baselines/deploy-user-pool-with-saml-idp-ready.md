# Baseline (no-skill) response: deploy-user-pool-with-saml-idp-ready

This file captures what a generic assistant produces WITHOUT the
cognito-user-pool-deployer skill loaded.

---

To create a user pool federated with Okta SAML:

```bash
aws cognito-idp create-user-pool \
  --pool-name corp-workforce-pool \
  --username-attributes '["email"]' \
  --mfa-configuration ON

aws cognito-idp create-identity-provider \
  --user-pool-id <id> \
  --provider-name CorpOkta \
  --provider-type SAML \
  --provider-details '{"MetadataURL":"https://corp.okta.com/app/abc123/sso/saml"}'
```

Make sure your SAML metadata URL is reachable.
