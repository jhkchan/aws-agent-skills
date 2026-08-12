# Eval: custom-routes-selection

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — custom routes (sendMessage, joinRoom, leaveRoom), $default route, route selection expression matching message format, DynamoDB connection management

## Prompt

Create a WebSocket API named my-collab-api in us-east-1.
Route selection expression $request.body.action. Custom
routes: sendMessage (Lambda ws-message-handler), joinRoom
(Lambda ws-room-handler), leaveRoom (Lambda ws-room-handler).
$connect stores ConnectionId in DynamoDB CollaboratorConnections.
$default route for unmatched messages. Auto-deploy stage prod.
Tags: Environment=production, Service=collab.
