# Eval: basic-connect-disconnect

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — $connect/$disconnect routes with Lambda, DynamoDB ConnectionId storage, route selection expression, auto-deploy stage, PostToConnection via ApiGatewayManagementApi

## Prompt

Create a WebSocket API named my-chat-api in us-east-1.
Route selection expression $request.body.action. $connect
route invokes Lambda ws-connect-handler (stores ConnectionId
in DynamoDB table WebSocketConnections). $disconnect route
invokes Lambda ws-disconnect-handler (deletes ConnectionId).
Auto-deploy stage prod. Tags: Environment=production,
Service=chat.
