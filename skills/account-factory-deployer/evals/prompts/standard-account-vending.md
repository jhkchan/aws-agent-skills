# Eval: standard-account-vending

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — Service Catalog provisioning, registered OU, Guardrail inheritance, SSO permission set, baseline StackSets

## Prompt

Vend a new AWS account "data-platform-prod" via Control Tower Account
Factory in us-east-1. Root email
aws+prod-data-platform@company.com. Target OU "Custom (DataPlatform)"
(ou-bbb-ccc). SSO admin email platform-lead@company.com. Assign
DataEngineerAccess permission set to group DataPlatformTeam.
Management account 123456789012. Identity Center instance ssoins-12345.
Tags: Environment=production, OU=DataPlatform.
