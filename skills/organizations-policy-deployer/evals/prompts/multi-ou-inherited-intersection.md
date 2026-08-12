# Eval: multi-ou-inherited-intersection

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — Deny-list SCP at parent OU, intersection inheritance traced at a child account

## Prompt

Create an SCP named prod-deny-root-tamper denying
iam:DeleteRole and iam:DetachRolePolicy. Attach it to OU_Prod
(ou-prod-001). Account 111122223311 lives under OU_Prod_Data
(ou-prod-data-001), a child of OU_Prod. Verify the inheritance
intersection is correctly traced at account 111122223311.
Management account 123456789012. Keep FullAWSAccess at both
OUs.
