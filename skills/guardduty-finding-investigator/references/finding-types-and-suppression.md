# GuardDuty Finding-Type Catalogue and Suppression Patterns

Supplementary reference for the GuardDuty Finding Investigator skill.
Loaded on-demand when an investigation needs the full finding-type
catalogue, severity bands, or ready-to-use suppression-filter criteria
JSON.

## Severity bands

| Numeric range | Label | Typical SLA | Example families |
|---|---|---|---|
| `0.1` – `1.9` | Low | Triage within 72h | `Recon:*`, `UnauthorizedAccess:IAMUser/ConsoleLogin` (single event) |
| `2.0` – `6.9` | Medium | Triage within 24h | `UnauthorizedAccess:EC2/SSHBruteForce`, `Persistence:IAMUser/*`, `Policy:IAMUser/*` |
| `7.0` – `8.9` | High | Page on-call immediately | `CryptoCurrency:EC2/*`, `Backdoor:EC2/C&CActivity.B`, `Exfiltration:*`, `UnauthorizedAccess:IAMUser/Instance*` |

Severity is GuardDuty's confidence in the detection, NOT the operator's
confidence in the verdict. A Low finding can still warrant
ROOT_CAUSE_FOUND with CREDENTIAL_ABUSE if CloudTrail shows a suspicious
actor.

## Finding-type families

### Recon — reconnaissance

| Type | Action | Common FP | First probe |
|---|---|---|---|
| `Recon:EC2/PortProbe` | PORT_PROBE | Authorised scanner CIDR | `portProbeAction.remoteIpDetails.ipAddressV4` |
| `Recon:EC2/PortProbedPort` | PORT_PROBE | Misconfigured LB health check | Same as above |
| `Recon:IAMUser/PortProbe` | PORT_PROBE | AWS Config aggregator | Same as above + principalId |
| `Recon:IAMUser/UserPermissions` | AWS_API_CALL | Terraform plan / Access Analyzer | CloudTrail `ListBuckets`/`GetCallerIdentity` burst |
| `Recon:IAMUser/TorIPCaller` | AWS_API_CALL | Tor exit node legitimate use | `awsApiCallAction.remoteIpDetails` |

### UnauthorizedAccess — unauthorized access

| Type | Action | Common FP | First probe |
|---|---|---|---|
| `UnauthorizedAccess:IAMUser/ConsoleLogin` | AWS_API_CALL | User travelling, new SSO region | CloudTrail `ConsoleLogin`, `MFAUsed` |
| `UnauthorizedAccess:EC2/SSHBruteForce` | NETWORK_CONNECTION | Single misconfigured client | VPC Flow Logs `dstport=22` |
| `UnauthorizedAccess:EC2/RDPBruteForce` | NETWORK_CONNECTION | Same | VPC Flow Logs `dstport=3389` |
| `UnauthorizedAccess:Kubernetes/SuccessfulAnonymousAccess` | AWS_API_CALL | Intentional anonymous read | K8s audit log, `resource.kubernetesDetails` |

### Backdoor — backdoor / C&C

| Type | Action | Common FP | First probe |
|---|---|---|---|
| `Backdoor:EC2/Spambot` | NETWORK_CONNECTION | Misconfigured mail relay | VPC Flow Logs egress + `threatListName` |
| `Backdoor:EC2/C&CActivity.B` | NETWORK_CONNECTION | Domain re-used for CDN | `networkConnectionAction.remoteIpDetails` + `threatListName` |
| `Backdoor:EC2/DenialOfService.TcpFlood` | NETWORK_CONNECTION | Load test runner | VPC Flow Logs + corporate scanner list |

### CryptoCurrency — crypto mining

| Type | Action | Common FP | First probe |
|---|---|---|---|
| `CryptoCurrency:EC2/BitcoinTool.B` | NETWORK_CONNECTION | Authorised mining in isolated lab | VPC Flow Logs + CPUUtilization |
| `CryptoCurrency:EC2/BitcoinTool.B!DNS` | DNS_REQUEST | Domain re-used for CDN edge | DNS request domain + CPUUtilization |

### Persistence — anomalous IAM changes

| Type | Action | Common FP | First probe |
|---|---|---|---|
| `Persistence:IAMUser/UserCreation` | AWS_API_CALL | CI/CD deployment role | CloudTrail `CreateUser`, `userIdentity.arn` |
| `Persistence:IAMUser/IAMUserAnonymousAccess` | AWS_API_CALL | Intentional cross-account role | CloudTrail `AssumeRole` + trust policy |
| `Persistence:IAMUser/NetworkCredentialShare` | AWS_API_CALL | Shared CI key in plain text | CloudTrail source IP / user-agent |

### Policy — suspicious policy grants

| Type | Action | Common FP | First probe |
|---|---|---|---|
| `Policy:IAMUser/S3BucketAnonymousGranted` | AWS_API_CALL | Documented public website bucket | CloudTrail `PutBucketAcl` + ticket |
| `Policy:IAMUser/RootCredentialUsage` | AWS_API_CALL | Documented break-glass procedure | CloudTrail `userIdentity.sessionContext` |
| `Policy:IAMUser/AssumeRolePolicyChanged` | AWS_API_CALL | IaC pipeline update | CloudTrail `UpdateAssumeRolePolicy` |

### Exfiltration — data leaving the account

| Type | Action | Common FP | First probe |
|---|---|---|---|
| `Exfiltration:S3/AnomalousBehavior.S3` | AWS_API_CALL | Daily batch job to DW | CloudTrail data events GetObject burst |
| `Exfiltration:EC2/PortSweep` | NETWORK_CONNECTION | Internal network scanner | VPC Flow Logs egress + scanner CIDR |
| `Exfiltration:EC2/AnomalousTraffic.UnusualProtocols` | NETWORK_CONNECTION | New SaaS integration | VPC Flow Logs + ASN lookup |

### Runtime — Runtime Monitoring findings

| Type | Resource | Common FP | First probe |
|---|---|---|---|
| `Runtime:EC2/ProcessA` / `Runtime:EC2/ProcessA.Listener` | EC2 | APM sidecar (e.g., `collector`) | `service.runtimeData.processDetails` |
| `Runtime:ECS/ProcessA` | ECS task | CI runner named `agent` | `service.runtimeData` + `resource.containerDetails` |
| `Runtime:EKS/ProcessA` | EKS pod | Cron DaemonSet | `service.runtimeData` + `resource.eksClusterDetails` |

## Suppression filter criteria JSON

The `create-filter` CLI takes a JSON `finding-criteria` object. Each
criterion is a `Criterion` with `Eq` (equals) / `NotEquals` /
`GreaterThan` / `LessThan` over a finding field path.

### Authorised scanner (CIDR-based suppression)

```json
{
  "Criterion": {
    "type": { "Eq": ["Recon:EC2/PortProbe", "Recon:IAMUser/PortProbe"] },
    "service.action.portProbeAction.remoteIpDetails.ipAddressV4": {
      "Eq": ["198.51.100.10/32", "198.51.100.11/32"]
    }
  }
}
```

### AWS Config aggregator calling ListBuckets

```json
{
  "Criterion": {
    "type": { "Eq": ["Recon:IAMUser/UserPermissions"] },
    "service.action.awsApiCallAction.api": { "Eq": ["ListBuckets"] },
    "resource.accessKeyDetails.principalId": {
      "Pattern": ".*AWSServiceRoleForConfig.*"
    }
  }
}
```

### CI/CD deployment role IAM burst

```json
{
  "Criterion": {
    "type": {
      "Eq": ["Persistence:IAMUser/UserCreation", "Recon:IAMUser/UserPermissions"]
    },
    "resource.accessKeyDetails.principalId": {
      "Pattern": ".*deployment-role-prod.*"
    }
  }
}
```

### Documented public S3 bucket

```json
{
  "Criterion": {
    "type": { "Eq": ["Policy:IAMUser/S3BucketAnonymousGranted"] },
    "resource.s3BucketDetails.name": { "Eq": ["public-website-assets-prod"] }
  }
}
```

### Authorised daily S3 batch exfil pattern

```json
{
  "Criterion": {
    "type": { "Eq": ["Exfiltration:S3/AnomalousBehavior.S3"] },
    "resource.accessKeyDetails.principalId": {
      "Pattern": ".*dw-load-role.*"
    }
  }
}
```

## Trusted IP list vs suppression filter — when to use which

| Method | Effect | Use when |
|---|---|---|
| **Trusted IP list** (`create-ip-set`) | GuardDuty treats the CIDR as not-a-threat and continues behaviour tracking | The source IP is **known-benign** (scanner, corporate egress, SaaS posture manager). |
| **Archive filter** (`create-filter --action ARCHIVED`) | Matching findings auto-archive; no behavioural tracking | The finding is benign for a **non-IP reason** (API name, principalId, bucket name). |
| **Custom action** (`create-filter --action NOOP` + EventBridge) | Finding stays active, triggers a Lambda for custom handling | Investigative automation — auto-isolate, auto-scan, auto-notify SOC. |

## CloudTrail lookup-events gotchas

- `lookup-events` covers **management events only** for the last 90
  days. Data events (S3 GetObject, Lambda Invoke) require CloudTrail
  Lake or direct S3 access log queries.
- `lookup-events` is rate-limited at 1 QPS per account. For bursts,
  query CloudTrail Lake or the S3 trail bucket directly with Athena.
- `userIdentity.arn` is the **assumed role** for STS sessions, not the
  federated user. To find the human, follow
  `userIdentity.sessionContext.sessionIssuer.arn` +
  `sessionContext.attributes.mfaAuthenticated`.

## VPC Flow Logs query patterns

```text
# Find sustained outbound to a suspicious IP
fields @timestamp, srcAddr, dstAddr, dstPort, bytes
| filter (srcAddr="<instance-private-ip>" and dstAddr="<remote-ip>")
| sort @timestamp desc | limit 100

# Find mining-pool port traffic
fields srcAddr, dstAddr, dstPort, bytes
| filter srcAddr="<instance-private-ip>" and
  (dstPort=3333 or dstPort=4444 or dstPort=8888 or dstPort=14444)
| stats sum(bytes) by dstAddr

# Top outbound destinations by volume (exfil hunting)
fields srcAddr, dstAddr, bytes
| filter srcAddr="<instance-private-ip>"
| stats sum(bytes) as totalBytes by dstAddr
| sort totalBytes desc | limit 20
```
