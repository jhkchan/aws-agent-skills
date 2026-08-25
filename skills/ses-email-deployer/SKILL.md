---
name: ses-email-deployer
description: 'Provisions Amazon SES email infrastructure — domain identity with DNS verification (DKIM CNAME, MX for bounce / complaint), configuration set with event publishing (sends, deliveries, bounces, complaints, opens, clicks), dedicated IP pools with warmup, email templates (HTML / text), suppression list management, and VPC endpoint integration. Wires SES v2 API, Mail Manager ingress / egress, and emits a READY_TO_DEPLOY checklist verifying domain verification, DKIM signing, SPF / DMARC alignment, bounce / complaint notifications, and production-access state. Use when creating an SES domain identity, verifying DKIM, configuring a configuration set with event publishing, setting up dedicated IP pools, creating email templates, managing the suppression list, or wiring SES VPC endpoints. Triggers: amazon ses, sesv2, domain identity, dkim, spf, dmarc, mail-from domain, configuration set, event publishing, bounce complaint, dedicated ip pool, ip warmup, email template, suppression list, ses vpc endpoint, mail manager.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with sesv2, ses, route53, iam, and ec2 access. Works with Terraform aws_sesv2_* resources, CloudFormation AWS::SESV2::* types, and the AWS SDK sesv2 client.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: AppIntegration
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, ses, email, dkim, deploy
  dependencies: aws-orchestrator
  keywords: aws, ses, sesv2, email, dkim, spf, dmarc, configuration-set, dedicated-ip, ip-warmup, email-template, suppression-list, mail-manager, cloudops, deploy
  when_to_use: Invoke when the user wants to provision Amazon SES email infrastructure — domain identity with DNS verification (DKIM CNAME, MX for bounce / complaint feedback), email address identity, configuration set with event publishing (sends, deliveries, bounces, complaints, opens, clicks), dedicated IP pools with warmup, email templates (HTML / text), suppression list management, or SES VPC endpoints. Use for SES v2 API provisioning, Mail Manager ingress / egress, SPF / DMARC alignment, and production-access request workflow. Do NOT invoke for SNS topic provisioning (sns-topic-deployer), for Lambda-based email processing (lambda-function-deployer), for Route 53 record management outside SES verification (route53-routing-policy-deployer), or for Pinpoint campaign management (pinpoint-campaign-deployer).
---

# SES Email Deployer

An AWS CloudOps agent skill that provisions Amazon SES email
infrastructure with the correct production defaults — domain
identity with DNS verification, DKIM signing, SPF / DMARC
alignment, configuration set with event publishing, dedicated IP
pools with warmup, email templates, suppression list management,
and VPC endpoint integration. Emits a READY_TO_DEPLOY checklist
verifying every prerequisite.

## Quick navigation

| Need | Section |
|---|---|
| What MUST be in the response | "STRICT output contract" |
| Why the provisioning order matters | "Reasoning framework" |
| What to verify before sending | "Prerequisites" |
| The ordered provisioning steps | "Deployment procedure" |
| Common silent-failure pitfalls | "NEVER" |
| Domain identity, DKIM, SPF, DMARC | "Deployment procedure" Steps 1-3 |
| Configuration set, event publishing, IP pools | "Deployment procedure" Steps 4-6 |
| Templates, suppression list, VPC endpoints | "Deployment procedure" Steps 7-9 |
| Mail Manager, SES v2 API | "Deployment procedure" Step 10 |
| 2024-2026 feature changes | "Recent AWS features" |
| Deep CLI sequences | `references/deployment-cli-commands.md` |
| DNS records, DMARC, warmup schedules | `references/dns-and-deliverability-guide.md` |

## STRICT output contract

When this skill is invoked with an SES provisioning request
(domain identity, configuration set, dedicated IP pool, template,
suppression list, VPC endpoint, or a partial existing
configuration), the agent MUST respond with the READY_TO_DEPLOY
checklist defined in "Output format" using the literal all-caps
labels `DOMAIN:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with
prose, headings, or disclaimers — emit the block as the first
lines of the response.

### Required output structure

1. `DOMAIN: <domain-name>` — the sending domain.
2. `VERDICT: READY_TO_DEPLOY` OR `VERDICT: PREREQUISITES_MISSING`.
3. `CHECKLIST:` followed by indented lines with status markers
   (`[✓]`, `[✗]`, `[OPTIONAL]`, `[INPUT NEEDED]`).
4. `VERIFICATION_COMMANDS:` followed by indented `aws ...` commands.

### FORBIDDEN output patterns

- **No prose preamble before `DOMAIN:`** — the first non-empty
  line MUST be `DOMAIN:`.
- **No markdown variants of labels** — write `VERDICT:`, not
  `**VERDICT:**`, `### Verdict`, `Verdict =`, or `` `VERDICT` ``.
- **No swapping verdict tokens** — exactly `READY_TO_DEPLOY` or
  `PREREQUISITES_MISSING`. Not "ready", "missing", "BLOCKED", "OK".
- **No omitting `VERIFICATION_COMMANDS:`** — include even when
  PREREQUISITES_MISSING; the operator needs commands to verify
  gaps.
- **No extra sections after `VERIFICATION_COMMANDS:`** — the
  checklist block is the entire response. Put deeper explanation
  in `references/`.
- **No status marker drift** — use only `[✓]`, `[✗]`, `[OPTIONAL]`,
  `[INPUT NEEDED]`. Do not invent `[?]`, `[!]`, `[WARN]`, or emoji.

### Perfect example (copy the shape exactly)

```text
DOMAIN: example.com
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓]      Domain identity — arn:aws:ses:us-east-1:111122223333:identity/example.com (Verified)
  [✓]      DKIM signing — 3 CNAME records published in Route 53; SigningEnabled=true
  [✓]      MAIL FROM domain — mail.example.com (MX + SPF TXT published)
  [✓]      SPF alignment — include:amazonses.com in mail.example.com TXT
  [✓]      DMARC — _dmarc.example.com TXT v=DMARC1; p=quarantine; rua=mailto:dmarc@example.com
  [✓]      Configuration set — transactional-cs with event publishing to CloudWatch + SNS + Firehose
  [✓]      Event publishing — Send, Delivery, Bounce, Complaint, Open, Click
  [✓]      Bounce/complaint notifications — SNS topic arn:aws:sns:us-east-1:111122223333:ses-feedback
  [✓]      Dedicated IP pool — transactional-pool (2 IPs, warmup enabled)
  [✓]      IP warmup — 1-day-per-stage automatic warmup; day 1 = 100 emails / IP
  [✓]      Template — OrderConfirmation (HTML + text parts, fallback subject)
  [✓]      Suppression list — account-level enabled; suppressOnBounce=true, suppressOnComplaint=true
  [✓]      Production access — account out of sandbox (max 65536 emails/sec)
  [OPTIONAL] VPC endpoint — interface endpoint for sesv2 (private DNS)
  [OPTIONAL] Mail Manager — ingress analysis + egress rule set
VERIFICATION_COMMANDS:
  aws sesv2 get-email-identity --email-identity example.com --region us-east-1
  aws sesv2 get-dedicated-ip-pool --pool-name transactional-pool --region us-east-1
  aws sesv2 get-configuration-set --configuration-set-name transactional-cs --region us-east-1
  aws sesv2 list-email-templates --region us-east-1
  aws sesv2 get-suppression-attributes --region us-east-1
  aws ec2 describe-vpc-endpoints --service-name com.amazonaws.us-east-1.sesv2 --region us-east-1
```

## Reasoning framework (why the provisioning order matters)

SES provisioning has **dependency and ordering constraints**.
Skipping or misordering causes silent failures — email goes to
spam, DKIM fails verification, bounces never reach SNS, or the
account is throttled at sandbox limits:

1. **Domain identity FIRST** — `sesv2 create-email-identity`
   provisions the identity and generates DKIM tokens. Every
   downstream config references the verified identity.
2. **DKIM tokens require DNS publication** — SES generates 3 CNAME
   tokens; they MUST be published before `VerificationStatus`
   flips to `Success`. Unpublished tokens leave the identity in
   `Pending` state.
3. **MAIL FROM domain requires MX + SPF** — the custom MAIL FROM
   domain needs an MX record pointing at the SES feedback
   endpoint and an SPF TXT record with
   `v=spf1 include:amazonses.com ~all`. Without both, SPF
   alignment fails and inbox providers mark mail as spam.
4. **DMARC policy published by the domain owner** — DMARC is a
   TXT record at `_dmarc.example.com`. SES does not manage DMARC;
   the operator publishes it. The skill verifies alignment.
5. **Configuration set declares event destinations** — create it
   BEFORE associating with sends. Event destinations (CloudWatch,
   SNS, Firehose, EventBridge) are attached to the set.
6. **Dedicated IP pools need warmup** — new dedicated IPs have
   zero reputation. SES automatic warmup ramps volume over ~45
   days. Skipping warmup causes throttling or rejection.
7. **Templates registered before send** — `send-email` references
   the template by name. Creating the template after the send
   call returns `TemplateDoesNotExist`.
8. **Production access is a separate request** — new SES accounts
   are in the sandbox (verified addresses only, 1 email/sec).
   The operator must request production access via the SES
   console. The skill verifies the account is out of sandbox.

## Prerequisites (verify before deployment)

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| **Domain ownership or DNS access** | DKIM CNAME, MAIL FROM MX, SPF TXT, DMARC TXT must be published. | `aws route53 list-resource-record-sets --hosted-zone-id <id>` |
| **SES account out of sandbox** | Sandbox limits sends to verified addresses at 1/sec. | `aws sesv2 get-account --region <r>` (`EnforcementStatus` = `PRODUCTION`) |
| **Route 53 hosted zone (or third-party DNS)** | DNS records for verification. Route 53 is simplest. | `aws route53 list-hosted-zones` |
| **IAM permissions for caller** | Needs `sesv2:CreateEmailIdentity`, `sesv2:CreateConfigurationSet`, `sesv2:CreateDedicatedIpPool`, `sesv2:CreateEmailTemplate`, `route53:ChangeResourceRecordSets`. | `aws sts get-caller-identity` |
| **SNS topic for bounce / complaint feedback** (optional) | Required for real-time bounce / complaint processing. | `aws sns list-topics` |
| **CloudWatch / Firehose for event publishing** (optional) | Event destinations for the configuration set. | `aws logs describe-log-groups`, `aws firehose list-delivery-streams` |
| **Dedicated IP quota** (optional) | Dedicated IPs require service quota increase (default is 0). | `aws service-quotas get-service-quota --service-code ses --quota-code L-1BCE5A11` |
| **VPC for SES VPC endpoint** (optional) | Required for private SES API access. | `aws ec2 describe-vpcs` |

## Deployment procedure (apply in order)

### Step 1: Create the domain identity and generate DKIM tokens

The domain identity is the sending domain. SES generates 3 DKIM
CNAME tokens at creation time.

```bash
aws sesv2 create-email-identity \
  --email-identity example.com \
  --dkim-signing-attributes '{"SigningEnabled": true}' \
  --region us-east-1
```

The response returns `DkimTokens` — 3 tokens. Each maps to a
CNAME record in Route 53.

### Step 2: Publish DKIM CNAME records in Route 53

Publish the 3 CNAME records. The record name is the token; the
value is the SES DKIM endpoint.

```bash
HOSTED_ZONE_ID=$(aws route53 list-hosted-zones \
  --query "HostedZones[?Name=='example.com.'].Id" \
  --output text | cut -d'/' -f2)

cat > /tmp/dkim-change.json <<'EOF'
{
  "Changes": [
    {"Action": "CREATE", "ResourceRecordSet": {"Name": "abc123._domainkey.example.com", "Type": "CNAME", "TTL": 1800, "ResourceRecords": [{"Value": "abc123.dkim.amazonses.com"}]}},
    {"Action": "CREATE", "ResourceRecordSet": {"Name": "def456._domainkey.example.com", "Type": "CNAME", "TTL": 1800, "ResourceRecords": [{"Value": "def456.dkim.amazonses.com"}]}},
    {"Action": "CREATE", "ResourceRecordSet": {"Name": "ghi789._domainkey.example.com", "Type": "CNAME", "TTL": 1800, "ResourceRecords": [{"Value": "ghi789.dkim.amazonses.com"}]}}
  ]
}
EOF

aws route53 change-resource-record-sets \
  --hosted-zone-id $HOSTED_ZONE_ID \
  --change-batch file:///tmp/dkim-change.json
```

SES polls the records; `VerificationStatus` flips to `Success`
once all 3 are resolvable (1-15 minutes). Verify:

```bash
aws sesv2 get-email-identity --email-identity example.com --region us-east-1
```

### Step 3: Configure the MAIL FROM domain (SPF alignment)

→ Moved to [references/deployment-cli-commands.md](references/deployment-cli-commands.md#step-3-configure-the-mail-from-domain-spf-alignment) — put-email-identity-mail-from-domain + Route 53 MX / SPF TXT change batch.
Load that reference on demand before executing this section.

### Step 4: Publish the DMARC record

→ Moved to [references/deployment-cli-commands.md](references/deployment-cli-commands.md#step-4-publish-the-dmarc-record) — _dmarc TXT change batch and p=quarantine to p=reject escalation.
Load that reference on demand before executing this section.

### Step 5: Create the configuration set with event publishing

→ Moved to [references/deployment-cli-commands.md](references/deployment-cli-commands.md#step-5-create-the-configuration-set-with-event-publishing) — create-configuration-set + CloudWatch and SNS event destinations, MatchingEventTypes.
Load that reference on demand before executing this section.

### Step 6: Create the dedicated IP pool with warmup

Dedicated IPs give you a fixed sender reputation. New IPs require
warmup to build reputation with inbox providers.

```bash
aws sesv2 create-dedicated-ip-pool \
  --pool-name transactional-pool \
  --region us-east-1

# Associate dedicated IPs (requires quota approval)
aws sesv2 put-dedicated-ip-warmup-attributes \
  --ip 10.0.0.1 \
  --warmup-enabled \
  --region us-east-1

# Assign the pool to the configuration set
aws sesv2 put-configuration-set-delivery-options \
  --configuration-set-name transactional-cs \
  --sending-pool-name transactional-pool \
  --region us-east-1
```

Automatic warmup ramps volume over ~45 days: day 1 = 100 emails /
IP, doubling each day until the target volume is reached. Do NOT
disable warmup on a new IP — inbox providers will throttle or
reject.

### Step 7: Create the email template

Templates store the HTML and text parts. The `send-email` API
references the template by name.

```bash
cat > /tmp/template.json <<'EOF'
{
  "TemplateName": "OrderConfirmation",
  "TemplateContent": {
    "Subject": "Your order #{{orderNumber}} is confirmed",
    "Html": "<html><body><h1>Order {{orderNumber}}</h1><p>Total: {{total}}</p></body></html>",
    "Text": "Order {{orderNumber}}\nTotal: {{total}}"
  }
}
EOF

aws sesv2 create-email-template \
  --cli-input-json file:///tmp/template.json \
  --region us-east-1
```

Template variables use `{{varName}}` Handlebars syntax. Always
provide a text fallback for email clients that do not render
HTML.

### Step 8: Configure the suppression list

The account-level suppression list prevents sending to addresses
that previously bounced or generated complaints.

```bash
aws sesv2 put-suppression-attributes \
  --suppressed-attributes BOUNCE COMPLAINT \
  --region us-east-1
```

`BOUNCE` suppresses addresses that bounced; `COMPLAINT` suppresses
addresses that filed a complaint. Both are recommended for
production. To add specific addresses manually:

```bash
aws sesv2 put-suppressed-destination \
  --email-address spamtrap@example.com \
  --reason COMPLAINT \
  --region us-east-1
```

### Step 9: Verify production access and send a test

Verify the account is out of the sandbox (production access
granted):

```bash
aws sesv2 get-account --region us-east-1
```

`EnforcementStatus` should be `PRODUCTION`. If still in sandbox,
request production access via the SES console (Account dashboard
→ "Request production access"). Send a test email using the
template and configuration set:

```bash
aws sesv2 send-email \
  --from-email-address noreply@example.com \
  --destination '{"ToAddresses": ["recipient@example.com"]}' \
  --content '{"Template": {"TemplateName": "OrderConfirmation", "TemplateData": "{\"orderNumber\": \"12345\", \"total\": \"$99.00\"}"}}' \
  --configuration-set-name transactional-cs \
  --region us-east-1
```

Verify events flow to CloudWatch and SNS within 1 minute of the
send.

### Step 10: Wire VPC endpoint (optional) and Mail Manager (optional)

For private SES API access from a VPC (no internet egress), create
an interface VPC endpoint:

```bash
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-abcdef1234 \
  --service-name com.amazonaws.us-east-1.sesv2 \
  --subnet-ids subnet-aaa subnet-bbb \
  --security-group-ids sg-mail-sender \
  --vpc-endpoint-type Interface \
  --private-dns-enabled \
  --region us-east-1
```

For Mail Manager (ingress analysis and egress rule sets):

```bash
aws sesv2 create-email-traffic-policy \
  --policy-name transactional-egress \
  --policy-statements '[{"Conditions": {...}, "Actions": {...}}]' \
  --region us-east-1
```

Mail Manager inspects inbound email, applies filtering rules, and
routes to workloads or mailboxes. It is distinct from the SES
sending pipeline.

## Resource-type matrix

| Resource | SES v2 API | Terraform |
|---|---|---|
| Domain identity | `create-email-identity` | `aws_sesv2_email_identity` |
| DKIM tokens | `get-email-identity` (DkimAttributes) | `aws_sesv2_email_identity_dkim_signing_attributes` |
| MAIL FROM domain | `put-email-identity-mail-from-domain` | `aws_sesv2_email_identity_mail_from` |
| Configuration set | `create-configuration-set` | `aws_sesv2_configuration_set` |
| Event destination | `create-configuration-set-event-destination` | `aws_sesv2_configuration_set_event_destination` |
| Dedicated IP pool | `create-dedicated-ip-pool` | `aws_sesv2_dedicated_ip_pool` |
| Email template | `create-email-template` | `aws_sesv2_email_template` |
| Suppression list | `put-suppression-attributes` | `aws_sesv2_account_suppression_attributes` |
| VPC endpoint | `ec2 create-vpc-endpoint` | `aws_vpc_endpoint` |

## Edge-case handling

→ Moved to [references/advanced-patterns.md](references/advanced-patterns.md#edge-case-handling) — 10-item edge-case catalog (Pending identity, DKIM doubling, SPF/DMARC misalignment, throttling, VPC DNS).
Load that reference on demand before executing this section.

## Recent AWS features (2024-2026)

→ Moved to [references/advanced-patterns.md](references/advanced-patterns.md#recent-aws-features-2024-2026) — Mail Manager, sesv2 VPC endpoints, VDM, warmup enhancements, EventBridge destination, v2-as-canonical.
Load that reference on demand before executing this section.

## NEVER (top 5 — full list in references)

- NEVER send from an unverified domain identity. SES rejects with
  `MessageRejected`. Verify (`Pending` → `Success`) before sending.
- NEVER disable dedicated IP warmup on a new IP. Inbox providers
  throttle or reject email from IPs with no reputation history.
  Let automatic warmup run the full ~45-day cycle.
- NEVER use `-all` (hard fail) in the SPF record for the MAIL FROM
  domain. Forwarded mail fails SPF and may be rejected. Use `~all`.
- NEVER omit `--configuration-set-name` on the send call if you
  need event publishing. Without the configuration set, no events
  flow to CloudWatch / SNS / Firehose / EventBridge, and bounces
  do not trigger suppression.
- NEVER publish DMARC `p=reject` on day one. Start with `p=none`
  (monitor), verify alignment via aggregate reports, escalate to
  `p=quarantine`, then `p=reject` after 2-4 weeks of clean reports.

## Expert heuristic — designing SES infrastructure

→ Moved to [references/advanced-patterns.md](references/advanced-patterns.md#expert-heuristic--designing-ses-infrastructure) — seven design heuristics (per-workload config sets, dedicated-IP thresholds, MAIL FROM, DMARC staging).
Load that reference on demand before executing this section.

## Pre-flight safety checks (run before any SES CLI)

→ Moved to [references/diagnostic-commands.md](references/diagnostic-commands.md#pre-flight-safety-checks-run-before-any-ses-cli) — sandbox / DNS / quota / SNS / IAM / VPC DNS pre-flight gate.
Load that reference on demand before executing this section.

## Output format — MANDATORY literal labels

When invoked with an SES provisioning request, your ENTIRE
response MUST be the checklist block below. The labels are
**case-sensitive all-caps keywords** — write them EXACTLY as
shown. Do NOT write a preamble. Start with `DOMAIN:` and stop
after the `VERIFICATION_COMMANDS:` block.

```text
DOMAIN: <domain-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓]      Domain identity — <identity-arn> (Verified | Pending)
  [✓]      DKIM signing — <3 CNAME records published>; SigningEnabled=true
  [✓]      MAIL FROM domain — <mail-from-domain> (MX + SPF TXT published)
  [✓]      SPF alignment — include:amazonses.com in <mail-from-domain> TXT
  [✓]      DMARC — _dmarc.<domain> TXT <policy>
  [✓]      Configuration set — <name> with event publishing
  [✓]      Event publishing — <event-types> to <destinations>
  [✓]      Bounce/complaint notifications — SNS topic <topic-arn>
  [✓]      Dedicated IP pool — <pool-name> (<N> IPs, warmup <enabled|disabled>)
  [✓]      IP warmup — <schedule>
  [✓]      Template — <template-name> (HTML + text parts)
  [✓]      Suppression list — account-level <BOUNCE|COMPLAINT|both>
  [✓]      Production access — account <PRODUCTION|SANDBOX>
  [OPTIONAL] VPC endpoint — interface endpoint for sesv2 (private DNS)
  [OPTIONAL] Mail Manager — ingress analysis + egress rule set
VERIFICATION_COMMANDS:
  aws sesv2 get-email-identity --email-identity <domain> --region <region>
  aws sesv2 get-dedicated-ip-pool --pool-name <pool-name> --region <region>
  aws sesv2 get-configuration-set --configuration-set-name <name> --region <region>
  aws sesv2 list-email-templates --region <region>
  aws sesv2 get-suppression-attributes --region <region>
  aws ec2 describe-vpc-endpoints --service-name com.amazonaws.<region>.sesv2 --region <region>
```

**Status marker semantics:**
- `[✓]` — applied and verified.
- `[✗]` — NOT applied or misconfigured. Cite the gap.
- `[OPTIONAL]` — recommended but not required for the workload.
- `[INPUT NEEDED]` — prerequisite value missing; operator must
  provide.

**PREREQUISITES_MISSING verdict:** if any REQUIRED prerequisite
is missing (domain identity not verified, DKIM records not
published, account in sandbox, SPF / DMARC records missing), the
verdict is `PREREQUISITES_MISSING` with each gap listed and a
`REMEDIATION:` line per gap.


## References (load on demand)

- [references/deployment-cli-commands.md](references/deployment-cli-commands.md) — full copy-pasteable CLI sequence for all 10 provisioning steps (incl. Step 3 MAIL FROM, Step 4 DMARC, Step 5 configuration set + event destinations), Terraform equivalents, per-Region MX endpoints.
- [references/dns-and-deliverability-guide.md](references/dns-and-deliverability-guide.md) — DKIM CNAME layout, MAIL FROM MX + SPF per Region, DMARC policy stages, dedicated IP warmup schedule, full NEVER list, extended edge cases.
- [references/advanced-patterns.md](references/advanced-patterns.md) — edge-case catalog, expert heuristic for designing SES infrastructure, recent AWS features (2024-2026).
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — pre-flight safety checks to run before any SES CLI.

## Domain

AWS CloudOps / Email Infrastructure Provisioning.

## AWS documentation

- **Amazon SES Developer Guide** — https://docs.aws.amazon.com/ses/latest/dg/Welcome.html
- **SES v2 API reference** — https://docs.aws.amazon.com/ses/latest/APIReference-V2/
- **Verifying a domain identity + DKIM** — https://docs.aws.amazon.com/ses/latest/dg/creating-identities.html
- **MAIL FROM domain** — https://docs.aws.amazon.com/ses/latest/dg/mail-from.html
- **Configuration sets + event publishing** — https://docs.aws.amazon.com/ses/latest/dg/using-configuration-sets.html
- **Dedicated IP pools + warmup** — https://docs.aws.amazon.com/ses/latest/dg/dedicated-ip.html
- **SES VPC endpoints** — https://docs.aws.amazon.com/ses/latest/dg/vpc-endpoints.html
- **Mail Manager** — https://docs.aws.amazon.com/ses/latest/dg/mail-manager.html

## References

- `references/deployment-cli-commands.md` — full copy-pasteable
  CLI command sequence for all 10 provisioning steps, Terraform
  equivalents, CloudFormation snippets, and per-Region MX record
  endpoints.

- `references/dns-and-deliverability-guide.md` — deep reference
  on DKIM CNAME layout, MAIL FROM MX + SPF per Region, DMARC
  policy stages, dedicated IP warmup schedule, full NEVER list,
  and edge-case handling.
