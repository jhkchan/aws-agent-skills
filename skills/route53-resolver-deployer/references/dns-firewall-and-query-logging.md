# DNS Firewall & Query Logging Reference

Load this reference when planning Resolver DNS Firewall policies or
query logging configurations. The procedures below cover managed domain
lists, custom domain lists, rule group associations, and query log
destination wiring.

## DNS Firewall decision tree

| Scenario | Use | Why |
|---|---|---|
| Block known malware/botnet domains | **Managed domain list + BLOCK** | AWS updates the list automatically |
| Alert on specific domains (no block) | **Custom domain list + ALERT** | Log without disrupting users |
| Override blocked domain with walled garden | **Custom list + BLOCK + OVERRIDE** | Redirect to remediation portal |
| Allow a domain that a higher-priority group blocks | **Custom list + ALLOW** | Per-VPC exception to a global block |
| Log all DNS queries for audit/SIEM | **Query logging (not firewall)** | Separate feature — query log config |

## Managed domain lists

AWS provides managed domain lists that are automatically updated. The
list IDs are region-specific but follow a consistent naming pattern:

| List (logical name) | Typical use |
|---|---|
| `rslvr-fdl-aws-managed-domains-malware` | Block malware distribution domains |
| `rslvr-fdl-aws-managed-domains-botnet` | Block botnet C2 domains |
| `rslvr-fdl-aws-managed-domains-spam` | Block known spam domains |

**Check available managed lists:**
```bash
aws route53resolver list-firewall-domain-lists \
  --max-results 100 \
  --query 'FirewallDomainLists[?ManagedDomainName!=`null`].[Id,Name,ManagedDomainName]'
```

**Create a BLOCK rule using a managed list:**
```bash
aws route53resolver create-firewall-rule \
  --firewall-rule-group-id <group-id> \
  --firewall-domain-list-id "rslvr-fdl-aws-managed-domains-malware" \
  --priority 1 \
  --action BLOCK \
  --block-response NXDOMAIN
```

## Custom domain lists

**Create a custom list and import domains:**
```bash
aws route53resolver create-firewall-domain-list \
  --creator-request-id fdl-$(date +%s) \
  --name "custom-block-list" \
  --tags '[{"Key":"Environment","Value":"prod"}]'

# domains.txt: one domain per line, wildcards supported
# *.malware.example.
# badsite.example.
# phishingcampaign.example.
aws route53resolver import-firewall-domains \
  --firewall-domain-list-id <fdl-id> \
  --domain-file file://domains.txt \
  --operation REPLACE
```

**Domain syntax rules:**
- Bare domain (`example.com.`) matches the apex only.
- Wildcard (`*.example.com.`) matches all subdomains, NOT the apex.
- Trailing dot is optional but recommended for clarity.
- Domains are case-insensitive.
- Maximum 200,000 domains per list (soft limit).

## Firewall actions matrix

| Action | Effect | BlockResponse required | Override fields |
|---|---|---|---|
| `ALLOW` | Permits the query; overrides a BLOCK in a higher-priority group | No | N/A |
| `BLOCK` with `NXDOMAIN` | Returns "domain does not exist" | Yes (`NXDOMAIN`) | No |
| `BLOCK` with `NODATA` | Returns empty answer | Yes (`NODATA`) | No |
| `BLOCK` with `OVERRIDE` | Returns a custom DNS record | Yes (`OVERRIDE`) | `BlockOverrideDnsType` (CNAME/A), `BlockOverrideDnsValue`, `BlockOverrideTtl` |
| `ALERT` | Logs the query; does NOT block | No | N/A |

**Priority ordering across rule groups on the same VPC:**
- Each rule group association has a VPC-level priority integer (1-1000).
- Lower integer = evaluated first.
- An ALLOW in priority 1 overrides a BLOCK in priority 2 for the same domain.
- Within a rule group, each rule has its own priority integer for the
  same group.

## Rule group association procedure

**Create a rule group and add rules, then associate to a VPC:**
```bash
# Create the rule group (container for rules)
aws route53resolver create-firewall-rule-group \
  --creator-request-id frg-$(date +%s) \
  --name "prod-firewall-rules" \
  --tags '[{"Key":"Environment","Value":"prod"}]'

# Add rules to the group (each with a within-group priority)
aws route53resolver create-firewall-rule \
  --firewall-rule-group-id <group-id> \
  --firewall-domain-list-id <managed-or-custom-fdl-id> \
  --priority 1 \
  --action BLOCK \
  --block-response NXDOMAIN

# Associate the group to a VPC with a VPC-level priority
aws route53resolver create-firewall-rule-group-association \
  --firewall-rule-group-id <group-id> \
  --vpc-id vpc-0abc123 \
  --priority 1 \
  --name "prod-vpc-firewall" \
  --mutation-protection ENABLED
```

**MutationProtection:** when `ENABLED`, the association cannot be deleted
or modified without first setting it to `DISABLED`. Always use `ENABLED`
for production associations to prevent accidental deletion.

**Priority collision check:**
```bash
aws route53resolver list-firewall-rule-group-associations \
  --max-results 100 \
  --query 'FirewallRuleGroupAssociations[?VPCId==`vpc-0abc123`].[Priority,Name,Id]'
```
Each VPC can have up to 5 rule group associations, each with a unique
priority integer.

## Query logging procedure

**One query log config per VPC.** The destination can be CloudWatch
Logs, S3, or Kinesis Data Firehose.

### CloudWatch Logs destination

**Resource policy (run once per account/region):**
```bash
aws logs put-resource-policy \
  --policy-name Route53ResolverQueryLogs \
  --policy-document '{
    "Version":"2012-10-17",
    "Statement":[{"Effect":"Allow","Principal":{"Service":"route53resolver.amazonaws.com"},"Action":["logs:PutLogEvents","logs:CreateLogStream"],"Resource":"arn:aws:logs:us-east-1:111111111111:log-group:/aws/route53resolver/*:*"}]
  }'
```

**Create and associate the query log config:**
```bash
aws logs create-log-group --log-group-name /aws/route53resolver/prod

aws route53resolver put-resolver-query-log-config \
  --name "prod-query-logs-cw" \
  --destination-arn arn:aws:logs:us-east-1:111111111111:log-group:/aws/route53resolver/prod \
  --creator-request-id qlc-$(date +%s)

aws route53resolver associate-resolver-query-log-config \
  --resolver-query-log-config-id <qlc-id> \
  --resource-id vpc-0abc123
```

### S3 destination

**Bucket policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "route53resolver.amazonaws.com"},
    "Action": "s3:PutObject",
    "Resource": "arn:aws:s3:::my-resolver-logs/*"
  }]
}
```

```bash
aws route53resolver put-resolver-query-log-config \
  --name "prod-query-logs-s3" \
  --destination-arn arn:aws:s3:::my-resolver-logs \
  --creator-request-id qlc-$(date +%s)
```

### Kinesis Data Firehose destination

The Firehose delivery stream must be in the same Region as the VPC. The
delivery stream IAM role must allow `route53resolver.amazonaws.com` as a
trusted principal or use a resource-based policy.

```bash
aws route53resolver put-resolver-query-log-config \
  --name "prod-query-logs-firehose" \
  --destination-arn arn:aws:firehose:us-east-1:111111111111:deliverystream/resolver-logs \
  --creator-request-id qlc-$(date +%s)
```

## Query log format

Each log entry is a JSON object:
```json
{
  "version": "1.100000",
  "account_id": "111111111111",
  "region": "us-east-1",
  "vpc_id": "vpc-0abc123",
  "query_timestamp": "2026-08-10T12:00:00Z",
  "query_name": "example.com.",
  "query_type": "A",
  "query_class": "IN",
  "rcode": "NOERROR",
  "answers": [{"Rdata":"93.184.216.34","Type":"A","Class":"IN"}],
  "srcaddr": "10.0.1.42",
  "srcport": "12345",
  "transport": "UDP"
}
```

Use the `query_name` and `srcaddr` fields for SIEM correlation and
threat hunting.

## Verification commands

```bash
# Verify firewall rule group association
aws route53resolver list-firewall-rule-group-associations \
  --query 'FirewallRuleGroupAssociations[?VPCId==`vpc-0abc123`].[Priority,Name,Status,Id]'

# Verify query log config association
aws route53resolver list-resolver-query-log-config-associations \
  --filters Name=ResourceId,Values=vpc-0abc123 \
  --query 'ResolverQueryLogConfigAssociations[].[Resolution,Status]'

# Check CloudWatch for incoming logs (within 5 minutes of association)
aws logs filter-log-events \
  --log-group-name /aws/route53resolver/prod \
  --start-time $(($(date +%s) * 1000 - 300000)) \
  --limit 10
```
