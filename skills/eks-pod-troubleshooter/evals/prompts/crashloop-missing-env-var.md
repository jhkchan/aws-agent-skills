# Eval prompt: crashloop-missing-env-var

Diagnose the following EKS pod failure. Walk the CrashLoopBackOff
diagnostic tree and emit the standard VERDICT block (INCIDENT, VERDICT,
ROOT_CAUSE, EVIDENCE, ROOT_CAUSE_CATALOG, REMEDIATION).

## Scenario

A Kubernetes pod on an EKS cluster is in `CrashLoopBackOff`. Namespace:
`production`. Pod: `api-server-5d4b6c7d8-x9fk2`. Node:
`ip-10-0-3-42.ec2.internal`.

## Known facts

- `kubectl get pod api-server-5d4b6c7d8-x9fk2 -n production -o wide`
  shows: STATUS=`CrashLoopBackOff`, RESTARTS=14, climbing.
- `kubectl describe pod` shows:
  - `Containers: api: State: Waiting (CrashLoopBackOff)`
  - `Last State: Terminated, Reason: Error, Exit Code: 1, Started
    10:42:11Z, Finished 10:42:12Z` (~0.8s apart)
- `kubectl logs api-server-5d4b6c7d8-x9fk2 -n production -c api
  --previous` shows:
  ```
  Traceback (most recent call last):
    File "/app/main.py", line 12, in <module>
      db_host = os.environ["DB_HOST"]
    File "/usr/lib/python3.11/os.py", line 680, in __getitem__
      raise KeyError(key) from None
  KeyError: 'DB_HOST'
  ```
- `kubectl get pod -o jsonpath='{.spec.containers[0].env}'` returns:
  ```
  [{"name":"APP_PORT","value":"8080"},{"name":"LOG_LEVEL","value":"info"}]
  ```
  (No `DB_HOST` entry present.)

## Symptom

The pod transitions from `Running` to `CrashLoopBackOff` repeatedly
within ~1 second of each container start.
