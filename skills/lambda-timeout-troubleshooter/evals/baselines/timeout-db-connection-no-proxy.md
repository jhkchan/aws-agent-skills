# Baseline (no-skill) response: timeout-db-connection-no-proxy

---

Your Lambda is timing out during database connections. The Aurora
cluster looks healthy so it's probably the function code. Try
increasing the Lambda timeout to 30 seconds and the memory to at least
512 MB.

Also consider moving the database connection outside the handler
function so it gets reused across invocations. That should reduce the
connection overhead.
