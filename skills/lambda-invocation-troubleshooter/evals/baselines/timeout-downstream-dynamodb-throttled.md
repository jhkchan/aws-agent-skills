# Baseline (no-skill) response: timeout-downstream-dynamodb-throttled

This file captures what a generic assistant produces WITHOUT the
lambda-invocation-troubleshooter skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, layer identification,
evidence-backed root cause, symptom-to-layer triage).

---

Your Lambda function is timing out. The error is TaskTimeoutException
which means it ran for 30 seconds and got killed. You should raise the
timeout to 60 seconds or 90 seconds. Also check that the function has
enough memory — 512 MB might be too low for some workloads. If that
doesn't help, look at the function code to see where it's spending time.

The fact that 70% of invocations succeed quickly suggests the slow
ones might be hitting a heavier code path. Try adding more logging to
see which branch is slow.
