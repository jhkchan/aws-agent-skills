# End-to-end usage scenario: ses-email-deployer

A walkthrough showing the skill provisioning Amazon SES email
infrastructure for a transactional email workload — domain
identity with DKIM / SPF / DMARC, configuration set with event
publishing, dedicated IP pool with warmup, email template, and
VPC endpoint. This exercises Steps 1-10.

## Input (user prompt)

> Provision SES for example.com in us-east-1. DKIM signing
> enabled, MAIL FROM mail.example.com with SPF
> include:amazonses.com ~all, DMARC p=quarantine. Configuration
> set transactional-cs with CloudWatch (Campaign dimension) and
> SNS (arn:aws:sns:us-east-1:111122223333:ses-feedback) event
> destinations. Dedicated IP pool transactional-pool with 2 IPs,
> warmup enabled. Template OrderConfirmation with Handlebars
> variables. Suppression on BOUNCE + COMPLAINT. VPC endpoint for
> sesv2 in vpc-abcdef1234. Route 53 hosted zone Z2ABCDEF12345.
> Account is out of sandbox.

## Skill output

```text
DOMAIN: example.com
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓]      Domain identity — arn:aws:ses:us-east-1:111122223333:identity/example.com (Verified)
  [✓]      DKIM signing — 3 CNAME records published in Route 53; SigningEnabled=true
  [✓]      MAIL FROM domain — mail.example.com (MX + SPF TXT published)
  [✓]      SPF alignment — include:amazonses.com in mail.example.com TXT
  [✓]      DMARC — _dmarc.example.com TXT v=DMARC1; p=quarantine; rua=mailto:dmarc@example.com
  [✓]      Configuration set — transactional-cs with event publishing
  [✓]      Event publishing — Send, Delivery, Bounce, Complaint, Open, Click to CloudWatch + SNS
  [✓]      Bounce/complaint notifications — SNS topic arn:aws:sns:us-east-1:111122223333:ses-feedback
  [✓]      Dedicated IP pool — transactional-pool (2 IPs, warmup enabled)
  [✓]      IP warmup — automatic ~45-day ramp; day 1 = 100 emails / IP
  [✓]      Template — OrderConfirmation (HTML + text parts, Handlebars variables)
  [✓]      Suppression list — account-level BOUNCE + COMPLAINT
  [✓]      Production access — account PRODUCTION (out of sandbox)
  [OPTIONAL] VPC endpoint — interface endpoint for sesv2 (private DNS)
VERIFICATION_COMMANDS:
  aws sesv2 get-email-identity --email-identity example.com --region us-east-1
  aws sesv2 get-dedicated-ip-pool --pool-name transactional-pool --region us-east-1
  aws sesv2 get-configuration-set --configuration-set-name transactional-cs --region us-east-1
  aws sesv2 list-email-templates --region us-east-1
  aws sesv2 get-suppression-attributes --region us-east-1
  aws ec2 describe-vpc-endpoints --service-name com.amazonaws.us-east-1.sesv2 --region us-east-1
```

## What the skill caught that a generic assistant misses

1. **DMARC stage progression.** A generic assistant suggests
   `p=reject` on day one. The skill starts with `p=quarantine`
   and explains the escalation path.
2. **SPF soft fail vs hard fail.** A generic assistant uses
   `-all` (hard fail). The skill uses `~all` because forwarded
   mail breaks SPF and hard fail causes legitimate rejections.
3. **DKIM CNAME record naming.** A generic assistant doubles the
   `_domainkey` segment. The skill uses the correct name
   (`<token>._domainkey.example.com`) without doubling.
4. **MAIL FROM MX Region endpoint.** A generic assistant uses a
   generic endpoint. The skill uses
   `feedback-smtp.us-east-1.amazonses.com` for us-east-1.
5. **Dedicated IP warmup.** A generic assistant creates the pool
   without warmup. The skill enables automatic warmup on each IP.
6. **Configuration set association on send.** A generic assistant
   omits `--configuration-set-name`. The skill ensures the send
   call references the configuration set so events flow.
7. **Sandbox detection.** A generic assistant assumes production
   access. The skill verifies `get-account` returns
   `EnforcementStatus` = `PRODUCTION`.
8. **VPC endpoint private DNS prerequisites.** A generic assistant
   creates the endpoint without checking VPC DNS settings. The
   skill verifies `enableDnsHostnames` and `enableDnsSupport`.

## Slash-command invocation

```
/aws:deploy-ses-email
```

Or via the orchestrator:

```
/aws:pipeline
You: "provision ses for example.com with dkim spf dmarc configuration set and dedicated ip pool"
```

The orchestrator emits `[Phase: Deploy | Skills routed:
ses-email-deployer]` and hands off to this skill for the VERDICT.

## Related scenarios

The same skill handles:

- **Domain identity + DKIM + SPF + DMARC** — full DNS verification
  suite.
- **Configuration set with event publishing** — CloudWatch, SNS,
  Firehose, EventBridge destinations.
- **Dedicated IP pool with warmup** — automatic warmup ramp.
- **Email templates with Handlebars** — conditional rendering,
  loops, helpers.
- **Suppression list management** — account-level + per-address.
- **SES VPC endpoint** — private API access from VPC.
- **Mail Manager** — ingress analysis and egress rule sets.
- **Sandbox-to-production migration** — verifying production
  access and requesting it.
