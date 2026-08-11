# Eval: cross-account-ap-delegation

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — delegated AP creation + containment statement on foreign AP ARN

## Prompt

Bucket "shared-with-partner" in account 123456789012 (region
us-east-1) needs to let partner account 991122334455 create
their own access point named "partner-ap" scoped to prefix
"partner-data/". I want to delegate creation but contain the
foreign-owned AP so it cannot expose the "internal/" prefix.
