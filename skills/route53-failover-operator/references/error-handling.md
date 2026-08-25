# Error Handling — Route 53 Failover Operator

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Malformed input handling

**Malformed input:** if the input JSON is invalid or missing required
fields, emit `VERDICT: ERROR` with `REASON: Hosted zone / record set
configuration is not valid JSON or is missing required fields — cannot
plan.` and `REMEDIATION: Re-fetch with aws route53 list-resource-record-
sets --hosted-zone-id <id> --output json and re-plan.`

## Failover failure-mode table (use during diagnose-failover)

| Symptom | Root cause | Fix |
|---|---|---|
| `test-dns-answer` still returns PRIMARY IP after health check unhealthy | TTL caching by recursive resolvers; or `ChangeResourceRecordSets` not yet INSYNC | Wait TTL seconds; poll `get-change`; verify `test-dns-answer` from multiple resolvers |
| PRIMARY health check `Healthy` but app is broken | Health check probe path too shallow (e.g., `/health` returns 200 while app is broken) | Deepen the probe (check a real endpoint), or add a calculated health check with a CloudWatch alarm on error rate |
| PRIMARY health check `Unhealthy` but failover did not happen | PRIMARY record missing `HealthCheckId`, or the record's routing policy is not `Failover`, or there is no SECONDARY record | Wire the health check to the PRIMARY record; add a SECONDARY record |
| Both records returned (both unhealthy) | PRIMARY and SECONDARY health checks both failing | Fix the secondary before failing over; Route 53 returns both as a last resort |
| Health check `Unhealthy` with reason "Connection timed out" | Endpoint firewall blocks Route 53 checker IPs (route53-checker-ips AWS-managed prefix list) | Allow the AWS Route 53 checker prefix list on the endpoint SG/firewall |
| Health check `Unhealthy` with reason "No response from server" | Endpoint crashed or port closed | Restart the endpoint service |
| Health check `Unhealthy` with reason "String not found" | Search string not in response body (app deployed a new build that changed the response) | Update `SearchString` or the application's health endpoint |
| Cross-account `AccessDenied` on `ChangeResourceRecordSets` | Operator role not granted by zone-owning account | Zone account attaches inline policy or shares via RAM |
| DNS still serves old IP from `dig` but `test-dns-answer` is correct | Recursive resolver / OS DNS cache | Wait TTL seconds; flush DNS (`sudo dscacheutil -flushcache` macOS, `sudo systemctl restart systemd-resolved` Linux) |
| Latency routing serves a "wrong" region | Latency DB has stale measurements; or endpoint moved | Use `test-dns-answer --resolver-ip <client-resolver>` to inspect per-resolver answers |
| Weighted routing returns a 0-weight record | Both records have weight 0; or weights mis-typed | Verify `Weight` values; sum of all weights for the same name+type = traffic distribution |
| `ChangeInfo` stuck `PENDING` > 5 minutes | Rare Route 53 backend delay | Open AWS support; do NOT submit a second change-batch for the same record |
