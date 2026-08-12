# GuardDuty Finding Types and Remediation Actions Reference

Supplementary reference for the GuardDuty Finding Automator skill. Use
when selecting a remediation action for a specific finding type,
designing a Lambda remediation function, or mapping a finding family
to a severity-based response tier.

## Finding type → remediation action matrix

### EC2 finding family

| Finding type | Default severity | Auto-action | Lambda function | Notes |
|---|---|---|---|---|
| `UnauthorizedAccess:EC2/SSHBruteForce` | 6.0-8.0 | Isolate EC2 (High) / Notify (Medium) | `gd-isolate-ec2` | Check for authorized scanner before isolating |
| `UnauthorizedAccess:EC2/RDPBruteForce` | 6.0-8.0 | Isolate EC2 (High) / Notify (Medium) | `gd-isolate-ec2` | Same as SSH; check scanner |
| `UnauthorizedAccess:EC2/InstanceCredentialExfiltration` | 7.0-9.0 | Isolate EC2 + revoke IAM keys | `gd-isolate-ec2` + `gd-revoke-iam-keys` | AWS credentials used from external IP |
| `Backdoor:EC2/BackdoorAtTask` | 8.0-9.0 | Isolate EC2 + snapshot | `gd-isolate-ec2` + `gd-snapshot-ebs` | C2 callback detected |
| `Backdoor:EC2/DriveThroughSource` | 7.0-8.0 | Isolate EC2 + snapshot | `gd-isolate-ec2` + `gd-snapshot-ebs` | Known malicious domain callback |
| `CryptoCurrency:EC2/BitcoinTool` | 9.0 | Isolate EC2 + snapshot immediately | `gd-isolate-ec2` + `gd-snapshot-ebs` | Revoke IAM keys unconditionally |
| `CryptoCurrency:EC2/CryptoDomain` | 8.0-9.0 | Isolate EC2 + snapshot | Same | Connection to crypto mining pool |
| `Trojan:EC2/Trojan` | 7.0-8.0 | Isolate EC2 + Malware Protection scan | `gd-isolate-ec2` + `gd-malware-scan` | Wait for scan before cleanup |
| `Recon:EC2/PortProbe` | 1.0-3.0 | Log only (trend analysis) | N/A | Suppress authorized scanner |
| `Recon:EC2/PortProbeUnprotectedPort` | 2.0-4.0 | Log only (trend analysis) | N/A | Suppress authorized scanner |
| `Impact:EC2/AbusedDomain` | 5.0-7.0 | Notify + isolate (if High) | `gd-isolate-ec2` (conditional) | Check if domain is SaaS allowlist |

### IAM finding family

| Finding type | Default severity | Auto-action | Lambda function | Notes |
|---|---|---|---|---|
| `Persistence:IAMUser/BackdoorUser` | 8.0 | Revoke all keys + DenyAll policy | `gd-revoke-iam-keys` | Attacker-created user |
| `Persistence:IAMUser/AccessKeyCreated` | 7.0-8.0 | Revoke the specific key | `gd-revoke-iam-keys` | Check `AccessKeyLastUsed` (unless Critical) |
| `Policy:IAMUser/RootAccess` | 7.0 | Notify + CloudTrail correlate | `gd-notify-only` | Root credential anomaly — never auto-revoke root |
| `Policy:IAMUser/AdminAccess` | 6.0-7.0 | Notify + CloudTrail correlate | `gd-notify-only` | Check if intentional (break-glass) |
| `Recon:IAMUser/UserPermissions` | 2.0-4.0 | Log only | N/A | Permission enumeration |
| `CredentialAccess:IAMUser/AnomalousBehavior` | 6.0-8.0 | Notify (High → revoke) | Conditional | ML-based — verify before action |

### S3 / Exfiltration family

| Finding type | Default severity | Auto-action | Lambda function | Notes |
|---|---|---|---|---|
| `Exfiltration:S3/ObjectExfiltration` | 8.0-9.0 | Revoke IAM keys + notify | `gd-revoke-iam-keys` | Large data egress to external account |
| `Exfiltration:EC2/NetPort` | 7.0-8.0 | Isolate EC2 + snapshot | `gd-isolate-ec2` | Abnormal data transfer |
| `UnauthorizedAccess:S3/MaliciousIPCaller` | 6.0-8.0 | WAF block IP + notify | `gd-waf-block-ip` | Access from known malicious IP |
| `Impact:S3/MaliciousIPCaller` | 6.0-8.0 | WAF block IP + notify | `gd-waf-block-ip` | Delete/modify from malicious IP |

### Kubernetes (EKS) family

| Finding type | Default severity | Auto-action | Lambda function | Notes |
|---|---|---|---|---|
| `CredentialAccess:EKS/MaliciousApiCall` | 7.0-8.0 | Revoke K8s token + notify | `gd-eks-revoke-token` | Uses EKS API, not EC2 SG swap |
| `Persistence:EKS/MaliciousApiCall` | 6.0-8.0 | Notify + isolate pod | `gd-eks-isolate-pod` | Pod eviction via Kubernetes API |
| `Recon:EKS/SuccessfulAnonymousAccess` | 5.0-7.0 | Notify | `gd-notify-only` | Anonymous API access succeeded |

### Runtime (ECS/EKS/EC2) family

| Finding type | Default severity | Auto-action | Lambda function | Notes |
|---|---|---|---|---|
| `Runtime/ECS/CryptoDomain` | 8.0-9.0 | Stop ECS task + notify | `gd-ecs-stop-task` | Container-level crypto mining |
| `Runtime/EKS/CryptoDomain` | 8.0-9.0 | Evict pod + notify | `gd-eks-isolate-pod` | Same for EKS |
| `Runtime/EC2/SSH` | 7.0-8.0 | Isolate host EC2 | `gd-isolate-ec2` | SSH into running container |
| `Runtime/EC2/ReverseShell` | 8.0-9.0 | Isolate host + snapshot | `gd-isolate-ec2` + `gd-snapshot-ebs` | Reverse shell detected in process |

## Severity tier decision table

| Severity range | Label | Auto-action | Notification | When to escalate to auto |
|---|---|---|---|---|
| 9.0-10.0 | Critical | Immediate containment (isolate + revoke + snapshot) | SNS + Page on-call | Always (instance is compromised) |
| 7.0-8.9 | High | Conditional containment (isolate EC2, revoke with last-used check) | SNS + Email security | After pre-prod validation (3-phase rule) |
| 4.0-6.9 | Medium | No auto-action — notify only | SNS email | Never auto-contain; correlate via CloudTrail |
| 0.1-3.9 | Low | No action — log only | CloudWatch log | Never auto-contain; suppress known FPs |

## Finding ID deduplication pattern

GuardDuty updates finding IDs as new evidence arrives. The Lambda MUST
deduplicate to avoid re-remediation:

```python
import boto3
from datetime import datetime, timedelta

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('guardduty-processed-findings')

def is_duplicate(finding_id):
    """Check if finding was already processed within TTL window."""
    resp = table.get_item(Key={'finding_id': finding_id})
    return 'Item' in resp

def mark_processed(finding_id, action_taken):
    """Mark finding as processed with 7-day TTL."""
    table.put_item(Item={
        'finding_id': finding_id,
        'action': action_taken,
        'processed_at': datetime.utcnow().isoformat(),
        'ttl': int((datetime.utcnow() + timedelta(days=7)).timestamp())
    })
```

DynamoDB TTL configuration:
- **PK:** `finding_id` (string)
- **TTL attribute:** `ttl` (epoch seconds)
- **TTL duration:** 7 days (findings re-evaluated after TTL expiry)
- **Billing:** on-demand (spiky workload driven by finding volume)

## WAF IP set management

| Limit | Value | Mitigation |
|---|---|---|
| Max IPs per IP set | 10,000 | Use multiple IP sets or NACL-based blocking |
| Max IP sets per ACL | 200 | Rotate sets with TTL-based eviction |
| Update rate | 1 req/sec | Batch updates in Lambda (collect, then single update) |
| Propagation delay | 60-90 seconds | Do not block, then immediately verify — wait 90s |

Eviction policy Lambda (for high-volume IP blocking):

```python
def evict_oldest_if_full(ip_set_arn, max_entries=9500):
    """Remove oldest entries when IP set approaches limit."""
    current = wafv2.get_ip_set(IPSetArn=ip_set_arn)
    addresses = current['IPSet']['Addresses']
    if len(addresses) >= max_entries:
        # Remove oldest 500 entries (FIFO)
        addresses = addresses[500:]
    return addresses
```
