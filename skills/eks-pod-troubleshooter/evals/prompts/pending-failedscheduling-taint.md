# Eval prompt: pending-failedscheduling-taint

Diagnose the following EKS pod failure. Walk the Pending /
FailedScheduling diagnostic tree and emit the standard VERDICT block
(INCIDENT, VERDICT, ROOT_CAUSE, EVIDENCE, ROOT_CAUSE_CATALOG,
REMEDIATION).

## Scenario

A Kubernetes pod on an EKS cluster is stuck `Pending`. Namespace:
`data-pipeline`. Pod: `etl-job-batch-x86-cron-28093000-xyz12`.

## Known facts

- `kubectl get pod etl-job-batch-x86-cron-28093000-xyz12 -n
  data-pipeline -o wide` shows: STATUS=`Pending`.
- `kubectl describe pod etl-job-batch-x86-cron-28093000-xyz12 -n
  data-pipeline` Events:
  ```
  Warning  FailedScheduling  default-scheduler
  0/3 nodes are available: 3 node(s) had taints that the pod
  didn't tolerate.
  ```
- `kubectl get nodes -o custom-columns=NAME:.metadata.name,TAINTS:.spec.taints`:
  ```
  NAME                            TAINTS
  ip-10-0-1-10.ec2.internal       [map[effect:NoSchedule key:dedicated value:batch]]
  ip-10-0-2-20.ec2.internal       [map[effect:NoSchedule key:dedicated value:batch]]
  ip-10-0-3-30.ec2.internal       [map[effect:NoSchedule key:dedicated value:batch]]
  ```
- `kubectl get pod etl-job-batch-x86-cron-28093000-xyz12 -n
  data-pipeline -o jsonpath='{.spec.tolerations}'` returns empty (no
  tolerations configured).
- `kubectl top nodes` shows CPU < 30% and memory < 40% on all three
  nodes — plenty of capacity.

## Symptom

The pod has been `Pending` for 5+ minutes. The scheduler cannot place
it anywhere.
