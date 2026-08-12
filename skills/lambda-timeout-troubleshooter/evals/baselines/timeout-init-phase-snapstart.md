# Baseline (no-skill) response: timeout-init-phase-snapstart

---

Your Lambda function is timing out at 8 seconds. The error says
TaskTimeoutException, which means the function took longer than the
configured timeout. Try increasing the timeout to 30 or 60 seconds.

Since it's a Java function, cold starts can be slow. You might want to
add more memory as well — Java functions generally need at least 1 GB.
If that doesn't help, consider optimising your Spring Boot startup.
