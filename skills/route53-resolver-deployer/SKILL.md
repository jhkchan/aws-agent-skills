---
name: route53-resolver-deployer
description: >-
  Provisions Route 53 Resolver endpoints, forwarding rules, DNS Firewall,
  and query logging with secure networking defaults. Supports inbound
  endpoints (on-prem DNS to Route 53), outbound endpoints (VPC to
  on-prem DNS), forwarding rules with VPC associations, Resolver DNS
  Firewall (managed/custom domain lists, block/alert actions), and query
  logging to CloudWatch, S3, or Kinesis. Runs pre-checks (subnet AZ
  diversity, security group port 53 rules, IAM permissions, query log
  destination policies), emits create-resolver-endpoint, create-resolver
  -rule, create-firewall-rule, put-resolver-query-log-config CLIs behind
  a CONFIRM gate, verifies via get-resolver-endpoint. Emits
  READY_TO_DEPLOY | PREREQUISITES_MISSING. Use when provisioning Resolver
  endpoints, forwarding rules, DNS Firewall policies, or query logging.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline plan classification. Live-account
  operations use aws route53resolver create-resolver-endpoint,
  create-resolver-rule, associate-resolver-rule, create-firewall-domain-list,
  create-firewall-rule, create-firewall-rule-group-association,
  put-resolver-query-log-config, associate-resolver-query-log-config,
  get-resolver-endpoint, list-resolver-rule-associations (AWS CLI v2,
  SSO or key-based credentials).
keywords:
  - Route 53 Resolver
  - Resolver endpoint
  - inbound endpoint
  - outbound endpoint
  - forwarding rule
  - conditional forwarding
  - DNS Firewall
  - firewall domain list
  - firewall rule group
  - managed domain list
  - custom domain list
  - query logging
  - CloudWatch Logs
  - S3 logging
  - Kinesis Firehose
  - DNS
  - hybrid DNS
  - on-prem DNS
  - VPC DNS
  - route53resolver
  - rule association
tags: [route53, resolver, dns, networking, firewall, query-logging, deploy, hybrid-dns, vpc]
dependencies:
  - aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: Networking
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  version: 0.1.0
  author: "Jacky Chan — AWS Community Builder"
  tags:
    - route53
    - resolver
    - dns
    - networking
    - firewall
    - query-logging
    - deploy
    - hybrid-dns
    - vpc
  dependencies:
    - aws-orchestrator
  keywords:
    - Route 53 Resolver
    - Resolver endpoint
    - inbound endpoint
    - outbound endpoint
    - forwarding rule
    - DNS Firewall
    - firewall domain list
    - query logging
    - hybrid DNS
    - on-prem DNS
  when_to_use: >-
    Creating a Route 53 Resolver inbound endpoint (on-prem resolvers
    forwarding to Route 53), outbound endpoint (VPC forwarding to on-prem
    DNS), conditional forwarding rules with VPC associations, Resolver DNS
    Firewall policies (managed or custom domain lists), or Resolver query
    logging to CloudWatch Logs, S3, or Kinesis Data Firehose.
  activation_triggers:
    - "create Resolver endpoint"
    - "provision Resolver inbound endpoint"
    - "provision Resolver outbound endpoint"
    - "deploy Route 53 Resolver"
    - "conditional forwarding rule"
    - "forwarding rule association"
    - "DNS Firewall"
    - "firewall domain list"
    - "firewall rule group"
    - "managed domain list"
    - "custom domain list"
    - "block DNS domains"
    - "Resolver query logging"
    - "DNS query logs CloudWatch"
    - "DNS query logs S3"
    - "hybrid DNS setup"
    - "on-prem DNS forwarding"
    - "route53resolver create-resolver-endpoint"
    - "route53resolver create-resolver-rule"
    - "route53resolver create-firewall-rule"
  invocation_schema: >-
    Input: either (a) a Resolver deployment intent (create inbound endpoint,
    outbound endpoint, forwarding rule, DNS Firewall policy, or query log
    config) with target VPC, subnets, security groups, IP addresses, and
    forwarding targets; OR (b) an endpoint/rule ID for live-account update
    or validation. Output: deterministic RESOLVER/VERDICT/PRE_CHECKS/
    STEPS/POST_VERIFY block per operation, where VERDICT is one of
    READY_TO_DEPLOY, PREREQUISITES_MISSING.
---

# Route 53 Resolver Deployer

## What this skill does

Provisions Route 53 Resolver endpoints, forwarding rules, DNS Firewall
policies, and query logging configurations with secure networking
defaults. Enforces the minimum two subnets in distinct Availability Zones
for every endpoint, security groups that only expose UDP/TCP 53 to the
expected source CIDRs, forwarding rules that target reachable IPs with
the correct port, DNS Firewall rule group associations that do not
conflict on priority, and query log destinations that are writable by the
`route53resolver` service principal. Runs deterministic pre-checks
before any state-changing CLI, emits the exact
`create-resolver-endpoint`, `create-resolver-rule`,
`create-firewall-domain-list`, `create-firewall-rule`, and
`put-resolver-query-log-config` CLIs behind a CONFIRM gate, and verifies
the deployment via `get-resolver-endpoint` and
`list-resolver-rule-associations`. Every Resolver plan surfaces the
inbound/outbound direction, the rule-priority ordering, the firewall
action matrix, and the query-log destination write-permission gate.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **Quick reference** | Verdict thresholds + pre-check priority order + endpoint config matrix | Before any operation |
| **Mindset** | Why defaults matter; Resolver silent-failure modes; overwrite traps | Understanding the deployment model |
| **Pre-flight** | Endpoint metadata gate — subnets, security groups, target IPs, IAM permissions | Before executing any CLI |
| **Process** | Per-operation planning: inbound, outbound, forwarding rule, DNS Firewall, query logging | When choosing which operation |
| **Common patterns** | Production hybrid DNS / conditional forwarding / DNS Firewall / query logging boilerplate | Boilerplate lookup |
| **STRICT output contract** | Required RESOLVER/VERDICT/PRE_CHECKS/STEPS/POST_VERIFY block | Formatting the response |
| **NEVER (top 5)** | Hard rules that prevent common insecure patterns | Review before deploy |
| **Expert heuristic** | Choosing inbound vs outbound vs both for hybrid DNS | Choosing endpoint strategy |

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `PREREQUISITES_MISSING` | Any pre-check failed (fewer than 2 subnets in distinct AZs, security group missing UDP/TCP 53 ingress, outbound target IP unreachable, forwarding rule domain name malformed, DNS Firewall rule group priority collides with an existing association, query log destination ARN is not writable by route53resolver, IAM permission missing, endpoint name already exists for create) | List failures, do NOT execute |
| `READY_TO_DEPLOY` | All pre-checks passed; awaiting CONFIRM gate | Emit exact CLI sequence with full endpoint config, wait for operator yes |

**Priority order for pre-checks (apply in this sequence, all must pass for
READY_TO_DEPLOY):**

1. **Endpoint name uniqueness** — `list-resolver-endpoints` returns no
   endpoint with the target name (for create) or matches exactly one
   (for update).
2. **Subnet count and AZ diversity** — every Resolver endpoint requires
   at least 2 IP addresses in 2 distinct Availability Zones. Fewer than
   2 subnets is a hard block.
3. **Security group ingress** — the referenced security group allows
   UDP/TCP 53 inbound from the expected source CIDR (the peered VPC,
   Direct Connect, or VPN CIDR for inbound endpoints; the VPC CIDR for
   outbound endpoints).
4. **Security group egress** — the referenced security group allows
   UDP/TCP 53 outbound to the on-prem DNS server IPs (outbound endpoints)
   or to the VPC CIDR (inbound endpoints).
5. **Forwarding rule domain** — the `DomainName` is a valid DNS suffix
   (e.g., `corp.example.local.`), trailing dot handled, not a TLD that
   conflicts with a public domain.
6. **Forwarding target IPs** — every IP in `TargetIps` is reachable from
   the outbound endpoint subnets (route table check or caller-provided
   attestation). Port 53 is the default; non-standard ports are flagged.
7. **Rule association VPC** — the target VPC exists in the same account
   and region (or is shared via `share-resolver-rule` cross-account).
8. **DNS Firewall rule group priority** — the `Priority` integer on a
   new `firewall-rule-group-association` does not collide with an
   existing association on the same VPC. Lower priority = evaluated
   first.
9. **Firewall domain list content** — custom domain lists use valid
   domain syntax with wildcards (`*.malware.example.`). Malformed
   entries are rejected.
10. **Firewall action consistency** — `BLOCK` actions have a
    `BlockResponse` (NXDOMAIN, NODATA, or custom IP) and optionally a
    `BlockOverrideDnsType`. `ALERT` logs but does not block. `ALLOW`
    overrides a matching BLOCK in a higher-priority group.
11. **Query log destination ARN** — the CloudWatch Logs log group, S3
    bucket, or Kinesis Data Firehose exists and the
    `route53resolver` service principal has write permission
    (`logs:PutLogEvents`, `s3:PutObject`, or `firehose:PutRecord`).
12. **Query log config name uniqueness** — `list-resolver-query-log-configs`
    returns no config with the target name.
13. **VPC DNS settings** — `enableDnsHostnames` and `enableDnsSupport`
    are both `true` on the target VPC (checked via `ec2:describe-vpc-attribute`).
14. **IAM permissions** — the operator principal holds
    `route53resolver:CreateResolverEndpoint`,
    `CreateResolverRule`, `AssociateResolverRule`,
    `CreateFirewallDomainList`, `CreateFirewallRule`,
    `CreateFirewallRuleGroupAssociation`, or
    `PutResolverQueryLogConfig` (as applicable to the operation).

**Route 53 Resolver limits (2026):**

- Resolver endpoints per Region: 4 inbound + 4 outbound (soft). 2-100 IPs per endpoint (>= 2 AZs).
- Resolver rules per account: 1000 (soft). Shareable cross-account via RAM.
- DNS Firewall rule groups per VPC: 5 (soft). Domain lists per account: 5000. Domains per list: 200,000.
- Query log configs per account: 2000 (soft). One query log config association per VPC.

## Mindset

**One-line takeaway:** Resolver silently accepts misconfigured security
groups and route tables. An outbound endpoint with a security group that
blocks egress to on-prem port 53 will deploy cleanly — DNS queries from
the VPC will time out, and the operator will blame the on-prem DNS
server. The skill enforces the networking gate at pre-check time.

Driven by three Resolver realities:

- **Resolver endpoints need a minimum of two subnets in two AZs.** A
  single-subnet endpoint is rejected at API time, but a two-subnet
  endpoint where both subnets are in the same AZ silently loses HA.

- **Forwarding rules are evaluated in priority order against the VPC.**
  If two rules match the same domain suffix, the lower-priority integer
  wins. A new rule with an overlapping domain silently shadows an
  existing rule.

- **DNS Firewall rule groups stack per VPC.** Each association has a
  priority integer; a BLOCK in priority 1 is overridden by an ALLOW in
  priority 2. Misordered priorities are the #1 cause of "why is my block
  not working" tickets.

## Pre-flight: resolver endpoint metadata gate

Run before classification. Misclassifying these produces wrong plans.

**Pagination:** `list-resolver-endpoints` returns at most 100 per page
(via `--max-results`). Use `--next-token` to drain. `list-resolver-rules`
is paginated the same way.

**Live-account pre-flight (skip if offline plan audit):**
1. `aws route53resolver list-resolver-endpoints --max-results 100` —
   confirm the endpoint name does not collide (for create) or matches
   (for update).
2. `aws route53resolver get-resolver-endpoint --resolver-endpoint-id <id>`
   — capture the full endpoint config for snapshot/diff.
3. `aws ec2 describe-subnets --subnet-ids <ids>` — confirm the subnets
   exist, are in distinct AZs, and belong to the target VPC.
4. `aws ec2 describe-security-groups --group-ids <sg-id>` — confirm the
   security group exists and its ingress/egress rules cover UDP/TCP 53
   on the expected CIDRs.
5. `aws ec2 describe-vpc-attribute --vpc-id <vpc> --attribute enableDnsSupport`
   and `--attribute enableDnsHostnames` — confirm both are `true`.
6. `aws route53resolver list-resolver-rules --max-results 100` — for
   forwarding rules, check domain-name overlap and priority.
7. `aws route53resolver list-firewall-rule-group-associations --max-results 100`
   — for DNS Firewall, check priority collisions on the target VPC.
8. `aws logs describe-log-groups --log-group-name-prefix <name>` (for
   CloudWatch) / `aws s3api head-bucket --bucket <name>` (for S3) /
   `aws firehose describe-delivery-stream --delivery-stream-name <name>`
   (for Kinesis) — verify the query log destination exists.

**Malformed input:** if the Resolver spec is missing required fields
(`EndpointName`, `Direction`, `Subnets` (>= 2), or `SecurityGroupIds`),
emit `VERDICT: PREREQUISITES_MISSING` with `REASON: Resolver spec
missing required field — EndpointName, Direction, >= 2 SubnetIds in
distinct AZs, or SecurityGroupIds. Cannot plan.` and `REMEDIATION:
Provide the full endpoint configuration per
https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver.html.`

| Attribute | Effect on operation |
|---|---|
| Fewer than 2 subnets | API rejects. PREREQUISITES_MISSING. |
| Both subnets in same AZ | Deploys but loses HA. Flag in NOTES; allow if user-acknowledged. |
| Security group missing UDP 53 ingress | DNS queries silently time out. PREREQUISITES_MISSING. |
| Outbound target IP unreachable from subnet route table | Forwarding rule deploys but queries fail. PREREQUISITES_MISSING. |
| Forwarding rule domain overlaps existing rule with lower priority | New rule shadows existing. Flag in NOTES. |
| DNS Firewall rule group priority collides on VPC | API rejects. PREREQUISITES_MISSING. |
| Query log destination not writable by route53resolver | Logs silently dropped. PREREQUISITES_MISSING. |
| VPC enableDnsSupport false | Resolver endpoints cannot serve. PREREQUISITES_MISSING. |

## Process — operation planning (apply in order)

### Step 0: Expert knowledge — non-obvious Resolver behaviors

These behaviors are easy to misjudge without operational Resolver
experience. Each changes a plan if ignored:

- **Inbound endpoint IPs are the IPs on-prem forwards to.** The on-prem
  DNS server's forwarder config must point at the inbound endpoint IPs,
  not at the VPC CIDR. These IPs are assigned from the subnet CIDR and
  are visible in `get-resolver-endpoint` after creation.

- **Outbound endpoint IPs are the source IPs the on-prem DNS server
  sees.** The on-prem firewall ACL must allow UDP/TCP 53 from the
  outbound endpoint IPs (visible in `get-resolver-endpoint`). Mismatched
  firewall rules are the #1 cause of "forwarding rule works from a test
  EC2 instance but not from Resolver."

- **Forwarding rules match by longest suffix.** A rule for
  `corp.example.local.` matches `api.corp.example.local.` but NOT
  `corp.example.com.`. The trailing dot is significant.

- **Forwarding rules are SYSTEM or FORWARD.** `SYSTEM` (default AWS
  rule) resolves internet domains via Route 53. `FORWARD` sends to
  `TargetIps`. You cannot delete the SYSTEM rule; only associate or
  disassociate per VPC.

- **Rule associations are per-VPC.** Cross-account associations require
  sharing via RAM (`share-resolver-rule`) first — the #2 cause of "rule
  exists but my VPC does not use it" tickets.

- **DNS Firewall evaluates rule groups in priority order.** Priority 1
  is evaluated first; an ALLOW in priority 2 overrides a BLOCK in
  priority 1 for the same domain. Plan ordering before associating.

- **Firewall domain lists support wildcards.** `*.malware.example.`
  matches subdomains; bare `malware.example.` matches apex only.

- **BLOCK actions have a response.** `BlockResponse` is `NXDOMAIN`,
  `NODATA`, or `OVERRIDE` (custom DNS record — requires
  `BlockOverrideDnsType`, `BlockOverrideDnsValue`, `BlockOverrideTtl`).

- **Query logging has one association per VPC.** Switching destinations
  requires disassociating the old config first. Destinations need a
  resource policy granting `route53resolver.amazonaws.com` write access.

- **Resolver cache (2024-2026).** Configurable cache TTL on forwarding
  rules via `ResolverConfig`. Lower TTL = fresher data but more traffic.

### Step 1: Pre-check gate — PREREQUISITES_MISSING if any check fails

Run ALL of the following pre-checks. If ANY fails, the verdict is
PREREQUISITES_MISSING with the failed checks enumerated in PRE_CHECKS.
Do NOT execute.

**For ALL operations:**
1. Endpoint/rule/config name is set, <= 64 chars, matches `[a-zA-Z0-9-]`.
2. Target VPC exists, `enableDnsSupport: true`, `enableDnsHostnames: true`.
3. IAM principal holds the relevant `route53resolver:` permission.

**For create-resolver-endpoint (inbound or outbound):**
4. `Direction` is `INBOUND` or `OUTBOUND`.
5. `IpAddresses` contains at least 2 entries in 2 distinct AZs.
6. Each subnet in `IpAddresses` belongs to the target VPC.
7. `SecurityGroupIds` references exactly one or more existing security
   groups in the VPC.
8. For INBOUND: the security group ingress allows UDP/TCP 53 from the
   on-prem/peered source CIDR.
9. For OUTBOUND: the security group egress allows UDP/TCP 53 to the
   on-prem DNS server IPs.
10. Endpoint name does not collide with an existing endpoint
    (`list-resolver-endpoints`).

**For create-resolver-rule (forwarding):**
11. `DomainName` is a valid DNS suffix with trailing dot.
12. `TargetIps` references at least one IP (port defaults to 53; non-53
    flagged in NOTES).
13. The domain does not overlap an existing forwarding rule with lower
    priority (flag, allow with acknowledgement).
14. `RuleType` is `FORWARD`. (`SYSTEM` rules are managed by AWS.)

**For associate-resolver-rule:**
15. The rule exists and is in a `COMPLETE` state.
16. The target VPC exists and is not already associated with a
    conflicting rule on the same domain.

**For create-firewall-domain-list:**
17. Domain list name does not collide.
18. (For `import-firewall-domains`): each domain is valid syntax,
    wildcard prefix `*.` supported, trailing dot optional.

**For create-firewall-rule (in a rule group):**
19. The referenced `FirewallDomainListId` exists.
20. `Action` is one of `ALLOW`, `BLOCK`, `ALERT`.
21. For `BLOCK`: `BlockResponse` is set (`NXDOMAIN`, `NODATA`,
    `OVERRIDE`); if `OVERRIDE`, the override DNS type, value, and TTL
    are set.
22. `Priority` within the rule group does not collide with an existing
    rule.

**For create-firewall-rule-group-association:**
23. The rule group exists.
24. `Priority` does not collide with an existing association on the
    target VPC (lower priority = evaluated first).
25. `MutationProtection` is `ENABLED` for production associations.

**For put-resolver-query-log-config:**
26. `DestinationArn` points to an existing CloudWatch Logs log group,
    S3 bucket, or Kinesis Firehose.
27. The destination resource policy allows `route53resolver.amazonaws.com`
    to write (`logs:PutLogEvents`, `s3:PutObject`, `firehose:PutRecord`).
28. Config name does not collide.

**For associate-resolver-query-log-config:**
29. The target VPC is not already associated with another query log
    config.

### Step 2: READY_TO_DEPLOY — emit deployment plan

If all pre-checks pass, emit `VERDICT: READY_TO_DEPLOY` with the exact
CLI sequence and the CONFIRM gate. The plan includes:

- The exact `aws route53resolver create-resolver-endpoint` CLI with the
  full config (Direction, IpAddresses, SecurityGroupIds, Name, Tags).
- The follow-up `create-resolver-rule` CLI for each forwarding rule.
- The follow-up `associate-resolver-rule` CLI for each VPC association.
- The follow-up `create-firewall-domain-list` and `import-firewall-domains`
  CLIs for each custom domain list.
- The follow-up `create-firewall-rule` CLI for each rule in a group.
- The follow-up `create-firewall-rule-group-association` CLI for each VPC.
- The follow-up `put-resolver-query-log-config` and
  `associate-resolver-query-log-config` CLIs for query logging.
- The CONFIRM gate prompt.

### Step 3: Execute behind CONFIRM gate

- **MANDATORY CONFIRMATION GATE.** Before any state-changing CLI
  (`create-resolver-endpoint`, `create-resolver-rule`,
  `associate-resolver-rule`, `create-firewall-rule-group-association`,
  `put-resolver-query-log-config`), emit:
  `CONFIRM: About to <operation> <resource> in account <account>
  region <region>. This will <consequence>. Proceed? (yes/no)`. Do NOT
  execute until the operator confirms.
- Snapshot the current endpoint/rule config before modification:
  `aws route53resolver get-resolver-endpoint --resolver-endpoint-id <id>
  --output json > /tmp/<endpoint-name>-backup-$(date +%s).json`.
- Execute the CLI with the full config.

### Step 4: Post-verification

After the operation finishes, run post-verification:

1. `get-resolver-endpoint --resolver-endpoint-id <id>` returns
   `Status: OPERATIONAL`.
2. For inbound endpoints: the IP addresses are reachable from on-prem
   (confirm with on-prem DNS admin or `dig @<ip> example.com`).
3. For outbound endpoints: the IP addresses are the source IPs the
   on-prem DNS server sees.
4. `list-resolver-rule-associations --resolver-rule-id <id>` returns
   the expected VPC associations with `Status: COMPLETE`.
5. For DNS Firewall: `list-firewall-rule-group-associations` returns
   the association with the expected priority.
6. For query logging: `list-resolver-query-log-config-associations`
   returns the VPC with `Status: COMPLETE`; verify log entries appear
   in the destination within 5 minutes.

## Common resolver patterns (boilerplate)

### Inbound endpoint — on-prem DNS forwarding to Route 53

```bash
aws route53resolver create-resolver-endpoint \
  --creator-request-id inbound-$(date +%s) \
  --name "prod-inbound" \
  --security-group-ids sg-0abc123 \
  --direction INBOUND \
  --ip-addresses '[
    {"SubnetId":"subnet-aaa","Ip":"10.0.1.10"},
    {"SubnetId":"subnet-bbb","Ip":"10.0.2.10"}
  ]' \
  --tags '[{"Key":"Environment","Value":"prod"},{"Key":"Purpose","Value":"on-prem-to-route53"}]'
```

### Outbound endpoint + forwarding rule — VPC to on-prem DNS

```bash
aws route53resolver create-resolver-endpoint \
  --creator-request-id outbound-$(date +%s) \
  --name "prod-outbound" \
  --security-group-ids sg-0def456 \
  --direction OUTBOUND \
  --ip-addresses '[
    {"SubnetId":"subnet-aaa"},
    {"SubnetId":"subnet-bbb"}
  ]' \
  --tags '[{"Key":"Environment","Value":"prod"},{"Key":"Purpose","Value":"vpc-to-onprem"}]

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

### DNS Firewall — managed domain list block

```bash
# Use an AWS-managed domain list for malware/botnet domains
aws route53resolver create-firewall-rule \
  --firewall-rule-group-id <group-id> \
  --firewall-domain-list-id "rslvr-fdl-aws-managed-domains-malware" \
  --priority 1 \
  --action BLOCK \
  --block-response NXDOMAIN

# Associate the rule group to a VPC (MutationProtection prevents accidental deletion)
aws route53resolver create-firewall-rule-group-association \
  --firewall-rule-group-id <group-id> \
  --vpc-id vpc-0abc123 \
  --priority 1 \
  --name "prod-vpc-block-malware" \
  --mutation-protection ENABLED
```

### DNS Firewall — custom domain list with ALERT

```bash
aws route53resolver create-firewall-domain-list \
  --creator-request-id fdl-$(date +%s) \
  --name "custom-alert-list" \
  --tags '[{"Key":"Environment","Value":"prod"}]'

aws route53resolver import-firewall-domains \
  --firewall-domain-list-id <fdl-id> \
  --domain-file file://domains.txt
  # one domain per line: *.gambling.example. badsite.example.

aws route53resolver create-firewall-rule \
  --firewall-rule-group-id <group-id> \
  --firewall-domain-list-id <fdl-id> \
  --priority 2 \
  --action ALERT
```

### Query logging — CloudWatch Logs

```bash
# Resource policy on the log group (run once)
aws logs put-resource-policy \
  --policy-name Route53ResolverQueryLogs \
  --policy-document '{
    "Version":"2012-10-17",
    "Statement":[{"Effect":"Allow","Principal":{"Service":"route53resolver.amazonaws.com"},"Action":["logs:PutLogEvents","logs:CreateLogStream"],"Resource":"arn:aws:logs:us-east-1:111111111111:log-group:/aws/route53resolver/*:*"}]
  }'

aws logs create-log-group --log-group-name /aws/route53resolver/prod

aws route53resolver put-resolver-query-log-config \
  --name "prod-query-logs-cw" \
  --destination-arn arn:aws:logs:us-east-1:111111111111:log-group:/aws/route53resolver/prod \
  --creator-request-id qlc-$(date +%s)

aws route53resolver associate-resolver-query-log-config \
  --resolver-query-log-config-id <qlc-id> \
  --resource-id vpc-0abc123
```

### Query logging — S3 bucket

```bash
aws s3api put-bucket-policy --bucket my-resolver-logs --policy file://bucket-policy.json
# bucket-policy.json grants route53resolver.amazonaws.com s3:PutObject

aws route53resolver put-resolver-query-log-config \
  --name "prod-query-logs-s3" \
  --destination-arn arn:aws:s3:::my-resolver-logs \
  --creator-request-id qlc-$(date +%s)
```

## STRICT output contract

### Required output structure

Every response MUST begin with this block — no preamble, no conversational
opening:

```text
RESOLVER: <endpoint-name or rule-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
TARGET: <endpoint-name> (endpoint-id: <id> for updates)
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. CONFIRM: About to <operation> <resource> in account <account> region <region>. This will <consequence>. Proceed? (yes/no)
  2. <exact CLI command — no placeholders>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
ENDPOINT_TYPE: INBOUND | OUTBOUND
SUBNETS: <count> subnets in <count> AZs
SECURITY_GROUPS: <count> (ingress: <CIDR>/<ports>; egress: <CIDR>/<ports>)
FORWARDING_RULES: <count> (domains: <list>)
FIREWALL_GROUPS: <count> associated (priorities: <list>)
QUERY_LOGS: CloudWatch | S3 | Kinesis | NONE
NOTES: <networking posture, DNS strategy, rule-priority caveats>
```

### FORBIDDEN output patterns

- NEVER start with "Let me analyze…" or "I'll create…" — the VERDICT
  block is the FIRST line, always. No conversational preamble.
- NEVER use lowercase verdict values — emit `READY_TO_DEPLOY` or
  `PREREQUISITES_MISSING` (not `ready`, `prerequisites`).
- NEVER omit PRE_CHECKS — every pre-check run must appear with `[PASS]`
  or `[FAIL]` and a specific reason for each failure. An empty
  PRE_CHECKS block is non-compliant.
- NEVER emit a plan with placeholder values (e.g., `<endpoint-id>`,
  `<account-id>`) in a READY_TO_DEPLOY plan — every field must be
  populated with actual values from the input.
- NEVER omit the CONFIRM gate as the first STEPS entry for any
  state-changing operation.
- NEVER claim success without verifying that the endpoint reached
  `OPERATIONAL` status (via `get-resolver-endpoint`).
- NEVER put-update an endpoint or rule without snapshotting the existing
  config first — updates to `SecurityGroupIds` and `TargetIps` overwrite
  silently.
- NEVER silently allow a DNS Firewall rule group association with a
  colliding priority — block it explicitly with a [FAIL] pre-check row.

### Perfect example output

```text
RESOLVER: prod-outbound
VERDICT: READY_TO_DEPLOY
TARGET: prod-outbound
PRE_CHECKS:
  - [PASS] Endpoint name unique (no collision in list-resolver-endpoints)
  - [PASS] 2 subnets in 2 distinct AZs (us-east-1a, us-east-1b)
  - [PASS] Security group sg-0def456 egress UDP/TCP 53 to 10.99.1.5, 10.99.2.5
  - [PASS] VPC enableDnsSupport: true, enableDnsHostnames: true
  - [PASS] Forwarding rule domain corp.example.local. is valid
  - [PASS] Target IPs reachable (10.99.1.5, 10.99.2.5 port 53)
  - [PASS] IAM principal holds route53resolver:CreateResolverEndpoint
STEPS:
  1. CONFIRM: About to create-resolver-endpoint prod-outbound in account 111111111111 region us-east-1. This will CREATE a new OUTBOUND endpoint with 2 IPs in 2 AZs. Proceed? (yes/no)
  2. aws route53resolver create-resolver-endpoint --creator-request-id outbound-1699000000 --name prod-outbound --security-group-ids sg-0def456 --direction OUTBOUND --ip-addresses '[{"SubnetId":"subnet-aaa"},{"SubnetId":"subnet-bbb"}]' --tags '[{"Key":"Environment","Value":"prod"}]'
  3. aws route53resolver create-resolver-rule --creator-request-id rule-1699000000 --name forward-corp-local --rule-type FORWARD --domain-name "corp.example.local." --resolver-endpoint-id <returned-id> --target-ips '[{"Ip":"10.99.1.5","Port":53},{"Ip":"10.99.2.5","Port":53}]'
  4. aws route53resolver associate-resolver-rule --resolver-rule-id <returned-rule-id> --vpc-id vpc-0abc123
POST_VERIFY:
  - (pending execution)
  - get-resolver-endpoint returns Status: OPERATIONAL
  - list-resolver-rule-associations returns vpc-0abc123 with Status: COMPLETE
ENDPOINT_TYPE: OUTBOUND
SUBNETS: 2 subnets in 2 AZs (us-east-1a, us-east-1b)
SECURITY_GROUPS: 1 (egress: 10.99.1.5/53, 10.99.2.5/53)
FORWARDING_RULES: 1 (domains: corp.example.local.)
FIREWALL_GROUPS: 0 associated
QUERY_LOGS: NONE
NOTES:
  - Outbound endpoint IPs (visible after creation) must be allowed by the on-prem firewall ACL.
  - Forwarding rule matches corp.example.local. and all subdomains. Trailing dot is significant.
  - Associate query log config separately if DNS query logging is required.
```

## NEVER (top 5)

These are the highest-impact, most-frequent failure modes in Route 53
Resolver deployments. Violating any one of these is a networking or
security regression.

1. **NEVER create a Resolver endpoint with fewer than 2 subnets in 2
   distinct AZs.** A single-AZ endpoint loses the high-availability
   guarantee — if that AZ fails, all DNS forwarding stops. The API
   requires 2 IPs minimum, but both in the same AZ silently degrades
   HA. Block at pre-check.

2. **NEVER deploy an outbound endpoint without verifying the security
   group egress to the on-prem DNS server IPs.** The endpoint deploys
   cleanly, but every forwarded query times out. The on-prem team sees
   no traffic and the VPC team blames the on-prem DNS server. The
   pre-check gate verifies egress on UDP/TCP 53 to the exact target IPs.

3. **NEVER associate a DNS Firewall rule group to a VPC without
   checking priority collisions.** Each VPC can have up to 5 rule
   group associations, each with a unique priority integer. A new
   association with a colliding priority is rejected by the API — but
   a non-colliding priority that semantically overrides an existing
   ALLOW/BLOCK ordering is the #1 cause of "why is my block not
   working" tickets. Plan the priority ordering before associating.

4. **NEVER enable query logging without a resource policy on the
   destination.** The `route53resolver` service principal needs
   `logs:PutLogEvents` (CloudWatch), `s3:PutObject` (S3), or
   `firehose:PutRecord` (Kinesis) on the destination resource. Missing
   policy = silent log drop. The pre-check gate verifies the resource
   policy.

5. **NEVER create a forwarding rule for a domain that overlaps an
   existing rule with a lower priority integer.** The lower-priority
   rule is evaluated first and silently shadows the new rule. The
   pre-flight gate flags domain overlap and recommends priority
   reordering.

## Expert heuristic: choosing inbound vs outbound vs both

The right Resolver endpoint strategy is a function of where the DNS
source of truth lives, not a one-size-fits-all. The heuristic below
resolves the trade-off deterministically.

```
Hybrid DNS scenario
   ├─ On-prem DNS is the source of truth for private domains?
   │    └─ OUTBOUND endpoint + forwarding rules for corp.example.local.
   │         VPC instances query Resolver; Resolver forwards to on-prem.
   │         On-prem firewall must allow UDP/TCP 53 from endpoint IPs.
   │
   ├─ Route 53 is the source of truth for private domains (Private Hosted Zones)?
   │    └─ INBOUND endpoint. On-prem DNS forwarder points to endpoint IPs.
   │         On-prem queries traverse Direct Connect / VPN to Resolver.
   │         Resolver answers from the Private Hosted Zone.
   │
   ├─ Both directions (corp.example.local. on-prem, internal.aws. on Route 53)?
   │    └─ BOTH endpoints. Forwarding rules for on-prem domains only.
   │         Inbound endpoint lets on-prem resolve Route 53 PHZ records.
   │         Most common enterprise pattern.
   │
   └─ Pure cloud (no on-prem)?
        └─ Neither endpoint. Resolver answers from Route 53 PHZ + public.
             Add DNS Firewall for threat protection and query logging for audit.
```

**Decision rules:**
- Default to BOTH endpoints for enterprise hybrid environments. The
  marginal cost of a second endpoint is small compared to the DNS
  troubleshooting time it saves.
- For outbound-only, ensure the on-prem DNS servers are reachable from
  the VPC subnets (Direct Connect, VPN, or Transit Gateway).
- For inbound-only, ensure the on-prem DNS forwarder is configured to
  send to the inbound endpoint IPs (not the VPC CIDR).
- Always pair Resolver endpoints with DNS Firewall for threat protection
  (block known-malicious domains) and query logging for audit (who
  queried what, when).
- For multi-account, share forwarding rules via RAM rather than
  recreating per account. The rule is created once in the Resolver
  administrator account and shared to member accounts.

ALWAYS emit `enableDnsSupport: true` and `enableDnsHostnames: true` on
every VPC that uses Resolver. Without both, Resolver endpoints cannot
serve the VPC.

## Recent AWS features (2024-2026)

- **Route 53 Resolver DNS Firewall (GA, enhanced 2024-2026):** managed
  domain lists for malware, botnet, and command-and-control domains,
  auto-updated by AWS. Custom domain lists support wildcard matching and
  bulk import. Rule group associations support `MutationProtection` to
  prevent accidental deletion.
- **Resolver cache (2024-2025):** configurable cache TTL on forwarding
  rules via `ResolverConfig`. Reduces forwarding traffic to on-prem DNS
  at the cost of stale-on-failover. Default remains uncached.
- **DNS Firewall ALERT action with CloudWatch metrics (2024-2025):**
  ALERT actions now emit CloudWatch metrics per rule group, enabling
  dashboards and alarms on DNS policy violations without blocking.
- **Query logging to Kinesis Data Firehose (2024-2025):** Firehose
  destinations now support direct delivery to OpenSearch, S3, and
  third-party SIEMs for long-term DNS query retention.
- **Cross-account rule sharing via RAM (enhanced 2024-2025):** forwarding
  rules can now be shared with OUs (not just individual accounts) via
  AWS RAM, simplifying multi-account Resolver topologies.
- **DNS Firewall OVERRIDE block response (2024-2025):** BLOCK actions can
  return a custom DNS record (e.g., a walled-garden IP) instead of
  NXDOMAIN/NODATA — useful for redirecting blocked domains to a
  remediation portal.
- **Resolver endpoint health checks via CloudWatch (2025-2026):**
  per-endpoint health metrics (query count, error rate, latency) for
  proactive monitoring and alarm automation.

## AWS documentation

- **Route 53 Resolver Developer Guide** — https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver.html
- **Resolver endpoints** — https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver-endpoints.html
- **Resolver forwarding rules** — https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver-rules.html
- **DNS Firewall** — https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver-dns-firewall.html
- **Resolver query logging** — https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver-query-logs.html
- **Resolver CLI reference** — https://docs.aws.amazon.com/cli/latest/reference/route53resolver/

## Domain

AWS CloudOps / Networking & Content Delivery — Route 53 Resolver Provisioning.
