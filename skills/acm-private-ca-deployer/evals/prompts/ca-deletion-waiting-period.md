# Eval: ca-deletion-waiting-period

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — CA deletion with 30-day waiting period, restore capability documented, permanent deletion after expiry

## Prompt

Delete the subordinate CA
arn:aws:acm-pca:us-east-1:123456789012:certificate-authority/dddd-eeee-ffff
in us-east-1 with a 30-day permanent deletion waiting period.
Existing certificates should remain valid during this period.
Document the restore capability.
