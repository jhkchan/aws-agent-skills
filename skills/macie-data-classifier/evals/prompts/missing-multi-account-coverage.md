# Eval: missing-multi-account-coverage

**Difficulty:** medium
**Branch:** PARTIALLY_CLASSIFIED — admin account healthy but only 95/150 org accounts enrolled, 5 members PAUSED, 2 INVITED never accepted, ASDD auto-enable false

## Prompt

Audit the Macie data classification posture for the organization
with administrator account 123456789012 in us-east-1. Macie is
enabled in the admin account. ASDD is enabled. Classification
jobs cover all sensitive buckets in the admin account. Security
Hub export is enabled. However, when listing members, only 95 of
150 organization accounts are enrolled in Macie. Of those 95,
5 are in PAUSED status and 2 are in INVITED status (never
accepted). ASDD autoEnableOrganizationMembers is false.
