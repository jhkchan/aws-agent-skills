# End-to-end usage scenario: route53-resolver-deployer

A walkthrough showing the skill creating an outbound endpoint with a
forwarding rule, then adding DNS Firewall protection, and finally
blocking an attempt with a missing query-log destination policy. Each
path includes pre-checks, CONFIRM gate, and post-verification.

## Input (user prompt)

> Set up hybrid DNS for VPC vpc-0abc123 in us-east-1. Create an outbound
> Resolver endpoint so VPC instances can resolve corp.example.local. via
> on-prem DNS servers (10.99.1.5, 10.99.2.5). Then add a DNS Firewall
> rule using the AWS-managed malware domain list (BLOCK, NXDOMAIN) to
> the same VPC. Finally, enable query logging to CloudWatch.

```json
{
  "Operation": "create",
  "VpcId": "vpc-0abc123",
  "Region": "us-east-1",
  "Account": "111111111111",
  "OutboundEndpoint": {
    "Name": "prod-outbound",
    "SecurityGroupId": "sg-0def456",
    "IpAddresses": [
      {"SubnetId": "subnet-aaa"},
      {"SubnetId": "subnet-bbb"}
    ]
  },
  "ForwardingRule": {
    "Name": "forward-corp-local",
    "DomainName": "corp.example.local.",
    "TargetIps": [
      {"Ip": "10.99.1.5", "Port": 53},
      {"Ip": "10.99.2.5", "Port": 53}
    ]
  },
  "Firewall": {
    "GroupName": "prod-firewall-rules",
    "ManagedDomainListId": "rslvr-fdl-aws-managed-domains-malware",
    "Action": "BLOCK",
    "BlockResponse": "NXDOMAIN",
    "AssociationPriority": 1
  },
  "QueryLogging": {
    "Name": "prod-query-logs-cw",
    "Destination": "CloudWatch",
    "LogGroup": "/aws/route53resolver/prod"
  }
}
```

## Skill output — outbound endpoint + forwarding rule

```text
RESOLVER: prod-outbound
VERDICT: READY_TO_DEPLOY
TARGET: prod-outbound
PRE_CHECKS:
  - [PASS] Endpoint name unique (no collision)
  - [PASS] 2 subnets in 2 distinct AZs (us-east-1a, us-east-1b)
  - [PASS] Security group sg-0def456 egress UDP/TCP 53 to 10.99.1.5, 10.99.2.5
  - [PASS] VPC enableDnsSupport: true, enableDnsHostnames: true
  - [PASS] Forwarding rule domain corp.example.local. is valid
  - [PASS] Target IPs reachable (10.99.1.5, 10.99.2.5 port 53)
  - [PASS] IAM principal holds route53resolver:CreateResolverEndpoint
STEPS:
  1. CONFIRM: About to create-resolver-endpoint prod-outbound in account
     111111111111 region us-east-1. This will CREATE a new OUTBOUND
     endpoint with 2 IPs in 2 AZs. Proceed? (yes/no)
  2. aws route53resolver create-resolver-endpoint --name prod-outbound
     --security-group-ids sg-0def456 --direction OUTBOUND
     --ip-addresses '[{"SubnetId":"subnet-aaa"},{"SubnetId":"subnet-bbb"}]'
  3. aws route53resolver create-resolver-rule --name forward-corp-local
     --rule-type FORWARD --domain-name "corp.example.local."
     --resolver-endpoint-id <returned-id>
     --target-ips '[{"Ip":"10.99.1.5","Port":53},{"Ip":"10.99.2.5","Port":53}]'
  4. aws route53resolver associate-resolver-rule
     --resolver-rule-id <returned-rule-id> --vpc-id vpc-0abc123
POST_VERIFY:
  - (pending execution)
  - get-resolver-endpoint returns Status: OPERATIONAL
  - list-resolver-rule-associations returns vpc-0abc123 Status: COMPLETE
ENDPOINT_TYPE: OUTBOUND
SUBNETS: 2 subnets in 2 AZs
SECURITY_GROUPS: 1 (egress: 10.99.1.5/53, 10.99.2.5/53)
FORWARDING_RULES: 1 (corp.example.local.)
FIREWALL_GROUPS: 0 associated
QUERY_LOGS: NONE
NOTES:
  - Outbound endpoint IPs (visible after creation) must be allowed by
    the on-prem firewall ACL.
  - Trailing dot on domain is significant for longest-suffix matching.
```

## Skill output — DNS Firewall rule group association

```text
RESOLVER: prod-firewall-rules
VERDICT: READY_TO_DEPLOY
TARGET: prod-firewall-rules
PRE_CHECKS:
  - [PASS] Rule group name unique
  - [PASS] Managed domain list rslvr-fdl-aws-managed-domains-malware exists
  - [PASS] No priority collision on VPC vpc-0abc123 (no existing associations)
  - [PASS] IAM principal holds route53resolver:CreateFirewallRuleGroupAssociation
STEPS:
  1. CONFIRM: About to create-firewall-rule-group prod-firewall-rules and
     associate to VPC vpc-0abc123 at priority 1 (BLOCK malware). Proceed? (yes/no)
  2. aws route53resolver create-firewall-rule-group --name prod-firewall-rules
  3. aws route53resolver create-firewall-rule --firewall-rule-group-id <id>
     --firewall-domain-list-id rslvr-fdl-aws-managed-domains-malware
     --priority 1 --action BLOCK --block-response NXDOMAIN
  4. aws route53resolver create-firewall-rule-group-association
     --firewall-rule-group-id <id> --vpc-id vpc-0abc123 --priority 1
     --name prod-vpc-firewall --mutation-protection ENABLED
POST_VERIFY:
  - (pending execution)
  - list-firewall-rule-group-associations returns priority 1, Status COMPLETE
ENDPOINT_TYPE: N/A (firewall)
SUBNETS: N/A
SECURITY_GROUPS: N/A
FORWARDING_RULES: 1 (existing)
FIREWALL_GROUPS: 1 associated (priority 1, BLOCK malware)
QUERY_LOGS: NONE
NOTES:
  - MutationProtection ENABLED — set to DISABLED before modifying or deleting.
  - Managed domain list is auto-updated by AWS; no manual maintenance needed.
```

## Skill output — query logging with missing resource policy (blocked)

```text
RESOLVER: prod-query-logs-cw
VERDICT: PREREQUISITES_MISSING
TARGET: prod-query-logs-cw
PRE_CHECKS:
  - [PASS] Config name unique
  - [PASS] Log group /aws/route53resolver/prod exists
  - [FAIL] Log group resource policy does not grant route53resolver.amazonaws.com
    logs:PutLogEvents — query logs will be silently dropped.
STEPS: (none — pre-checks failed; add the resource policy)
POST_VERIFY: (none)
ENDPOINT_TYPE: N/A
SUBNETS: N/A
SECURITY_GROUPS: N/A
FORWARDING_RULES: 1 (existing)
FIREWALL_GROUPS: 1 associated
QUERY_LOGS: BLOCKED (missing resource policy)
NOTES:
  - Root cause: CloudWatch Logs resource policy missing.
  - Remediation: run logs:put-resource-policy granting
    route53resolver.amazonaws.com logs:PutLogEvents and logs:CreateLogStream
    on arn:aws:logs:us-east-1:111111111111:log-group:/aws/route53resolver/*:*
  - Then re-run the query log config creation.
```

## What the skill caught that a generic assistant misses

1. **AZ diversity check.** A generic assistant accepts any 2 subnets.
   The skill verifies they are in distinct AZs for HA.

2. **Security group egress verification.** A generic assistant deploys
   the outbound endpoint and walks away. The skill verifies egress on
   UDP/TCP 53 to the exact on-prem DNS server IPs — otherwise queries
   time out silently.

3. **Forwarding rule domain trailing dot.** A generic assistant writes
   `corp.example.local` without the trailing dot. The skill enforces the
   trailing dot for reliable longest-suffix matching.

4. **DNS Firewall priority collision.** A generic assistant picks an
   arbitrary priority. The skill checks existing associations on the VPC
   and flags collisions.

5. **Query log resource policy.** A generic assistant creates the query
   log config and assumes logs will flow. The skill verifies the
   destination resource policy — missing policy = silent log drop.

6. **MutationProtection ENABLED.** A generic assistant omits it. The
   skill defaults to `ENABLED` for production associations.

7. **CONFIRM gate.** A generic assistant auto-executes. The skill emits
   `CONFIRM:` and waits — Resolver endpoints incur hourly charges and
   cannot be trivially undone.

## Slash-command invocation

```
/aws:deploy-route53-resolver
```

Or via the orchestrator:

```
/aws:pipeline
You: "create a Resolver outbound endpoint for hybrid DNS"
```

The orchestrator emits
`[Phase: Deploy | Skills routed: route53-resolver-deployer]` and hands
off to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "create a route53 resolver endpoint"
# [Phase: Deploy | Skills routed: route53-resolver-deployer]
```

## Live-account follow-up (optional, requires AWS CLI)

After the endpoint is created:

```bash
aws route53resolver get-resolver-endpoint \
  --resolver-endpoint-id rslvr-in-abc123 \
  --profile default \
  --query 'ResolverEndpoint.[Name,Direction,Status,IpAddressCount]'

aws route53resolver list-resolver-rule-associations \
  --resolver-rule-id rslvr-rr-def456 \
  --profile default \
  --query 'ResolverRuleAssociations[].[VPCId,Status]'

aws route53resolver list-firewall-rule-group-associations \
  --profile default \
  --query 'FirewallRuleGroupAssociations[?VPCId==`vpc-0abc123`].[Priority,Status]'
```
