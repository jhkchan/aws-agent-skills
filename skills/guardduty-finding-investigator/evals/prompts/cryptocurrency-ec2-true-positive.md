# Eval prompt: cryptocurrency-ec2-true-positive

Diagnose the GuardDuty finding below. Walk the finding-type-driven
diagnostic tree and emit the standard diagnostic block (FINDING, VERDICT,
REASON, LAYER, SEVERITY, EVIDENCE, SUPPRESSION, REMEDIATION). The FINDING
line must reference the test-case id `cryptocurrency-ec2-true-positive`.

Symptom: GuardDuty finding a1b2c3d4 in detector 12ab34cd (us-east-1).
Type `CryptoCurrency:EC2/BitcoinTool.B!DNS`, severity 7.5 (High).
Resource: EC2 instance i-app-1 (Node.js API server in prod VPC).

```text
aws guardduty get-findings:
  service.action.dnsRequestAction.domain: "miningpool.example"
  resource.instanceDetails.instanceId: i-app-1
  service.additionalInfo.threatListName: "MiningDomains"

CloudWatch CPUUtilization on i-app-1 (last 90 min):
  Average 95.2%, Maximum 99.8%

VPC Flow Logs query (last 60 min):
  srcAddr=10.0.5.12 (i-app-1)  dstAddr=203.0.113.55  dstPort=3333
  sum(bytes) = 2.1 MB

Application dependency scan (package.json):
  no reference to "miningpool.example" or any mining library

Target SG sg-app: allows 0.0.0.0/0 on tcp/3333 (misconfigured
egress rule from a prior incident).
```

Emit the standard diagnostic block.
