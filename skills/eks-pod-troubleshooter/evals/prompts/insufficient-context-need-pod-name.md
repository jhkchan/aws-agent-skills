# Eval prompt: insufficient-context-need-pod-name

Diagnose the following EKS pod failure report. Determine whether the
provided context is sufficient to walk the decision tree, or emit
NEED_MORE_INFO with the specific missing inputs.

## Scenario

A user reports that some of their pods on an EKS cluster are failing.
They provide only the cluster name.

## Known facts

- Cluster name: `prod-cluster`.
- The user says: "some of my pods on EKS keep failing".
- No pod names provided.
- No namespace provided.
- No `kubectl get pods` output provided.
- No `kubectl describe pod` Events provided.
- No `kubectl logs` output provided.
- No exit codes, restart counts, or statuses provided.
- No Deployment / ReplicaSet / label selector provided.

## Symptom

Vague report of pods failing. The diagnostic walk cannot begin without
identifying the specific failing pod.
