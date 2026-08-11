---
description: Provision Amazon SES email infrastructure — domain identity with DNS verification (DKIM CNAME, MAIL FROM MX, SPF TXT, DMARC TXT), configuration set with event publishing (CloudWatch, SNS, Firehose, EventBridge), dedicated IP pools with warmup, email templates with Handlebars, suppression list management, and SES VPC endpoints. Wires SES v2 API and Mail Manager, and emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "amazon ses"
  - "ses v2"
  - "sesv2"
  - "domain identity ses"
  - "dkim ses"
  - "ses spf"
  - "ses dmarc"
  - "mail-from domain ses"
  - "configuration set ses"
  - "ses event publishing"
  - "ses bounce complaint"
  - "dedicated ip pool ses"
  - "ses ip warmup"
  - "ses email template"
  - "ses suppression list"
  - "ses vpc endpoint"
  - "ses mail manager"
  - "provision ses"
routes_to: ses-email-deployer
---

# /aws:deploy-ses-email

Activate the `ses-email-deployer` skill and provision Amazon SES
email infrastructure with production-grade configuration.

## What it does

The skill walks a 10-step provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Create the domain identity and generate DKIM tokens
2. Publish DKIM CNAME records in Route 53
3. Configure the MAIL FROM domain (MX + SPF for alignment)
4. Publish the DMARC record (quarantine policy)
5. Create the configuration set with event publishing
6. Create the dedicated IP pool with warmup
7. Create the email template (HTML + text, Handlebars)
8. Configure the suppression list (BOUNCE + COMPLAINT)
9. Verify production access and send a test
10. Wire VPC endpoint (optional) and Mail Manager (optional)

## When to use

- You want to create an SES domain identity with DKIM verification.
- You are configuring MAIL FROM domain, SPF alignment, or DMARC
  policy.
- You want a configuration set with event publishing to
  CloudWatch / SNS / Firehose / EventBridge.
- You want dedicated IP pools with automatic warmup.
- You want email templates with Handlebars variables.
- You want suppression list management at the account level.
- You want an SES VPC endpoint for private API access.
- You want to check for enablement blockers (domain unverified,
  DKIM not published, account in sandbox).

## How to invoke

### Slash command

```
/aws:deploy-ses-email
```

Then provide: domain name, Route 53 hosted zone ID, MAIL FROM
domain, DMARC policy stage, configuration set name, event
destinations (CloudWatch / SNS / Firehose / EventBridge),
dedicated IP pool name, IP count, warmup preference, template
name and variables, suppression list attributes, and VPC endpoint
details.

### Natural language

Any of these routes to the same skill:

- "provision ses for example.com"
- "verify my ses domain identity with dkim"
- "create a ses configuration set with event publishing"
- "set up ses dedicated ip pool with warmup"
- "create an ses email template"
- "configure ses suppression list"

### CLI routing

```bash
node cli/bin/cli.js route "deploy ses email"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps
pipeline. The output checklist feeds into verification pipelines
and downstream auditor skills (e.g., a CloudWatch alarm auditor
for bounce / complaint rate spikes).

## Example

```
You: /aws:deploy-ses-email

     Provision SES for example.com in us-east-1. DKIM signing
     enabled, MAIL FROM mail.example.com with SPF
     include:amazonses.com ~all, DMARC p=quarantine. Configuration
     set transactional-cs with CloudWatch (Campaign dimension) and
     SNS (arn:aws:sns:us-east-1:111122223333:ses-feedback) event
     destinations. Dedicated IP pool transactional-pool with 2 IPs,
     warmup enabled. Template OrderConfirmation with Handlebars.
     Suppression on BOUNCE + COMPLAINT. VPC endpoint for sesv2 in
     vpc-abcdef1234. Route 53 zone Z2ABCDEF12345.

Skill:
  DOMAIN: example.com
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓]      Domain identity — arn:aws:ses:us-east-1:111122223333:identity/example.com (Verified)
    [✓]      DKIM signing — 3 CNAME records published; SigningEnabled=true
    [✓]      MAIL FROM domain — mail.example.com (MX + SPF TXT)
    [✓]      SPF alignment — include:amazonses.com in mail.example.com TXT
    [✓]      DMARC — _dmarc.example.com TXT v=DMARC1; p=quarantine
    [✓]      Configuration set — transactional-cs with event publishing
    [✓]      Event publishing — Send, Delivery, Bounce, Complaint, Open, Click to CloudWatch + SNS
    [✓]      Bounce/complaint notifications — SNS ses-feedback
    [✓]      Dedicated IP pool — transactional-pool (2 IPs, warmup enabled)
    [✓]      IP warmup — automatic ~45-day ramp
    [✓]      Template — OrderConfirmation (HTML + text, Handlebars)
    [✓]      Suppression list — account-level BOUNCE + COMPLAINT
    [✓]      Production access — PRODUCTION (out of sandbox)
    [OPTIONAL] VPC endpoint — interface endpoint for sesv2
  VERIFICATION_COMMANDS:
    aws sesv2 get-email-identity --email-identity example.com --region us-east-1
    aws sesv2 get-dedicated-ip-pool --pool-name transactional-pool --region us-east-1
    aws sesv2 get-configuration-set --configuration-set-name transactional-cs --region us-east-1
    aws sesv2 list-email-templates --region us-east-1
    aws sesv2 get-suppression-attributes --region us-east-1
    aws ec2 describe-vpc-endpoints --service-name com.amazonaws.us-east-1.sesv2 --region us-east-1
```

## References

- Skill definition: `skills/ses-email-deployer/SKILL.md`
- Deployment CLI commands: `skills/ses-email-deployer/references/deployment-cli-commands.md`
- DNS and deliverability guide: `skills/ses-email-deployer/references/dns-and-deliverability-guide.md`
- Eval suite: `skills/ses-email-deployer/evals/evals.json`
