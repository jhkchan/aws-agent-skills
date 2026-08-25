# Error Handling — API Gateway WebSocket Deployer

Error-handling deep dive moved verbatim from the SKILL.md body for
progressive disclosure (agentskills.io): symptom-to-cause remedies for
connection, routing, integration, and size-limit failures. Loaded on
demand by the skill.

---

## Error handling

### Connections not receiving server-pushed messages
- ConnectionId not stored in DynamoDB on $connect. Verify the
  $connect handler stores the ConnectionId. Check DynamoDB for the
  connection.

### Custom routes never fire
- Route selection expression does not match the client message
  format. If clients send `{ "type": "..." }` but the expression
  evaluates `$request.body.action`, routes never match. Verify the
  expression.

### Integrations return 500
- Lambda resource-based policy missing. Verify
  `lambda:InvokeFunction` is granted to `apigateway.amazonaws.com`
  with the correct source ARN. Use `aws lambda get-policy`.

### PostToConnection returns 410 Gone
- The client disconnected without $disconnect firing (e.g.,
  network failure). Delete the stale ConnectionId from DynamoDB.
  The 410 is expected; handle it gracefully.

### Connections drop after 2 hours
- Idle timeout. Implement keepalive (client-side ping or
  application-level heartbeat every 30-60 seconds).

### Large messages rejected (413)
- Message exceeds the 128 KB limit. Chunk the payload or offload
  to S3 and send a reference URL via WebSocket.
