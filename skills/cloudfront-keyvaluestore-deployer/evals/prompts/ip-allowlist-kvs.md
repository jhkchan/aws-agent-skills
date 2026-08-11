# Eval: ip-allowlist-kvs

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — KVS for IP blocklist, function checks viewer.ip, 403 response, KVS-vs-WAF tradeoff noted

## Prompt

Create a CloudFront KeyValueStore named ip-blocklist-kvs for
blocking specific IPs at the edge. I need to block
192.168.1.10, 10.0.0.5, and 172.16.0.3. Create a CloudFront
Function named ip-blocker that checks viewer IP against the KVS
and returns 403 for blocked IPs. Distribution E456789012GHI.
Account ID: 123456789012.
