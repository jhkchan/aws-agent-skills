# Eval: allow-list-without-fullawsaccess-detach

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — Allow-list SCP is silently redundant while FullAWSAccess remains attached at the same entity

## Prompt

Create an SCP named prod-allowlist that allows ec2:* and s3:*
for OU_Prod_Apps (ou-prod-apps-001). Do NOT detach
FullAWSAccess at this OU. Management account 123456789012.
