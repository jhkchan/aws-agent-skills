# Baseline (no-skill) response: dns-failover-ttl-stale-record

---

Your DNS failover is taking too long. This is probably because of DNS
caching. When you set a TTL of 300 seconds, DNS resolvers will cache
the old record for up to 5 minutes. You should lower the TTL to 60
seconds for faster failover.

Also check the health check interval and failure threshold — with 30s
interval and 3 threshold, it takes 90 seconds for Route 53 to detect
the failure. You could lower the threshold or switch to 10-second
interval checks for faster detection.
