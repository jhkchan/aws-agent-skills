# End-to-End Example: Client VPN Endpoint Deployment

A walkthrough showing how to use the `client-vpn-endpoint-deployer`
skill from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning a Client VPN endpoint with mutual TLS
authentication, split-tunnel, and a multi-rule authorization policy.
The endpoint needs:

- Client CIDR: 10.250.0.0/16
- Authentication: mutual TLS (ACM server certificate)
- Split-tunnel: enabled (with custom DNS for leak prevention)
- Target VPC: vpc-aaa11122 (10.0.0.0/16)
- Subnet association: subnet-aaa11122 (us-east-1a)
- Authorization rules: (1) data-team → 10.0.0.0/16, (2) all-staff → 0.0.0.0/0
- Connection logging: CloudWatch log group client-vpn-logs
- Transport: UDP on port 443

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-client-vpn-endpoint
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create a Client VPN endpoint with mutual TLS in us-east-1.
      Client CIDR 10.250.0.0/16. Split-tunnel with DNS server
      10.0.0.2. Associate subnet-aaa11122. Two authorization rules:
      data-team to 10.0.0.0/16 first, then all-staff to 0.0.0.0/0."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create a client vpn endpoint"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
CLIENT_VPN: cvpn-aaa11122bbbb3333 (10.250.0.0/16 → vpc-aaa11122)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Client CIDR: 10.250.0.0/16 (non-overlapping with 10.0.0.0/16)
  [✓] Authentication: mutual-TLS (ACM arn:aws:acm:us-east-1:123456789012:certificate/abc123)
  [✓] Authorization rules: 2 rules — first-match ordering verified (10.0.0.0/16 data-team first; 0.0.0.0/0 all-staff last)
  [✓] Target subnet association: subnet-aaa11122 in us-east-1a — available
  [✓] Route table: propagated (10.0.0.0/16) + static route to 172.16.0.0/16
  [✓] DNS servers: 10.0.0.2 (VPC DNS resolver — split-tunnel DNS leak prevented)
  [✓] Tunnel mode: split-tunnel
  [✓] Transport protocol: udp (port 443)
  [✓] Connection logging: enabled (CloudWatch client-vpn-logs)
  [✓] Security group (VPN ENI): sg-vpn-eni-dedicated — dedicated
  [✓] Self-service portal: enabled (https://self-service.clientvpn.amazonaws.com/...)
  [✓] Session duration: 8h
  [✓] Tags: Environment=production, Access=corporate
VERIFICATION_COMMANDS:
  aws ec2 describe-client-vpn-endpoints --client-vpn-endpoint-ids cvpn-aaa11122bbbb3333 --region us-east-1
  aws ec2 describe-client-vpn-target-networks --client-vpn-endpoint-ids cvpn-aaa11122bbbb3333 --region us-east-1
  aws ec2 describe-client-vpn-routes --client-vpn-endpoint-ids cvpn-aaa11122bbbb3333 --region us-east-1
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Create the Client VPN endpoint (mutual TLS, split-tunnel)
CVPN_ID=$(aws ec2 create-client-vpn-endpoint \
  --client-cidr-block 10.250.0.0/16 \
  --server-certificate-arn arn:aws:acm:us-east-1:123456789012:certificate/abc123 \
  --authentication-type certificate-mutual-auth \
  --dns-servers 10.0.0.2 \
  --transport-protocol udp \
  --vpn-port 443 \
  --split-tunnel \
  --connection-log-options Enabled=true,CloudwatchLogGroup=client-vpn-logs \
  --client-portal-enabled enabled \
  --query 'ClientVpnEndpointId' --output text --region us-east-1)

# Step 2: Create the CloudWatch log group (if not already present)
aws logs create-log-group --log-group-name client-vpn-logs --region us-east-1

# Step 3: Associate the target subnet
aws ec2 create-client-vpn-endpoint-target-network-association \
  --client-vpn-endpoint-id "$CVPN_ID" \
  --subnet-id subnet-aaa11122 \
  --region us-east-1

# Wait for association to become available before proceeding

# Step 4: Create authorization rule 1 — data-team to VPC CIDR (SPECIFIC FIRST)
aws ec2 authorize-client-vpn-ingress \
  --client-vpn-endpoint-id "$CVPN_ID" \
  --target-network-cidr 10.0.0.0/16 \
  --access-group-id sg-data-team \
  --description "Data team access to VPC" \
  --region us-east-1

# Step 5: Create authorization rule 2 — all-staff to everything (BROAD LAST)
aws ec2 authorize-client-vpn-ingress \
  --client-vpn-endpoint-id "$CVPN_ID" \
  --target-network-cidr 0.0.0.0/0 \
  --authorize-all-groups \
  --description "All staff full access" \
  --region us-east-1

# Step 6: Export the client configuration bundle
aws ec2 export-client-vpn-client-configuration \
  --client-vpn-endpoint-id "$CVPN_ID" \
  --region us-east-1 > client-config.ovpn
```

---

## Step 4 — Post-deployment verification

```bash
# Endpoint status — should be available
aws ec2 describe-client-vpn-endpoints \
  --client-vpn-endpoint-ids "$CVPN_ID" \
  --query 'ClientVpnEndpoints[0].Status' --region us-east-1

# Target subnet association — should be available
aws ec2 describe-client-vpn-target-networks \
  --client-vpn-endpoint-ids "$CVPN_ID" \
  --query 'ClientVpnTargetNetworks[*].{Subnet:TargetNetworkId,Status:Status.Code}' \
  --region us-east-1 --output table

# Authorization rules — verify ordering
aws ec2 describe-client-vpn-authorization-rules \
  --client-vpn-endpoint-id "$CVPN_ID" \
  --query 'AuthorizationRules[*].{CIDR:DestinationCidr,Group:GroupId,Desc:Description}' \
  --region us-east-1 --output table

# Routes — verify propagated + static
aws ec2 describe-client-vpn-routes \
  --client-vpn-endpoint-id "$CVPN_ID" \
  --query 'Routes[*].{CIDR:DestinationCidr,Type:Type,Target:TargetSubnet}' \
  --region us-east-1 --output table

# Check active connections
aws cloudwatch get-metric-statistics \
  --namespace AWS/ClientVPN \
  --metric-name ActiveConnections \
  --dimensions Name=Endpoint,Value="$CVPN_ID" \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 --statistics Sum --region us-east-1
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Authorization rules | Missing or single broad rule | Multi-rule with ordering verified | Rules are first-match-wins; broad rule shadows specific if ordered wrong |
| Split-tunnel DNS | No custom DNS servers | DnsServers=10.0.0.2 (VPC resolver) | Split-tunnel without custom DNS leaks VPC hostname resolution |
| Subnet association | Attempted concurrently | Sequential with wait | AWS processes associations sequentially; concurrency causes failures |
| Static route + auth rule | Route without auth rule | Both route and authorization rule | Route controls forwarding; auth rule controls access; both needed |
| Self-service portal | Not enabled | ClientPortalEnabled=enabled | Users need the portal URL for self-enrollment |
| Connection logging | Not enabled | Enabled with CloudWatch log group | Without logging, authentication failures are invisible |

---

## Related artifacts

- **Skill definition:** `skills/client-vpn-endpoint-deployer/SKILL.md`
- **Authentication and authorization guide:** `skills/client-vpn-endpoint-deployer/references/auth-and-authorization.md`
- **Routes, DNS, and tunnel mode guide:** `skills/client-vpn-endpoint-deployer/references/routes-dns-and-tunnel.md`
- **Slash command:** `commands/aws/deploy-client-vpn-endpoint.md`
- **Eval suite:** `skills/client-vpn-endpoint-deployer/evals/evals.json`
- **Legacy test cases:** `skills/client-vpn-endpoint-deployer/eval/test-cases.yaml`
