---
name: guardduty-finding-automator
description: >-
  Designs and implements automated response workflows for Amazon GuardDuty
  findings. Wires EventBridge rules to severity-based routing (Critical/High
  auto-isolate, Medium notify, Low log), Lambda remediation functions
  (isolate EC2 via security group swap, revoke IAM access keys, block
  source IPs in WAF, update security groups), SNS notifications with full
  finding context, Security Hub integration via BatchImportFindings, and
  multi-account coverage through Organizations delegated administrator.
  Covers suppression rules (create-filter) for known false positives,
  finding archive workflows, CloudTrail correlation for TTP chaining,
  auto-enable GuardDuty in new accounts via Lambda on CreateAccount, and
  custom threat intel upload (ThreatIntelSet / IPSet). Emits
  AUTOMATION_DEPLOYED with the full EventBridge+Lambda+SNS pipeline or
  REVIEW_REQUIRED with the specific gap. Use when building automated
  GuardDuty response, severity-based auto-remediation, multi-account
  GuardDuty automation, or integrating GuardDuty with Security Hub.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline workflow design. Live deployment
  uses aws guardduty create-filter, list-findings, get-findings,
  archive-findings, create-threat-intel-set, create-ip-set,
  aws events put-rule, put-targets, aws lambda create-function,
  aws sns create-topic, subscribe, aws securityhub batch-import-findings,
  aws organizations enable-aws-service-access, and
  aws cloudformation deploy (for multi-account StackSets) — AWS CLI v2,
  SSO or key-based credentials.
keywords:
  - Amazon GuardDuty
  - EventBridge
  - Lambda remediation
  - severity-based routing
  - EC2 isolation
  - IAM credential revocation
  - WAF IP blocking
  - SNS notification
  - AWS Security Hub
  - BatchImportFindings
  - Organizations delegated admin
  - suppression filter
  - finding archive
  - CloudTrail correlation
  - TTP chaining
  - ThreatIntelSet
  - IPSet
  - auto-enable GuardDuty
  - incident response automation
tags: [guardduty, security, eventbridge, lambda, security-hub, incident-response, automate, threat-detection]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 4
  supports_pipeline: true
  entry_point: false
  family: Security
  task_type: automate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "AUTOMATION_DEPLOYED | REVIEW_REQUIRED"
  when_to_use: >-
    Building automated response workflows for GuardDuty findings, wiring
    EventBridge to Lambda remediation functions, designing severity-based
    auto-response (Critical/High auto-isolate, Medium notify, Low log),
    configuring GuardDuty with Security Hub integration, setting up
    multi-account GuardDuty via Organizations delegated administrator,
    creating suppression filters for known false positives, uploading
    custom threat intel, or auto-enabling GuardDuty in new accounts.
  when_not_to_use: >-
    Investigating a single GuardDuty finding for root cause (use
    guardduty-finding-investigator). Triaging finding severity numerically
    without automation (use guardduty-finding-severity-triage). Config
    posture audits of GuardDuty detector enablement (use the auditor
    family). Forensic chain of custody and disk imaging belong to
    incident-response-automator. Non-GuardDuty detections (Inspector,
    Macie, Detective) use their own skills.
  activation_triggers:
    - "automate GuardDuty response"
    - "GuardDuty EventBridge Lambda"
    - "severity-based auto-remediation"
    - "isolate EC2 on GuardDuty finding"
    - "revoke IAM keys on detection"
    - "block IP in WAF from GuardDuty"
    - "GuardDuty Security Hub integration"
    - "GuardDuty suppression filter"
    - "GuardDuty multi-account automation"
    - "auto-enable GuardDuty new account"
    - "GuardDuty custom threat intel"
    - "archive GuardDuty findings"
  invocation_schema: >-
    Input: either (a) a GuardDuty finding type or family (e.g.,
    UnauthorizedAccess:EC2/SSHBruteForce) plus desired remediation actions,
    OR (b) an automation requirement ("auto-isolate EC2 on Critical
    findings", "revoke IAM keys on credential-abuse detection"). Output:
    deterministic AUTOMATION block per finding family — ROUTING/REMEDIATION/
    NOTIFICATION/INTEGRATION/SAFETY/VERDICT — where VERDICT is
    AUTOMATION_DEPLOYED (pipeline template ready) or REVIEW_REQUIRED
    (specific gap cited).
---

# GuardDuty Finding Automator

## Mindset

**One-line takeaway:** every GuardDuty automation workflow is a five-stage
pipeline — **detect** (GuardDuty finding) → **route** (EventBridge severity
filter) → **respond** (Lambda remediation) → **notify** (SNS with finding
context) → **correlate** (Security Hub + CloudTrail TTP chaining). A gap
in ANY stage produces a silent failure: the finding fires but nothing is
contained, or containment fires on a false positive and takes down a
production service.

- **Detection** without **automated routing** is noise — alert fatigue
  sets in within weeks of enablement.
- **Severity-based auto-response** is the core design decision:
  Critical/High findings trigger automatic containment, Medium notifies
  the security team, Low findings are logged for trend analysis.
- **Finding ID deduplication is non-negotiable.** GuardDuty updates the
  same finding ID when new evidence arrives. Without dedup, the Lambda
  re-isolates the same instance on every update.
- **TTP correlation across findings reveals the attack chain.** A Recon
  finding followed by UnauthorizedAccess followed by Exfiltration is a
  kill-chain, not three isolated events. Security Hub is the correlation
  layer.

## Quick navigation

| You want to... | Go to |
|---|---|
| Route findings by severity via EventBridge | Step 2 + Appendix A |
| Pick the right Lambda remediation action | Step 3 (action matrix) |
| Wire EC2 isolation (SG swap) | Step 4 |
| Revoke IAM credentials safely | Step 5 |
| Block source IPs in WAF | Step 6 |
| Send SNS notifications with finding context | Step 7 |
| Ingest as Security Hub custom finding | Step 8 |
| Set up multi-account via Organizations | Step 9 |
| Suppress known false positives | Step 10 |
| Correlate TTPs across findings via CloudTrail | Step 11 |
| Auto-enable GuardDuty in new accounts | Step 12 |
| Upload custom threat intel | Step 13 |
| Avoid common automation pitfalls | Anti-Patterns |

## Critical rules at a glance (do NOT bury these)

1. **EventBridge fires on finding occurrence AND finding update.**
   GuardDuty emits an event when a finding is first created AND on every
   subsequent update. The Lambda MUST deduplicate on finding ID.

2. **EC2 isolation via security group swap is the safest containment.**
   Replacing SGs with an isolation SG (no ingress, restricted egress) is
   reversible. Terminating destroys forensic evidence. Stopping may
   trigger auto-scaling replacement.

3. **IAM key revocation must check `AccessKeyLastUsed` first** for Medium
   severity. Revoking an active application key causes an outage. For
   Critical findings (CryptoCurrency, Backdoor), revoke regardless.

4. **`create-filter` with `FindingCriteria` suppresses silently.** An
   over-broad filter hides real threats. Always scope to specific
   resource or IP and set an expiry review date.

5. **Security Hub `BatchImportFindings` requires the ASFF format.**
   Schema mismatches produce silent drops — Security Hub does not error
   on malformed findings.

## Pre-flight: data requirements

| Input | Source | Why |
|---|---|---|
| Finding types to automate | `get-findings-statistics --group-by type` | Drives remediation action selection |
| Severity distribution | `get-findings-statistics --group-by severity` | Drives routing tier |
| Sample finding JSON | `get-findings --finding-ids <id>` | Concrete parameters for Lambda |
| EventBridge rule status | `events describe-rule` | Existing routing |
| Lambda function config | `lambda get-function-configuration` | Existing remediation functions |
| Security Hub enabled? | `securityhub describe-hub` | Integration target |
| Organizations delegated admin | `organizations list-delegated-administrators` | Multi-account setup |
| Existing suppression filters | `guardduty list-filters` | Don't overwrite blindly |
| WAF web ACL | `wafv2 list-web-acls` | IP blocking target |
| SNS topic ARN | `sns list-topics` | Notification target |

**If the input is malformed** (missing finding type, ambiguous severity),
emit:

```text
AUTOMATION: <reference>
FINDING_TYPE: <type or UNKNOWN>
VERDICT: ERROR
REASON: Cannot design automation — finding type and desired remediation action are required.
GAP: Re-supply get-findings output for the finding type and the severity-routing requirement.
```

## Process — Workflow design (apply in order)

### Step 0: Expert knowledge — non-obvious GuardDuty + EventBridge behaviors

- **EventBridge `detail.severity` may serialize as string or number**
  depending on detector version. Numeric matching rules can fail
  silently. Test with a sample event; when in doubt, route ALL findings
  to Lambda and branch internally on `detail.finding.severity`.

- **Finding IDs are stable across updates.** GuardDuty updates the
  existing finding and increments `service.eventCount`. EventBridge
  emits on every update. Track processed IDs in DynamoDB (7-day TTL).

- **`archive-findings` does NOT delete.** Archived findings remain
  queryable for 90 days. Suppression filters archive automatically but
  do not prevent EventBridge emission if applied after the initial emit.

- **Security Hub auto-enables GuardDuty as a source** when both are
  enabled in the same Region. Custom enrichment via `BatchImportFindings`
  creates a SEPARATE finding — deduplicate on finding ID to avoid dups.

- **WAF IP set limits: 10,000 IPs per set, 200 sets per ACL.** Blocking
  every GuardDuty source IP exhausts the limit within weeks. Use a
  rotating IP set (TTL eviction) or NACL-based blocking for high volume.

- **Organizations delegated admin is Region-specific.** Each Region
  requires its own designation. Deploy the pipeline via StackSets.

- **Lambda remediation timeout must be at least 60 seconds.** EC2 SG
  swap takes 10-30 seconds to propagate. The default 3-second timeout
  is insufficient.

- **Cross-account event bus routing is required for multi-account.**
  Member-account findings emit to the member's default bus. Configure
  forwarding to the delegated admin's bus.

### Step 1: Classify the finding family and severity tier

| Finding family | Example types | Default severity | Response tier |
|---|---|---|---|
| `UnauthorizedAccess:EC2` | SSHBruteForce, RDPBruteForce | Medium-High | High → isolate; Medium → notify |
| `Backdoor:EC2` | BackdoorAtTask, DriveThroughSource | High-Critical | Auto-isolate |
| `CryptoCurrency:EC2` | CryptoDomain, BitcoinTool | High-Critical | Auto-isolate + snapshot |
| `Recon:EC2` | PortProbe, PortProbeUnprotectedPort | Low-Medium | Log + trend |
| `Persistence:IAMUser` | IAMUserBackdoor, NewUserCreation | High | Auto-revoke if credential-based |
| `Exfiltration` | S3, EC2 outbound anomalies | High-Critical | Auto-isolate + snapshot |
| `Trojan:EC2` | Trojan, DrivingLicense domain | High | Auto-isolate + Malware Protection |
| `Policy:IAMUser` | RootAccess, AssumeRole anomaly | Medium-High | Notify + CloudTrail correlate |

**Severity routing matrix (the core design):**

| Severity | Auto-action | Notification | Security Hub |
|---|---|---|---|
| Critical (9.0-10.0) | Isolate EC2, revoke IAM keys, WAF block, snapshot | SNS + Page on-call | Custom finding + correlation |
| High (7.0-8.9) | Isolate EC2, revoke IAM keys (conditional) | SNS + Email security | Custom finding |
| Medium (4.0-6.9) | No auto-action | SNS email | Forwarded (native) |
| Low (0.1-3.9) | No action | Log only (CloudWatch) | Forwarded (native) |

### Step 2: Wire the EventBridge rule for severity-based routing

```bash
aws events put-rule \
  --name guardduty-critical-high-routing \
  --event-pattern '{
    "source": ["aws.guardduty"],
    "detail-type": ["GuardDuty Finding"],
    "detail": {
      "severity": [{"numeric": [">=", 7.0]}]
    }
  }'

aws events put-targets \
  --rule guardduty-critical-high-routing \
  --targets '[{
    "Id": "guardduty-remediation-lambda",
    "Arn": "arn:aws:lambda:us-east-1:111111111111:function:guardduty-auto-remediation",
    "DeadLetterConfig": {"Arn": "arn:aws:sqs:us-east-1:111111111111:guardduty-remediation-dlq"}
  }]'
```

**IMPORTANT:** test the numeric severity match. If it fails (string
serialization), route all findings to Lambda and branch internally:

```python
severity = float(event['detail']['finding']['severity'])
if severity >= 7.0:    # Critical/High — auto-respond
elif severity >= 4.0:  # Medium — notify only
else:                  # Low — log only
```

### Step 3: Map finding type to remediation action (the action matrix)

| Finding type | Action | Lambda | Reversible |
|---|---|---|---|
| `UnauthorizedAccess:EC2/SSHBruteForce` | Isolate EC2 (SG swap) | `gd-isolate-ec2` | Yes |
| `UnauthorizedAccess:EC2/RDPBruteForce` | Isolate EC2 + WAF block | `gd-isolate-ec2` + `gd-waf-block-ip` | Yes |
| `Backdoor:EC2/*` | Isolate + snapshot | `gd-isolate-ec2` + `gd-snapshot-ebs` | Partial |
| `CryptoCurrency:EC2/*` | Isolate immediately + snapshot | `gd-isolate-ec2` + `gd-snapshot-ebs` | Partial |
| `Persistence:IAMUser/*` | Revoke IAM access keys | `gd-revoke-iam-keys` | Yes |
| `Exfiltration:*` | Isolate/revoke + snapshot | Combination | Partial |
| `Trojan:EC2/*` | Isolate + Malware Protection scan | `gd-isolate-ec2` + `gd-malware-scan` | Yes |
| `Recon:*` | No auto-action — log + correlate | N/A | N/A |

For the full parameter-level mapping, see
**references/finding-types-and-remediation-actions.md**.

### Step 4: EC2 isolation via security group swap

```python
ec2 = boto3.client('ec2')
ISOLATION_SG = 'sg-isolation-forensics'

def isolate_instance(instance_id, original_sgs):
    """Swap instance SGs to isolation SG. Store originals for rollback."""
    eni = get_eni(instance_id)
    ec2.modify_network_interface_attribute(NetworkInterfaceId=eni, Groups=[ISOLATION_SG])
    store_in_dynamodb(instance_id, original_sgs)  # For rollback
```

Isolation SG (CloudFormation):

```yaml
IsolationSecurityGroup:
  Type: AWS::EC2::SecurityGroup
  Properties:
    GroupDescription: GuardDuty isolation SG — no ingress, restricted egress
    SecurityGroupIngress: []
    SecurityGroupEgress:
      - IpProtocol: tcp
        FromPort: 443
        ToPort: 443
        CidrIp: 10.0.0.0/8  # Forensics VPC endpoint only
```

**Rollback:** store original SGs in DynamoDB. Always include a rollback
Lambda — an isolated production instance is an outage until released.

### Step 5: IAM credential revocation

```python
iam = boto3.client('iam')

def revoke_access_key(user_name, access_key_id, finding_type):
    last_used = iam.get_access_key_last_used(AccessKeyId=access_key_id)
    last_used_time = last_used['AccessKeyLastUsed'].get('LastUsedDate')

    if finding_type.startswith(('CryptoCurrency', 'Backdoor')):
        iam.update_access_key(UserName=user_name, AccessKeyId=access_key_id, Status='Inactive')
        return {'action': 'revoked', 'reason': 'critical_finding'}
    elif last_used_time and (now - last_used_time).seconds < 3600:
        notify_sns(f'Key active in last hour — manual review required for {user_name}')
        return {'action': 'notified', 'reason': 'key_in_use'}
    else:
        iam.update_access_key(UserName=user_name, AccessKeyId=access_key_id, Status='Inactive')
        return {'action': 'revoked', 'reason': 'key_inactive'}
```

### Step 6: WAF / NACL IP blocking

```python
wafv2 = boto3.client('wafv2')

def block_ip_in_waf(ip_address, ip_set_arn):
    ip_entry = f'{ip_address}/32'
    current = wafv2.get_ip_set(IPSetArn=ip_set_arn)
    addresses = current['IPSet']['Addresses']
    if ip_entry not in addresses:
        addresses.append(ip_entry)
        wafv2.update_ip_set(IPSetArn=ip_set_arn, Scope='REGIONAL',
                           Addresses=addresses, LockToken=current['LockToken'])
```

**Limit management:** WAF IP sets cap at 10,000 entries. Use eviction
policy (oldest removed when full) or switch to NACL-based blocking.

### Step 7: SNS notification with finding context

```python
sns = boto3.client('sns')

def notify_finding(finding, topic_arn, page_on_call=False):
    subject = f"[GuardDuty {finding['severity']}] {finding['type']}"
    message = json.dumps({
        'FindingId': finding['id'], 'Type': finding['type'],
        'Severity': finding['severity'], 'Resource': finding['resource']['resourceType'],
        'Action': finding.get('remediation_action', 'N/A'),
        'Count': finding['service']['eventCount']
    }, indent=2)
    sns.publish(TopicArn=topic_arn, Subject=subject, Message=message,
               MessageAttributes={'page': {'DataType': 'String',
                                   'StringValue': 'true' if page_on_call else 'false'}})
```

### Step 8: Security Hub integration via BatchImportFindings

GuardDuty natively forwards to Security Hub. For custom enrichment (TTP
annotation, blast-radius, correlation), create a custom finding:

```python
securityhub = boto3.client('securityhub')

def ingest_custom_finding(gd_finding, correlation_note=None):
    custom_finding = {
        'SchemaVersion': '2018-10-08',
        'Id': f"gd-custom-{gd_finding['id']}",
        'ProductArn': f'arn:aws:securityhub:us-east-1:111111111111:product/111111111111/default',
        'GeneratorId': 'guardduty-auto-remediation',
        'AwsAccountId': gd_finding['accountId'],
        'Types': ['TTPs/' + gd_finding['type'].split('/')[0]],
        'FirstObservedAt': gd_finding['service']['eventFirstSeen'],
        'LastObservedAt': gd_finding['service']['eventLastSeen'],
        'CreatedAt': now, 'UpdatedAt': now,
        'Severity': {'Label': severity_label(gd_finding['severity'])},
        'Title': f"GuardDuty Enriched: {gd_finding['type']}",
        'Description': gd_finding['description'],
        'ProductFields': {'Correlation': correlation_note or 'standalone'}
    }
    securityhub.batch_import_findings(Findings=[custom_finding])
```

### Step 9: Multi-account via Organizations delegated administrator

```bash
# Designate delegated admin (per Region)
aws guardduty enable-organization-admin-account \
  --admin-account-id 111111111111 --region us-east-1

# Auto-enable for all member accounts
aws guardduty update-organization-configuration \
  --detector-id <detector-id> --auto-enable --region us-east-1
```

**Cross-account event forwarding** (in each member account via StackSet):

```bash
aws events put-rule --name forward-guardduty-to-admin \
  --event-pattern '{"source":["aws.guardduty"],"detail-type":["GuardDuty Finding"]}'

aws events put-targets --rule forward-guardduty-to-admin \
  --targets '[{"Id":"admin-bus","Arn":"arn:aws:events:us-east-1:111111111111:event-bus/default",
  "RoleArn":"arn:aws:iam::222222222222:role/EventBridgeForwardRole"}]'
```

### Step 10: Suppression filters for known false positives

```bash
aws guardduty create-filter \
  --detector-id <detector-id> \
  --name suppress-authorized-scanner \
  --action ARCHIVE \
  --finding-criteria '{
    "Criterion": {
      "type": {"Eq": ["Recon:EC2/PortProbeUnprotectedPort"]},
      "service.additionalInfo.remoteIpDetails.ipAddressV4": {"Eq": ["203.0.113.50"]}
    }
  }' \
  --description "Suppress port probe from scanner 203.0.113.50. REVIEW: 2026-11-01"
```

Common false-positive patterns:

| Finding type | FP source | Filter criteria |
|---|---|---|
| `Recon:EC2/PortProbe*` | Authorized scanner | `remoteIpDetails.ipAddressV4` = scanner IP |
| `UnauthorizedAccess:EC2/SSHBruteForce` | CI/CD pipeline | `remoteIpDetails.ipAddressV4` = CI NAT gateway |
| `Recon:IAMUser/*` | Break-glass access | `accessKeyDetails.accessKeyId` = break-glass key |

**Never suppress without a review date.** Add it to the description and
set a calendar reminder.

### Step 11: CloudTrail correlation for TTPs

A single finding is an event. A sequence of findings is an attack chain.

| Chain pattern | MITRE tactic | Finding sequence |
|---|---|---|
| Recon → Initial Access | TA0043 → TA0001 | `Recon:EC2/PortProbe` → `UnauthorizedAccess:EC2/SSHBruteForce` |
| Initial Access → Persistence | TA0001 → TA0003 | `UnauthorizedAccess:EC2` → `Persistence:IAMUser/NewUserCreation` |
| Persistence → Exfiltration | TA0003 → TA0010 | `Backdoor:EC2` → `Exfiltration:S3/ObjectExfiltration` |
| Impact | TA0040 | `CryptoCurrency:EC2/BitcoinTool` (single, high confidence) |

```python
def correlate_ttps(finding, dynamodb_table):
    """Check for related findings within 60-min window."""
    related_types = get_related_ttps(finding['type'])
    recent = dynamodb_table.query(
        KeyConditionExpression='resource_id = :rid',
        FilterExpression='finding_type IN :types AND #ts > :cutoff',
        ExpressionAttributeValues={':rid': finding['resource']['resourceId'],
                                   ':types': related_types,
                                   ':cutoff': (datetime.utcnow() - timedelta(minutes=60)).isoformat()})
    if recent['Items']:
        chain = [i['finding_type'] for i in recent['Items']] + [finding['type']]
        return f"TTP chain detected: {' -> '.join(chain)}"
    return None
```

### Step 12: Auto-enable GuardDuty in new accounts

Lambda on CreateAccount event (via EventBridge):

```bash
aws events put-rule --name new-org-account-guardduty \
  --event-pattern '{
    "source": ["aws.organizations"],
    "detail-type": ["AWS API Call via CloudTrail"],
    "detail": {"eventName": ["CreateAccount"]}
  }'
```

The Lambda creates detectors in all target Regions and accepts the
invitation from the delegated admin.

### Step 13: Custom threat intel upload

```bash
# Threat intel set (malicious IPs/domains)
aws guardduty create-threat-intel-set \
  --detector-id <detector-id> --name custom-malicious-ips \
  --format TXT --location s3://threat-intel-bucket/malicious-ips.txt \
  --activate --tags '{"Source":"internal","ReviewDate":"2026-11-01"}'

# Trusted IP set (allowlist — overrides threat intel)
aws guardduty create-ip-set \
  --detector-id <detector-id> --name trusted-ips \
  --format TXT --location s3://threat-intel-bucket/trusted-ips.txt \
  --activate
```

Always verify with `list-threat-intel-sets` / `list-ip-sets` that the
status is `ACTIVE`. A set created with `--no-activate` is inert.

## Output format

```text
AUTOMATION: <reference>
FINDING_TYPE: <GuardDuty finding type>
SEVERITY: <numeric> (<label>)
ROUTING:
  - EventBridge rule: <rule-name>
  - Filter: severity >= <threshold>
  - Target: Lambda <function-name> with DLQ
REMEDIATION:
  - Action: <isolate EC2 | revoke IAM keys | WAF block | snapshot | notify only>
  - Lambda: <function name + ARN>
  - Rollback: <how to reverse the action>
NOTIFICATION:
  - SNS topic: <arn>
  - Content: finding context (type, severity, resource, action taken)
  - Paging: <on-call for Critical | email for Medium | none for Low>
INTEGRATION:
  - Security Hub: <native forwarding | custom enriched finding>
  - CloudTrail correlation: <enabled | disabled>
SAFETY:
  - Finding ID deduplication: <DynamoDB | Step Functions | none>
  - False-positive suppression: <filter name + criteria>
  - Rate limiting: <Lambda concurrency cap>
AUDIT:
  - CloudTrail: ec2:ModifyNetworkInterfaceAttribute, iam:UpdateAccessKey
  - CloudWatch: Lambda invocation logs + errors
VERDICT: AUTOMATION_DEPLOYED | REVIEW_REQUIRED
GAP: <if REVIEW_REQUIRED, the specific missing piece>
TEMPLATE: <CLI snippet or YAML for the pipeline>
```

### Worked example — AUTOMATION_DEPLOYED, EC2 SSH brute force

```text
AUTOMATION_DEPLOYED: prod-guardduty-auto-response
FINDING_TYPE: UnauthorizedAccess:EC2/SSHBruteForce
SEVERITY: 7.5 (HIGH)
ROUTING:
  - EventBridge rule: guardduty-critical-high-routing
  - Filter: severity >= 7.0
  - Target: Lambda guardduty-auto-remediation (DLQ: guardduty-remediation-dlq)
REMEDIATION:
  - Action: isolate EC2 via SG swap to sg-isolation-forensics
  - Lambda: guardduty-auto-remediation
  - Rollback: restore original SGs from DynamoDB (key: instance-id)
NOTIFICATION:
  - SNS topic: arn:aws:sns:us-east-1:111111111111:guardduty-alerts
  - Content: finding type, severity, instance ID, action taken, rollback
  - Paging: on-call (Critical/High only)
INTEGRATION:
  - Security Hub: custom enriched finding (TTP: Initial Access)
  - CloudTrail correlation: enabled (60-min window)
SAFETY:
  - Finding ID deduplication: DynamoDB table guardduty-processed-findings
  - False-positive suppression: suppress-authorized-scanner (CI/CD NAT)
  - Rate limiting: Lambda concurrency cap = 10
AUDIT:
  - CloudTrail: ec2:ModifyNetworkInterfaceAttribute, lambda:InvokeFunction
  - CloudWatch: /aws/lambda/guardduty-auto-remediation
VERDICT: AUTOMATION_DEPLOYED
GAP: None
TEMPLATE:
  aws events put-rule --name guardduty-critical-high-routing --event-pattern '{"source":["aws.guardduty"],"detail-type":["GuardDuty Finding"],"detail":{"severity":[{"numeric":[">=",7.0]}]}}'
```

### Worked example — REVIEW_REQUIRED, low-severity recon

```text
AUTOMATION_DEPLOYED: prod-guardduty-auto-response
FINDING_TYPE: Recon:EC2/PortProbeUnprotectedPort
SEVERITY: 2.0 (LOW)
ROUTING: none (Low — log only tier)
REMEDIATION: none (Low — no auto-response)
NOTIFICATION: N/A (Low severity)
INTEGRATION: Security Hub native forwarding only
SAFETY: N/A (no auto-action)
VERDICT: REVIEW_REQUIRED
GAP: Low-severity recon does not warrant auto-response. Recommend: (1) create suppression filter for authorized scanner IPs (Step 10); (2) CloudWatch metric for recon trend analysis (spike detection); (3) CloudTrail correlation — a recon finding followed by a High within 60 min indicates a real attack chain.
TEMPLATE: (suppression filter — see Step 10)
```

## Anti-Patterns — NEVER do these things

- NEVER auto-isolate EC2 without a rollback path. The SG swap is
  reversible ONLY if original SGs are stored in DynamoDB. Without
  persistence, the instance is permanently quarantined — an outage.

- NEVER revoke an IAM key without checking `AccessKeyLastUsed` for
  Medium severity. The key may be the application's active credential.
  For Critical (CryptoCurrency, Backdoor), revoke unconditionally.

- NEVER set Lambda timeout to the default 3 seconds. EC2 SG swap, IAM
  API calls, and WAF updates take 5-30 seconds. Set timeout >= 60s.

- NEVER skip finding ID deduplication. GuardDuty updates the same ID as
  evidence arrives. Without dedup, the Lambda re-remediates N times.

- NEVER rely solely on EventBridge numeric severity matching. The field
  serialization is inconsistent. Route to Lambda and filter internally.

- NEVER suppress findings without an expiry review. An "authorized
  scanner" that is later compromised silently hides threats.

- NEVER block IPs in WAF without an eviction policy. WAF sets cap at
  10,000 entries. Use rotating sets or NACL-based blocking.

- NEVER configure multi-account without cross-account EventBridge
  forwarding. The delegated admin does not auto-receive member findings.

- NEVER assume `BatchImportFindings` validates schema. Malformed ASFF
  findings are silently dropped. Test with the ASFF validator first.

- NEVER terminate an EC2 instance as auto-remediation. Termination
  destroys forensic evidence. Use isolation (SG swap) + EBS snapshot.

- NEVER set Lambda concurrency to unbounded for remediation. A burst of
  findings triggers hundreds of concurrent invocations, exhausting API
  throttling. Set reserved concurrency (10-20) and use SQS as buffer.

- NEVER deploy GuardDuty automation to a single Region. Deploy via
  StackSets to every Region where GuardDuty is enabled.

- NEVER confuse `archive-findings` with deletion. Archived findings
  remain queryable for 90 days. There is no delete API.

- NEVER skip CloudTrail correlation for Medium findings. A single Recon
  at severity 2.0 is noise. The same finding followed by Credential
  Abuse at severity 8.0 within 60 min is a kill-chain.

## Pre-flight safety checks

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation:
  `CONFIRM: About to <action> for finding type <type> in account
  <account>. Proceed? (yes/no)`

- **Test the remediation Lambda against a non-production instance.**
  Use `guardduty create-sample-findings` to generate test findings.

- **Verify the isolation SG exists in every VPC.** An SG from VPC-A
  cannot apply to an instance in VPC-B.

- **Verify SNS topic subscription is confirmed.** Unconfirmed email
  subscriptions silently drop notifications. Use Lambda/HTTPS for
  critical alerts.

- **For multi-account, verify delegated admin in every target Region**
  before deploying the StackSet.

## Appendix A — EventBridge rule patterns

| Pattern | Use case |
|---|---|
| All findings | `"source":["aws.guardduty"],"detail-type":["GuardDuty Finding"]` |
| Critical/High only | Add `"detail":{"severity":[{"numeric":[">=",7.0]}]}` |
| Medium only | Add `"detail":{"severity":[{"numeric":[">=",4.0,"<",7.0]}]}` |
| Specific type | Add `"detail":{"type":["UnauthorizedAccess:EC2/SSHBruteForce"]}` |
| Specific resource | Add `"detail":{"resource":{"resourceType":["Instance"]}}` |

## Appendix B — Lambda remediation decision tree

```
Severity >= 7.0?
├─ Yes → Resource is EC2?
│       ├─ Yes → Isolate via SG swap + snapshot for forensics
│       └─ No  → IAM user? → Revoke keys (Critical: unconditional; High: check last-used)
├─ Medium → Notify via SNS + Security Hub custom finding
└─ Low → Log to CloudWatch + background CloudTrail correlation
```

## Recent AWS features (2024-2026)

- **Runtime Monitoring for ECS/EKS (2024 GA):** Runtime-level detection.
  Findings of type `Runtime/EKS/*`, `Runtime/ECS/*`. Remediation should
  isolate the task/pod, not the host.

- **Malware Protection for EBS (2024):** Automated malware scan of
  flagged volumes. Wire AFTER isolation — scan the snapshot, not the
  live volume. `THREATS_DETECTED` should page on-call.

- **EKS Protection (2024-2025):** Kubernetes API-level detection.
  Remediation: revoke K8s RBAC token or isolate pod via Lambda + EKS API.

- **Security Hub custom actions (2024):** Console-button custom actions
  triggering Lambda — analyst-initiated remediation without EventBridge.

- **EventBridge global endpoints (2024-2025):** Multi-region failover
  for event-driven remediation pipelines.

- **Organizations auto-enable enhancements (2025):** `--auto-enable`
  now covers Runtime Monitoring and Malware Protection for new accounts.

## Expert heuristic: severity-based auto-response blast radius

A single misconfigured EventBridge rule with a Lambda that auto-isolates
on all findings can quarantine every EC2 instance in an account within
minutes — including the one running the Lambda itself.

> ALWAYS test GuardDuty auto-remediation in a non-production account
> first, and scope every EventBridge rule with an explicit finding-type
> AND severity filter. Never deploy a Lambda that auto-isolates on all
> finding types against an unbounded resource population.

**Scoping techniques:**

| Technique | Mechanism | Limit |
|---|---|---|
| Finding-type filter | `detail.type` in rule | Restricts to specific families |
| Severity threshold in Lambda | Internal branch on `severity` | Low/Medium never triggers containment |
| Resource-tag scope | Check instance tags before isolating | Only `auto-remediate: enabled` |
| Account isolation | Sandbox account only | Zero production exposure |
| Lambda reserved concurrency | `--reserved-concurrent-invocations 10` | Caps simultaneous actions |

**3-phase validation:**

1. **Phase 1 — DRY (notify only):** Deploy in non-prod with NOTIFY ONLY.
   Generate test findings. Monitor 1 week.
2. **Phase 2 — CONTAINMENT in non-prod:** Enable containment. Test on
   sandbox instances. Verify rollback. Monitor for FPs.
3. **Phase 3 — DRY in prod:** Deploy to prod in NOTIFY ONLY. Monitor
   2 weeks. If < 1% FP, enable containment for Critical/High only.

**Finding ID deduplication:**

```python
# DynamoDB: guardduty-processed-findings, PK: finding_id, TTL: 7 days
def is_already_processed(finding_id, table):
    return 'Item' in table.get_item(Key={'finding_id': finding_id})
```

**Post-deploy alarms:** Lambda Errors > 0, DLQ depth > 0, GuardDuty
Critical/High count increasing without Security Hub finding (broken
pipeline). All should page on-call.

**Surface in output:** `BLAST_RADIUS: <scope>` and
`VALIDATION_STATUS: <phase-1-dry | phase-2-containment | prod-dry |
prod-containment>`. If not `prod-containment`, do NOT mark as deployable.

## Domain

AWS CloudOps / Security Automation — GuardDuty-driven detection and response.

## AWS documentation

- **Amazon GuardDuty** — https://docs.aws.amazon.com/guardduty/latest/ug/what-is-guardduty.html
- **GuardDuty EventBridge events** — https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_findings_cloudwatch.html
- **GuardDuty suppression filters** — https://docs.aws.amazon.com/guardduty/latest/ug/filters.html
- **GuardDuty Organizations** — https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_organizations.html
- **Security Hub ASFF** — https://docs.aws.amazon.com/securityhub/latest/userguide/securityhub-findings-format.html
- **GuardDuty threat intel sets** — https://docs.aws.amazon.com/guardduty/latest/ug/threat-intel-set.html
- **GuardDuty Runtime Monitoring** — https://docs.aws.amazon.com/guardduty/latest/ug/runtime-monitoring.html
- **GuardDuty Malware Protection** — https://docs.aws.amazon.com/guardduty/latest/ug/malware-protection.html
