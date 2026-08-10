# End-to-end usage scenario: eks-pod-troubleshooter

A walkthrough showing the skill diagnosing a pod crash-loop caused by
a missing environment variable. This exercises Step 1 (symptom
identification), Step 4 (CRASH_LOOP), and the remediation workflow.

## Input (user prompt)

> My `api-server-5d4b6c7d8-x9fk2` pod in the `production` namespace on
> EKS is in CrashLoopBackOff. Restart count is 14. `kubectl logs
> --previous` shows `KeyError: 'DB_HOST'`. The pod env vars only have
> APP_PORT and LOG_LEVEL.

## Skill output

```text
INCIDENT: production/api-server-5d4b6c7d8-x9fk2 on node
ip-10-0-3-42.ec2.internal — CrashLoopBackOff (restart count 14)
VERDICT: ROOT_CAUSE_FOUND
ROOT_CAUSE: CRASH_LOOP — application reads `DB_HOST` env var that is
not set in the pod spec; container exits with code 1 in <1s
EVIDENCE:
  - kubectl describe pod: Last State: Terminated, Reason: Error, Exit
    Code: 1, Started/Finished ~0.8s apart
  - kubectl logs api-server-5d4b6c7d8-x9fk2 -n production -c api
    --previous: "Traceback ... KeyError: 'DB_HOST'"
  - kubectl get pod -o jsonpath
    '{.spec.containers[0].env}': APP_PORT, LOG_LEVEL present; DB_HOST
    absent
  - kubectl get events -n production --field-selector
    involvedObject.name=api-server-5d4b6c7d8-x9fk2: "Back-off
    restarting failed container" × N
ROOT_CAUSE_CATALOG: #7 (missing env var / ConfigMap)
REMEDIATION:
  1. Patch the Deployment to add DB_HOST (recommended: source from a
     ConfigMap so it is centralised):
     kubectl set env deployment/api-server -n production \
       --from configmap/api-config --keys DB_HOST
     (or inline: kubectl set env deployment/api-server -n production
       DB_HOST=postgres.production.svc.cluster.local)
  2. Watch the rollout:
     kubectl rollout status deployment/api-server -n production
  3. Verify the new pod reaches Running with restart count 0:
     kubectl get pods -n production -l app=api-server -w
  4. If DB connectivity is also wrong (logs then show
     "Connection refused"), check the Service name, NetworkPolicy,
     and security group on the RDS instance.
```

## What the skill caught that a generic assistant misses

1. **The exit-code-1-with-<1s-runtime signature.** A generic assistant
   often attributes "exit code 1" to "application error" or "OOM." The
   skill recognises that an ~0.8s container lifetime combined with a
   `KeyError` in the traceback is the classic missing-env-var pattern
   (catalog #7).

2. **`kubectl logs --previous` vs `kubectl logs`.** A generic
   assistant often reads the current logs — which are empty for a
   CrashLoopBackOff pod. The skill always uses `--previous` to read
   the crashed container's logs.

3. **The Deployment vs Pod distinction.** A generic assistant may
   recommend `kubectl edit pod` — which does not take effect because
   the Deployment controller will overwrite the change. The skill
   patches the Deployment so the change propagates to new pods.

4. **The DB connectivity escalation path.** The skill notes that if
   `DB_HOST` is set correctly but the app still fails, the next cause
   is Service DNS, NetworkPolicy, or RDS security group — giving the
   operator the next step without re-diagnosing from scratch.

## Slash-command invocation

```
/aws:troubleshoot-eks-pod
```

Or via the orchestrator:

```
/aws:pipeline
You: "api-server pod in production keeps CrashLoopBackOff, logs show KeyError DB_HOST"
```

The orchestrator emits `[Phase: Troubleshoot | Skills routed:
eks-pod-troubleshooter]` and hands off to this skill for the VERDICT.

## Live-cluster diagnostic flow (requires kubectl + AWS CLI)

When the operator has kubeconfig and AWS credentials:

```bash
# Capture the failure signal.
kubectl get pod api-server-5d4b6c7d8-x9fk2 -n production -o wide

# Read the previous container's logs (critical for CrashLoopBackOff).
kubectl logs api-server-5d4b6c7d8-x9fk2 -n production -c api --previous

# Read lastState (exit code, reason).
kubectl get pod api-server-5d4b6c7d8-x9fk2 -n production \
  -o jsonpath='{.status.containerStatuses[0].lastState}'

# Confirm the env var is missing.
kubectl get pod api-server-5d4b6c7d8-x9fk2 -n production \
  -o jsonpath='{.spec.containers[0].env}'

# Patch and verify.
kubectl set env deployment/api-server -n production \
  DB_HOST=postgres.production.svc.cluster.local
kubectl rollout status deployment/api-server -n production
```

The single-line trace (`KeyError: 'DB_HOST'`) plus the env-var audit
(`DB_HOST` absent from `.spec.containers[0].env`) confirms the
diagnosis without needing Prometheus or AWS-side queries.
