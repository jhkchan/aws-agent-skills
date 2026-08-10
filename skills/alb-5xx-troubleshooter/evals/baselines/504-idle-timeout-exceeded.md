# Baseline (no-skill) response: 504-idle-timeout-exceeded

This file captures what a generic assistant produces WITHOUT the
alb-5xx-troubleshooter skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, layer identification,
evidence-backed root cause, error-code-driven probe order).

---

The 504 timeout means your backend is taking too long to respond. The
ALB has a 60 second idle timeout by default, and if your target takes
longer than that, you'll get a 504.

You can increase the idle timeout in the load balancer attributes. Or
you should optimize your backend to respond faster. For long-running
requests like report generation, consider using an asynchronous pattern
where the API returns immediately and the client polls for the result.
