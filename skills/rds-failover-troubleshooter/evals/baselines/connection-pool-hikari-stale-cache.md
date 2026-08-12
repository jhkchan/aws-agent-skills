# Baseline (no-skill) response: connection-pool-hikari-stale-cache

---

The Aurora failover completed quickly but the application took several
minutes to recover. Since the cluster endpoint is correct and DNS TTL
is 1 second, the issue might be with the connection pool caching old
connections.

Try reducing the HikariCP maxLifetime or restarting the application
after failover to force new connections.
