# Baseline (no-skill) response: timeout-http-client-no-connect

---

Your Lambda is timing out at 10 seconds. The function calls an external
API so the partner service is probably slow. You should increase the
Lambda timeout to 30 seconds to give the call more time.

If the partner API is still slow, contact them to fix their service.
You might also want to add a retry mechanism in case the call fails.
