# Eval: lambda-authorizer-waf

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — Lambda authorizer ws-auth on $connect (identity source: query string token), WAF Web ACL for IP rate limiting, DynamoDB connection management

## Prompt

Create a WebSocket API named my-secure-ws-api in us-east-1.
Route selection expression $request.body.action. Lambda
custom authorizer ws-auth on $connect (identity source:
query string token). WAF Web ACL ws-waf for IP rate limiting
on stage prod. $connect stores ConnectionId in DynamoDB
SecureConnections. Routes: sendMessage, broadcast.
Auto-deploy stage prod. Tags: Environment=production,
Service=secure-realtime.
