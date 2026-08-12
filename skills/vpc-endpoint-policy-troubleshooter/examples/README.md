# End-to-End Example: VPC Endpoint Policy Troubleshooting

A walkthrough showing how to use the `vpc-endpoint-policy-troubleshooter`
skill from invocation through diagnosis and remediation. Mirrors the
structured-eval pattern of shipping a concrete worked example per skill.

---

## Scenario

You are troubleshooting an interface VPC endpoint for the SSM service
where clients in a specific subnet get connection timeouts. The
diagnosis requires identifying the security group layer as the root
cause.

- Endpoint: vpce-aaa111222 (Interface, com.amazonaws.us-east-1.ssm)
- Client subnet: 10.0.2.0/24
- Endpoint SG: sg-vpce123 (allows 443 from 10.0.0.0/16, 10.0.1.0/24)
- Private DNS: enabled
- Endpoint policy: default (full access)
- Endpoint state: available

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:troubleshoot-vpc-endpoint
```

Then paste the symptoms.

### Option B: Natural language

```
You: "Clients in subnet 10.0.2.0/24 are getting connection timeouts
      when accessing SSM via the interface endpoint vpce-aaa111222.
      The endpoint SG sg-vpce123 allows 443 from 10.0.0.0/16 and
      10.0.1.0/24 only."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "troubleshoot vpc endpoint connection timeout"
```

---

## Step 2 — Skill produces the ROOT_CAUSE_IDENTIFIED diagnosis

```text
VPC_ENDPOINT: vpce-aaa111222 (Interface — com.amazonaws.us-east-1.ssm)
VERDICT: ROOT_CAUSE_IDENTIFIED
DIAGNOSIS:
  ROOT CAUSE: Security group sg-vpce123 does not allow inbound on port 443 from client subnet 10.0.2.0/24
  FAILURE LAYER: Security Group
  IMPACT: Clients in subnet 10.0.2.0/24 get connection timeout when accessing SSM via the endpoint
EVIDENCE:
  [✗] Security group (interface): sg-vpce123 allows inbound on port 443 from 10.0.0.0/16 and 10.0.1.0/24 only; MISSING inbound rule for 10.0.2.0/24
  [✓] Endpoint policy: default (full access)
  [✓] DNS resolution: private DNS enabled
  [N/A] Route table (gateway): not applicable (interface endpoint)
  [N/A] Cross-account: not applicable (same account)
  [✓] Endpoint service health: AWS service (SSM) — healthy
  [✓] Endpoint state: available
  [✓] Policy JSON syntax: valid (default policy)
REMEDIATION_COMMANDS:
  aws ec2 authorize-security-group-ingress --group-id sg-vpce123 --protocol tcp --port 443 --cidr 10.0.2.0/24 --region us-east-1
  # Verify: from a client in 10.0.2.0/24, run: telnet <eni-private-ip> 443
```

---

## Step 3 — Remediation commands

```bash
# Step 1: Add the missing inbound rule
aws ec2 authorize-security-group-ingress \
  --group-id sg-vpce123 \
  --protocol tcp \
  --port 443 \
  --cidr 10.0.2.0/24 \
  --region us-east-1

# Step 2: Verify the rule was added
aws ec2 describe-security-groups \
  --group-ids sg-vpce123 \
  --query 'SecurityGroups[0].IpPermissions[*].{Protocol:IpProtocol,From:FromPort,To:ToPort,Sources:IpRanges[*].CidrIp}' \
  --output table --region us-east-1

# Step 3: Verify connectivity from a client in 10.0.2.0/24
# From the client instance:
telnet <endpoint-eni-private-ip> 443
# Expected: Connected (no longer times out)
```

---

## Step 4 — Post-remediation verification

```bash
# Get the endpoint ENI IP
ENI_IP=$(aws ec2 describe-vpc-endpoints \
  --vpc-endpoint-ids vpce-aaa111222 \
  --query 'VpcEndpoints[0].NetworkInterfaceIds' --output text --region us-east-1 | \
  xargs -I {} aws ec2 describe-network-interfaces \
    --network-interface-ids {} \
    --query 'NetworkInterfaces[0].PrivateIpAddress' --output text --region us-east-1)

# From a client in subnet 10.0.2.0/24:
# Test TCP connectivity
nc -zv "$ENI_IP" 443
# Expected: Connection succeeded

# Test SSM via the endpoint
aws ssm get-parameter --name "/config/test" --region us-east-1
# Expected: parameter value returned (no timeout)
```

---

## What the skill catches that a naive diagnosis misses

| Layer | Naive diagnosis | Skill output | Why the skill is right |
|---|---|---|---|
| Security group | Checks client SG only | Checks the endpoint ENI's own SG | Endpoint SG must allow inbound from client subnet; client SG only controls outbound |
| Endpoint policy | Checks IAM only | Checks endpoint policy as separate IAM layer | Endpoint policy is evaluated AFTER IAM; both must allow |
| DNS | Checks resolv.conf | Checks private DNS flag on endpoint | Private DNS must be enabled for AWS services to resolve to endpoint IP |
| Route table | Checks all endpoints | Distinguishes interface vs gateway endpoint | Only gateway endpoints use route tables; interface endpoints use ENI IPs |
| Cross-account | Checks IAM only | Checks provider's endpoint service resource policy | Three-layer model: consumer IAM + consumer endpoint policy + provider resource policy |
| Error classification | Guesses at the cause | Classifies by symptom (timeout=SG, 403=policy, NXDOMAIN=DNS) | Different symptoms point to different layers |

---

## Related artifacts

- **Skill definition:** `skills/vpc-endpoint-policy-troubleshooter/SKILL.md`
- **Endpoint policy and SG guide:** `skills/vpc-endpoint-policy-troubleshooter/references/endpoint-policy-and-sg.md`
- **Gateway endpoint and DNS guide:** `skills/vpc-endpoint-policy-troubleshooter/references/gateway-endpoint-and-dns.md`
- **Slash command:** `commands/aws/troubleshoot-vpc-endpoint.md`
- **Eval suite:** `skills/vpc-endpoint-policy-troubleshooter/evals/evals.json`
- **Legacy test cases:** `skills/vpc-endpoint-policy-troubleshooter/eval/test-cases.yaml`
