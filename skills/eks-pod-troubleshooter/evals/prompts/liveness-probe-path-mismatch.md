# Eval prompt: liveness-probe-path-mismatch

Diagnose the following EKS pod failure. Walk the PROBE_FAILURE
diagnostic tree and emit the standard VERDICT block (INCIDENT, VERDICT,
ROOT_CAUSE, EVIDENCE, ROOT_CAUSE_CATALOG, REMEDIATION).

## Scenario

A Kubernetes pod on an EKS cluster is `Running` but its restart count
climbs every ~90 seconds. Namespace: `production`. Pod:
`api-deployment-6b7c8d9-x9mn2`. Node: `ip-10-0-1-10.ec2.internal`.

## Known facts

- `kubectl get pod api-deployment-6b7c8d9-x9mn2 -n production -o wide`
  shows: STATUS=`Running`, RESTARTS=6, climbing.
- `kubectl describe pod api-deployment-6b7c8d9-x9mn2 -n production`
  Events:
  ```
  Warning  Unhealthy  kubelet  Liveness probe failed:
  HTTP probe failed with statuscode: 404
  Warning  Killing     kubelet  Killing container with id
  containerd://api ... Container failed liveness probe
    (will restart)
  ```
- `kubectl get pod -o yaml | grep -A 10 livenessProbe`:
  ```yaml
  livenessProbe:
    httpGet:
      path: /healthz
      port: 8080
      scheme: HTTP
    initialDelaySeconds: 5
    periodSeconds: 10
    failureThreshold: 3
  ```
- `kubectl exec -n production api-deployment-6b7c8d9-x9mn2 -c api --
  curl -s -o /dev/null -w "%{http_code}\n"
  http://localhost:8080/healthz` returns `404`.
- `kubectl exec -n production api-deployment-6b7c8d9-x9mn2 -c api --
  curl -s -o /dev/null -w "%{http_code}\n"
  http://localhost:8080/api/health` returns `200`.
- CloudWatch Container Insights shows no application errors during the
  restart window — the app is healthy; the probe is wrong.

## Symptom

The pod cycles Running → killed (liveness fail) → Running. The
application is actually fine when the right path is probed.
