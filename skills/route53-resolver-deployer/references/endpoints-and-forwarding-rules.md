# Resolver Endpoints & Forwarding Rules Reference

Load this reference when planning or executing any Route 53 Resolver
endpoint or forwarding rule deployment. The procedures below are the
canonical endpoint configurations, rule patterns, and verification
sequences for each Resolver archetype.

## Decision tree — which endpoint direction

| Scenario | Use | Why |
|---|---|---|
| On-prem needs to resolve Route 53 Private Hosted Zones | **INBOUND endpoint** | On-prem DNS forwarder points to inbound IPs |
| VPC needs to resolve on-prem private domains | **OUTBOUND endpoint + FORWARD rule** | VPC queries Resolver; Resolver forwards to on-prem |
| Both directions (enterprise hybrid) | **BOTH endpoints** | Most common enterprise pattern |
| Pure cloud, no on-prem | **Neither endpoint** | Resolver answers from PHZ + public zones |
| Multi-account hybrid DNS | **OUTBOUND in hub + RAM share** | Share rules via Resource Access Manager |

## Inbound endpoint procedure

**When to use:** on-prem DNS servers need to resolve Route 53 Private
Hosted Zone records (e.g., internal AWS service names).

**Pre-checks:**
1. At least 2 subnets in 2 distinct AZs in the target VPC.
2. Security group allows UDP/TCP 53 ingress from the on-prem/peered CIDR.
3. VPC `enableDnsSupport: true`, `enableDnsHostnames: true`.
4. Connectivity from on-prem to the VPC subnets (Direct Connect, VPN, or TGW).

**CLI structure:**
```bash
aws route53resolver create-resolver-endpoint \
  --creator-request-id inbound-$(date +%s) \
  --name "prod-inbound" \
  --security-group-ids sg-0abc123 \
  --direction INBOUND \
  --ip-addresses '[
    {"SubnetId":"subnet-aaa","Ip":"10.0.1.10"},
    {"SubnetId":"subnet-bbb","Ip":"10.0.2.10"}
  ]'
```

**Post-deploy: on-prem forwarder config**

The on-prem DNS server (BIND, Windows AD DNS, Infoblox) must be
configured with a conditional forwarder or stub zone pointing to the
inbound endpoint IPs returned by `get-resolver-endpoint`. Example BIND
config:

```
zone "internal.aws." {
    type forward;
    forwarders { 10.0.1.10; 10.0.2.10; };
};
```

**Common failure modes:**
- "On-prem cannot resolve" — check the on-prem DNS forwarder points to
  the inbound endpoint IPs (not the VPC CIDR or the VPC DNS server IP+2).
- "Queries from on-prem are blocked" — check the security group ingress
  allows UDP/TCP 53 from the on-prem source CIDR.
- "Intermittent resolution" — one of the two IPs is unreachable (single
  AZ failure). Confirm both IPs are routable from on-prem.

## Outbound endpoint procedure

**When to use:** VPC EC2/Lambda/RDS instances need to resolve on-prem
private domains (e.g., `corp.example.local.`).

**Pre-checks:**
1. At least 2 subnets in 2 distinct AZs.
2. Security group allows UDP/TCP 53 egress to the on-prem DNS server IPs.
3. On-prem DNS servers reachable from the VPC subnets (route table check).
4. On-prem firewall allows UDP/TCP 53 from the outbound endpoint IPs.

**CLI structure:**
```bash
aws route53resolver create-resolver-endpoint \
  --creator-request-id outbound-$(date +%s) \
  --name "prod-outbound" \
  --security-group-ids sg-0def456 \
  --direction OUTBOUND \
  --ip-addresses '[
    {"SubnetId":"subnet-aaa"},
    {"SubnetId":"subnet-bbb"}
  ]'
```

**Note:** For outbound endpoints, you can let AWS auto-assign IPs from
the subnet (omit `Ip`) or specify them explicitly. Auto-assign is
preferred — AWS picks available IPs from the subnet CIDR.

## Forwarding rule procedure

**When to use:** after the outbound endpoint is created, define which
domains get forwarded to on-prem DNS servers.

**CLI structure:**
```bash
aws route53resolver create-resolver-rule \
  --creator-request-id rule-$(date +%s) \
  --name "forward-corp-local" \
  --rule-type FORWARD \
  --domain-name "corp.example.local." \
  --resolver-endpoint-id <outbound-endpoint-id> \
  --target-ips '[{"Ip":"10.99.1.5","Port":53},{"Ip":"10.99.2.5","Port":53}]'

aws route53resolver associate-resolver-rule \
  --resolver-rule-id <rule-id> \
  --vpc-id vpc-0abc123
```

**Domain matching rules:**
- Rules match by longest suffix. `corp.example.local.` matches
  `api.corp.example.local.` but not `corp.example.com.`.
- The trailing dot is significant. Omitting it may cause no-match.
- If two rules match, the one with the lower priority integer wins.
- The AWS-managed `.` (root) rule forwards all non-matched domains to
  Route 53 public resolvers. You cannot delete it.

**Cross-account rule sharing:**
```bash
# In the Resolver administrator account
aws route53resolver share-resolver-rule \
  --resolver-rule-id <rule-id> \
  --aws-account-id 222222222222

# Or share via AWS RAM to an OU
aws ram create-resource-share \
  --name "resolver-rules-share" \
  --resource-arns arn:aws:route53resolver:us-east-1:111111111111:resolver-rule/<rule-id>
```

## Rule association verification

```bash
# Check the rule is associated with the target VPC
aws route53resolver list-resolver-rule-associations \
  --resolver-rule-id <rule-id> \
  --query 'ResolverRuleAssociations[].[VPCId,Status,StatusMessage]'

# Check all rules associated with a VPC
aws route53resolver list-resolver-rule-associations \
  --filters Name=VPCId,Values=vpc-0abc123

# Test resolution from within the VPC
aws ssm send-command \
  --instance-id i-0abc123 \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=["dig @127.0.0.11 corp.example.local. +short"]'
```

## Endpoint IP address reference

| Endpoint type | IPs visible to | Source/dest for on-prem |
|---|---|---|
| INBOUND | On-prem DNS forwarders (destination) | On-prem queries → inbound IPs |
| OUTBOUND | On-prem DNS servers (source) | Outbound IPs → on-prem port 53 |

Always retrieve IPs via `get-resolver-endpoint` after creation:
```bash
aws route53resolver get-resolver-endpoint \
  --resolver-endpoint-id <id> \
  --query 'ResolverEndpoint.IpAddresses[].[Ip,SubnetId,AZ]' \
  --output table
```

## Common pitfalls

1. **Same-AZ subnets.** The API accepts 2 subnets in the same AZ but HA
   is lost. Always verify AZ diversity via `ec2:describe-subnets`.

2. **Security group on wrong VPC.** The security group must be in the
   same VPC as the subnets. Cross-VPC SG references are not supported.

3. **Forwarding rule without association.** A rule created but not
   associated with a VPC is inert. Always follow with
   `associate-resolver-rule`.

4. **Overlapping domain rules.** If `corp.example.local.` (priority 100)
   and `internal.corp.example.local.` (priority 50) both exist, the
   priority-50 rule wins for `internal.corp.example.local.` queries.
   Plan domain specificity and priority together.

5. **On-prem DNS server port.** Port 53 is default. Non-standard ports
   (e.g., 5353) are supported via `TargetIps[].Port` but the on-prem DNS
   server must be listening on that port.
