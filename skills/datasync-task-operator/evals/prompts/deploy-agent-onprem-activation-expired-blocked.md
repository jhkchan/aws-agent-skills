# Eval prompt: deploy-agent-onprem-activation-expired-blocked

Plan the following DataSync on-prem agent deployment and emit the
standard VERDICT block.

Operation: deploy-agent
Deployment: on-prem VM (.ova on ESXi 7.0)
Source: nfs://10.0.10.20/vol/data
Destination: s3://prod-migration-archive-2026 (us-east-1)

```json
{
  "Deployment": {
    "Hypervisor": "ESXi 7.0",
    "ImageFormat": "ova",
    "AgentVmPrivateIp": "10.0.30.40",
    "LocalConsoleUrl": "http://10.0.30.40"
  },
  "ActivationKey": {
    "FetchedAt": "2026-08-08T10:00:00Z",
    "AgeHours": 48
  },
  "Network": {
    "AgentOutboundHttps443": "reachable to datasync.us-east-1.amazonaws.com",
    "SourceReachabilityFromAgentSubnet": "subnet-0abc (10.0.10.0/24) can reach 10.0.10.20 on TCP 2049",
    "SecurityGroup": "sg-001 allows outbound TCP 2049 to 10.0.10.20"
  },
  "IntendedCli": "aws datasync create-agent --activation-key AAAAAAAAAA --agent-name onprem-agent-nfs"
}
```
