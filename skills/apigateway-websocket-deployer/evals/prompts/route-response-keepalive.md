# Eval: route-response-keepalive

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — route response on sendMessage for bidirectional, ping route for client heartbeat (60s interval), 128 KB message limit noted

## Prompt

Create a WebSocket API named my-bidirectional-api in
us-east-1. Route selection expression $request.body.action.
Enable route response on sendMessage route for bidirectional
communication. Add ping route for client heartbeat (interval
60s). $connect and $disconnect manage ConnectionId in
DynamoDB BidirectionalConnections. Auto-deploy stage prod.
Tags: Environment=production, Service=realtime-bidirectional.
