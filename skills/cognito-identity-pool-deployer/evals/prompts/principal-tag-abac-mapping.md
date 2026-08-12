# Eval: principal-tag-abac-mapping

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — principal tag mapping (Department from cognito:groups, Division from custom:division)

## Prompt

Create a Cognito Identity Pool with Cognito User Pool provider
(us-east-1_XyZ456, client: myclient789). Pool name: abac-pool.
I need principal tag mapping for ABAC: map the cognito:groups
claim to the Department session tag, and the custom:division
claim to the Division tag. Authenticated role: ABACRole. No
guest access. Account: 123456789012. Region us-east-1.
