# Eval: kvs-size-limit-exceeded

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — 8000 IPs exceed feasible KVS usage (function 1 ms execution limit, store size); recommend WAF IP sets

## Prompt

I want to store a blocklist of 8000 IP addresses in a CloudFront
KeyValueStore. Each IP is about 20 characters. I need the function
to check each incoming request against all 8000 entries. Create a
KVS named big-blocklist-kvs. Account ID: 123456789012.
