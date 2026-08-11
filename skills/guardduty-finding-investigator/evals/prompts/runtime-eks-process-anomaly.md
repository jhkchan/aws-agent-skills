# Eval prompt: runtime-eks-process-anomaly

Diagnose the GuardDuty finding below. Walk the finding-type-driven
diagnostic tree and emit the standard diagnostic block (FINDING, VERDICT,
REASON, LAYER, SEVERITY, EVIDENCE, SUPPRESSION, REMEDIATION). The FINDING
line must reference the test-case id `runtime-eks-process-anomaly`.

Symptom: GuardDuty finding m3n4o5p6 in detector 12ab34cd (us-east-1).
Type `Runtime:EKS/ProcessA`, severity 7.5 (High). Resource: EKS cluster
prod-eks, container billing-api in namespace payments.

```text
aws guardduty list-features:
  EKS Protection: ENABLED
  Runtime Monitoring: ENABLED (EKS coverage)

aws guardduty get-findings:
  service.runtimeData.processDetails:
    name: "xmrig"
    path: "/tmp/xmrig"
    pid: 7
    user: "node"
    cmdline: "./xmrig -o pool.miningpool.example:3333 -u wallet"
    parentProcessName: "node"  (container entrypoint — shimming)
    parentUser: "node"
  service.runtimeData.networkConnection:
    direction: "OUTBOUND"
    local: "10.50.3.12:54321"
    remote: "203.0.113.77:3333"
  resource.eksClusterDetails.name: "prod-eks"
  resource.containerDetails.name: "billing-api"
  resource.containerDetails.image: "111111111111.dkr.ecr.us-east-1.amazonaws.com/billing-api:v2.3.1"

CloudWatch Container Insights on billing-api pod:
  CPU usage 99% of pod limit (last 30 min)
  Network out: 4.2 MB sustained (vs baseline 200 KB/min)

Container image scan (Inspector):
  no known CVEs; image was last built 2 hours ago from main branch

billing-api source code review:
  no xmrig binary in the repo or the Dockerfile
```

Emit the standard diagnostic block.
