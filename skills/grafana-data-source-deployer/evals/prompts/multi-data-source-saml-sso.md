# Eval: multi-data-source-saml-sso

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — multi-data-source (CloudWatch + Athena + Timestream), SAML SSO with Okta IdP, all per-service permissions noted

## Prompt

Create a Managed Grafana workspace named enterprise-grafana
in us-east-1. Use SAML SSO authentication with Okta as the IdP.
IdP metadata URL: https://idp.example.com/saml/metadata.
Permission type CUSTOM. Data sources: CloudWatch, Athena
(workgroup primary, results bucket s3://athena-results-123456789012),
and Timestream. Workspace IAM role GrafanaWorkspaceRole with
per-service read permissions for all three data sources.
Tags: Environment=production, Auth=saml.
