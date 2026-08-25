
<!-- Moved verbatim from SKILL.md (eks-nodegroup-troubleshooter) — progressive-disclosure restructure, lines 190-212 -->

## Pre-flight gather-info command set

```bash
# 1. Node group details (status, amiType, version, scalingConfig, health)
aws eks describe-nodegroup \
  --cluster-name <cluster> --nodegroup-name <ng> --output json

# 2. Cluster details (kubernetesVersion, vpcConfig)
aws eks describe-cluster --name <cluster> --output json

# 3. Node states and conditions
kubectl get nodes -o wide
kubectl describe node <node> | grep -A30 Conditions
kubectl describe node <node> | grep -A10 Allocatable

# 4. Pod states on affected nodes
kubectl get pods --all-namespaces --field-selector spec.nodeName=<node>

# 5. ASG activity (launch failures, capacity)
aws autoscaling describe-scaling-activities \
  --auto-scaling-group-name <asg-name> --max-records 5 --output json

# 6. Recent cluster events
kubectl get events --sort-by='.lastTimestamp' | tail -20
```

