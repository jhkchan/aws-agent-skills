# Eval: eks-pod-disruption

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — worker has SSM + kubeconfig, alarm OK

## Prompt

Build an FIS experiment "eks-pod-kill-api" in us-east-1. Use
SSM Run Command on EKS worker node i-0abc789 (tagged
fis-target=true, SSM agent Online, has EKS API permissions via
kubeconfig). Delete pods matching label "app=critical" in
namespace "api". Run kubectl via AWS-RunShellScript. Stop
condition: alarm "fis-stop-api-5xx" (OK state, role has
DescribeAlarms). budgetDuration 3 minutes.
