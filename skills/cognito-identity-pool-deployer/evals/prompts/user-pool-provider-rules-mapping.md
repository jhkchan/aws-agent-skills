# Eval: user-pool-provider-rules-mapping

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — User Pool federation, rules-based mapping (admins/readers), guest access, both roles

## Prompt

Create a Cognito Identity Pool for my application. Federate
from Cognito User Pool us-east-1_AbCdEf123 with client ID
abc123def456. Pool name: app-identity-pool. I need guest access
enabled. Use rules-based role mapping: cognito:groups containing
"admins" should get AdminRole, "readers" should get ReaderRole.
Default authenticated role: AppAuthenticatedRole. Unauthenticated
role: AppUnauthenticatedRole. Account: 123456789012. Region
us-east-1. Tags: Environment=production, Application=app.
