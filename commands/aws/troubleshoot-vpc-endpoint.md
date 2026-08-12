---
description: Diagnose Amazon VPC endpoint policy and connectivity failures (interface endpoint PrivateLink timeouts, Gateway endpoint S3/DynamoDB routing, endpoint policy access denied, DNS resolution, cross-account access). Emits a ROOT_CAUSE_IDENTIFIED diagnosis with remediation commands.
nl_triggers:
  - "vpc endpoint connection failure"
  - "troubleshoot vpc endpoint"
  - "endpoint connection timeout"
  - "privatelink timeout"
  - "endpoint policy denied"
  - "endpoint access denied"
  - "gateway endpoint route table"
  - "endpoint dns resolution"
  - "s3 endpoint not working"
  - "dynamodb endpoint routing"
  - "cross-account endpoint"
  - "nlb endpoint service"
  - "endpoint security group"
  - "vpc endpoint troubleshoot"
  - "privatelink connection failure"
routes_to: vpc-endpoint-policy-troubleshooter
---

# /aws:troubleshoot-vpc-endpoint

Activate the `vpc-endpoint-policy-troubleshooter` skill and diagnose a
VPC endpoint policy or connectivity failure with methodical root-cause
analysis.

## What it does

The skill walks the diagnostic layers and emits a ROOT_CAUSE_IDENTIFIED
diagnosis:

1. Security group (interface endpoint ENI inbound on service port)
2. Endpoint policy (separate IAM layer evaluated AFTER IAM policy)
3. DNS resolution (private DNS enabled, PHZ associated)
4. Route table (Gateway endpoint S3/DynamoDB)
5. Cross-account endpoint access (resource policy + IAM)
6. Endpoint service health (NLB-backed target health)
7. Connection timeout classification (SG vs service health)
8. Endpoint policy JSON syntax validation
9. PrivateLink endpoint service availability

## When to use

- You need to troubleshoot a VPC endpoint connection timeout.
- Clients are getting HTTP 403 Access Denied from an endpoint.
- S3 or DynamoDB traffic is not using the Gateway endpoint.
- The endpoint DNS name resolves to the wrong IP.
- Cross-account PrivateLink access is failing.
- An NLB-backed endpoint service has unhealthy targets.
- The endpoint policy needs syntax validation.

## When NOT to use

- **VPC peering connectivity** — use VPC peering troubleshoot skills.
- **Transit Gateway routing** — use Transit Gateway skills.
- **VPN / Direct Connect** — use VPN/DX-specific skills.
- **Endpoint creation or provisioning** — use endpoint deploy skills.

## How to invoke

### Slash command

```
/aws:troubleshoot-vpc-endpoint
```

Then provide: endpoint ID, endpoint type (interface or gateway),
service name, security group details, endpoint policy, DNS
configuration, error symptom (timeout, 403, or NXDOMAIN), and
client subnet CIDR.

### Natural language

Any of these routes to the same skill:

- "clients in subnet 10.0.2.0/24 get connection timeout on endpoint"
- "endpoint vpce-xxx is returning 403 access denied"
- "S3 traffic is going through NAT instead of the gateway endpoint"
- "the endpoint DNS name is resolving to a public IP"
- "cross-account PrivateLink connection is failing"

### CLI routing

```bash
node cli/bin/cli.js route "troubleshoot vpc endpoint connection"
```

## Pipeline integration

This skill operates in **Phase 1 (Diagnose)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to troubleshoot VPC
endpoint failures. The output diagnosis feeds into remediation
pipelines and downstream audit skills.

## Example

```
You: /aws:troubleshoot-vpc-endpoint

     Clients in subnet 10.0.2.0/24 are getting connection timeouts
     when accessing SSM via the interface endpoint vpce-aaa111222.
     The endpoint SG sg-vpce123 allows 443 from 10.0.0.0/16 and
     10.0.1.0/24 only. Private DNS is enabled. Endpoint policy is
     default. Endpoint state is available.

Skill:
  VPC_ENDPOINT: vpce-aaa111222 (Interface — com.amazonaws.us-east-1.ssm)
  VERDICT: ROOT_CAUSE_IDENTIFIED
  DIAGNOSIS:
    ROOT CAUSE: SG sg-vpce123 missing inbound 443 from 10.0.2.0/24
    FAILURE LAYER: Security Group
  EVIDENCE:
    [✗] Security group: MISSING inbound for 10.0.2.0/24
    [✓] Endpoint policy: default (full access)
    [✓] DNS: private DNS enabled
    [✓] Endpoint state: available
  REMEDIATION_COMMANDS:
    aws ec2 authorize-security-group-ingress --group-id sg-vpce123 --protocol tcp --port 443 --cidr 10.0.2.0/24 --region us-east-1
```

## References

- Skill definition: `skills/vpc-endpoint-policy-troubleshooter/SKILL.md`
- Endpoint policy and SG guide: `skills/vpc-endpoint-policy-troubleshooter/references/endpoint-policy-and-sg.md`
- Gateway endpoint and DNS guide: `skills/vpc-endpoint-policy-troubleshooter/references/gateway-endpoint-and-dns.md`
- Eval suite: `skills/vpc-endpoint-policy-troubleshooter/evals/evals.json`
