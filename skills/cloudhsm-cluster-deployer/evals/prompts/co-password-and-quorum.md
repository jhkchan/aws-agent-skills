# Eval: co-password-and-quorum

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — 2 CO users, CO password in Secrets Manager (KMS-encrypted), 2-of-2 quorum for destructive ops

## Prompt

Configure crypto officer management for CloudHSM cluster
cluster-abc123def. Create admin and officer2 as CO users. CO
password must be stored in Secrets Manager (encrypted with
customer-managed KMS key). Document a quorum policy of 2-of-2 COs
for destructive operations. CU users: app-tls-user,
app-code-sign-user. Password policy: min 14 chars, mixed, 90-day
rotation.
