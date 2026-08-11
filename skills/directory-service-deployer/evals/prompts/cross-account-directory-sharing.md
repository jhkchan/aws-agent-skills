# Eval: cross-account-directory-sharing

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — share Managed AD with target account 999999999999, accepter must accept, unsharing breaks accepter resources

## Prompt

Share Managed Microsoft AD directory d-aaa111222 with target
account 999999999999. The directory is in us-east-1, owner account
123456789012. Use HANDSHAKE method. Tags: Environment=production,
SharedWith=dev-account.
