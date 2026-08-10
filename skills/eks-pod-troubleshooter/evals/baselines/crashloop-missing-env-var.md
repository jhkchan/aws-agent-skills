# Baseline (no-skill) response: crashloop-missing-env-var

This file captures what a generic assistant produces WITHOUT the
eks-pod-troubleshooter skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, category-aware walk,
specific remediation).

---

Your pod is in CrashLoopBackOff which means the container keeps
crashing. The exit code is 1 so it's an application error. The logs
show a KeyError on DB_HOST which means the application can't find the
DB_HOST environment variable.

You should add DB_HOST to the pod's environment variables. You can do
this in the deployment yaml under env. Also check that your database
is reachable from the pod.

You can also try to set restartPolicy: Never to stop the crash loop,
or increase resources on the pod.
