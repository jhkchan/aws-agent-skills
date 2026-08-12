# Eval prompt: saml-provider-cert-mismatch

Diagnose the Cognito SAML authentication failure for the following User
Pool and SAML provider. Walk the symptom-driven diagnostic tree and emit
the standard diagnostic block (TARGET, VERDICT, REASON, LAYER, EVIDENCE,
REMEDIATION).

Symptom: SAML login via Okta stopped working 2 days ago. Users
authenticate on Okta successfully but Cognito returns
`SAMLResponseDoesNotMatch` after the IdP redirect.

```text
UserPoolId: us-east-1_MnOpQr789
ProviderName: OktaSAML
ProviderType: SAML
ProviderDetails:
  MetadataURL: https://example.okta.com/app/abc123/sso/saml/metadata
  (Cognito last fetched metadata 5 days ago — before Okta
   rotated the signing certificate)

Error:
  { "__type": "SAMLResponseDoesNotMatch",
    "message": "SAML assertion signature does not match the
    certificate in the provider metadata." }

Okta context:
  - Okta rotated its SAML signing certificate 2 days ago
  - Okta metadata at the MetadataURL now contains the NEW cert
  - Cognito has not re-fetched the metadata since the rotation
```

The SAML provider metadata in Cognito is stale. Okta rotated its signing
certificate, and Cognito is validating the SAML assertion against the
old certificate. The fix is to update the provider metadata.
