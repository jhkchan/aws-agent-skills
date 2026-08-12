# Baseline (no-skill) response: vpa-hpa-conflict

This file captures what a generic assistant produces WITHOUT the
eks-autoscaling-automator skill loaded.

---

You can set up both HPA and VPA for your data-processor deployment.
HPA will scale the number of replicas based on CPU utilization, and
VPA will automatically adjust the CPU and memory requests.

For HPA:

```
kubectl autoscale deployment data-processor --cpu-percent=70 --min=3 --max=20
```

For VPA, install the VPA component and create a VPA resource:

```
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: data-processor-vpa
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: data-processor
  updatePolicy:
    updateMode: Auto
```

This should give you both horizontal and vertical scaling. VPA will
automatically adjust the resource requests and HPA will scale the
replicas based on the adjusted utilization.
