# Baseline (no-skill) response: liveness-probe-path-mismatch

This file captures what a generic assistant produces WITHOUT the
eks-pod-troubleshooter skill loaded.

---

Your pod is being restarted because the liveness probe is failing.
The probe returns 404, which means the path is wrong. The probe is
checking /healthz but the application is serving on a different path.

You should change the liveness probe path to match what your
application serves. Or you can lower the failureThreshold and
periodSeconds to make the probe more forgiving. Also consider raising
the initialDelaySeconds to give the app more time to start.
