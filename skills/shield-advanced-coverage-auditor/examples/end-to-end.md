# End-to-end usage scenario: shield-advanced-coverage-auditor

A walkthrough showing the skill auditing an account with three findings:
an unprotected EIP-backed EC2 instance (UNPROTECTED), a missing DRT role
(NO_DRT_ACCESS), and an ALB protection without a health check
(CONFIG_GAP). The aggregation produces UNPROTECTED, and the remediation
sequence follows the ordered principle: cover resources first, then DRT,
then detection.

## Input (user prompt)

> Audit our Shield Advanced coverage. We have a CloudFront distribution,
> an ALB, and a game-server EC2 instance with an Elastic IP. Shield
> Advanced is active.

```text
Account: 111111111111 (us-east-1)
SubscriptionState: ACTIVE

Internet-facing resource inventory:
  - CloudFront distribution d-prod1 (prod-cdn)
  - ALB arn:aws:elasticloadbalancing:us-east-1:111111111111:loadbalancer/app/prod-alb/abc
  - Elastic IP eipalloc-prod-gameserver associated with EC2 i-gameserver-01

Protections (from ListProtections):
  - ProtectionId: p-alb-001
    Name: prod-alb-protection
    ResourceArn: arn:aws:elasticloadbalancing:us-east-1:111111111111:loadbalancer/app/prod-alb/abc
    HealthCheckIds: []

DRT access (from DescribeDRTAccess):
  RoleArn: null
  LogBuckets: []

ProactiveEngagement: DISABLED
EmergencyContactList: []

WAF Web ACL associations:
  - ALB arn:...:loadbalancer/app/prod-alb/abc -> WebACLArn arn:aws:wafv2:us-east-1:111111111111:regional/webacl/prod-alb-waf/xyz
```

## Skill output

```text
SCOPE: account 111111111111 (us-east-1)
VERDICT: UNPROTECTED
REASON: Elastic IP eipalloc-prod-gameserver (EC2 i-gameserver-01) is not
in the Protections list — the game server has Shield Standard only (L3/L4)
and no Shield Advanced enhanced detection or DRT support (Step 2). The DRT
has no associated role, compounding the gap (Step 3). The ALB protection
also lacks a health check.
FINDINGS:
  - [UNPROTECTED] Elastic IP eipalloc-prod-gameserver not in Protections —
    EC2 i-gameserver-01 is behind Shield Standard only (Step 2)
  - [NO_DRT_ACCESS] DRT RoleArn absent, LogBuckets empty — DRT cannot
    create custom WAF mitigations during a live attack (Step 3)
  - [CONFIG_GAP] Protection p-alb-001 has no HealthCheckIds — L7
    application-layer detection degraded, cost-protection credits
    disqualified for this ALB (Step 4)
  - [CONFIG_GAP] Proactive engagement DISABLED, EmergencyContactList empty
    — DRT will not proactively contact you during an event (Step 5)
  - [OK] CloudFront distribution d-prod1 is auto-protected (Step 0a) — no
    Protections entry needed
  - [OK] ALB prod-alb is in Protections list (Step 2)
  - [OK] ALB prod-alb has WAF Web ACL associated (Step 6)
REMEDIATION:
  1. UNPROTECTED — Create a Protection for the Elastic IP immediately:
     aws shield create-protection --name prod-gameserver-eip \
       --resource-arn arn:aws:ec2:us-east-1:111111111111:elastic-ip/eipalloc-prod-gameserver
  2. NO_DRT_ACCESS — Create the DRT IAM role (trust policy allowing
     service-role.shield.amazonaws.com) and associate it:
     aws shield associate-drt-role --role-arn arn:aws:iam::111111111111:role/AWSShieldDRTAccessRole
  3. NO_DRT_ACCESS — Associate the DRT log bucket (ALB access logs):
     aws shield associate-drt-log-bucket --log-bucket shield-drt-alb-logs
  4. CONFIG_GAP — Associate a Route 53 health check with the ALB protection:
     aws shield associate-health-check --protection-id p-alb-001 \
       --health-check-arn arn:aws:route53:::healthcheck/hc-prod-alb
  5. CONFIG_GAP — Populate emergency contacts and enable proactive engagement:
     aws shield update-emergency-contact-list --emergency-contact-list \
       '[{"EmailAddress":"oncall@example.com","PhoneNumber":"+15551234567","ContactNotes":"24/7 NOC"}]'
     aws shield enable-proactive-engagement
```

## What the skill caught that a generic assistant misses

1. **CloudFront auto-protection.** A generic assistant may flag the
   CloudFront distribution as "not in Protections list" — a false positive.
   The skill recognises that CloudFront (and Route 53) are auto-protected
   by Shield Advanced (re:Invent 2023) and marks them OK without requiring
   a Protections entry.

2. **The EIP ARN format.** The protection for an EC2 instance uses the EIP
   allocation ARN (`arn:aws:ec2:<region>:<account>:elastic-ip/eipalloc-xxx`),
   not the EC2 instance ARN. A generic assistant might try to create a
   protection with the EC2 ARN, which Shield Advanced rejects.

3. **DRT role vs log bucket distinction.** A generic assistant lumps "DRT
   access" into one binary. The skill distinguishes missing role
   (NO_DRT_ACCESS — DRT cannot act at all) from missing log bucket only
   (CONFIG_GAP — DRT can act but is blind to log patterns). This changes
   the verdict from NO_DRT_ACCESS to CONFIG_GAP in partial-DRT cases.

4. **Cost-protection eligibility link.** The skill notes that the missing
   health check disqualifies the ALB from cost-protection credits — a
   financial consequence that a generic assistant misses entirely.

5. **Severity aggregation ordering.** The skill correctly ranks UNPROTECTED
   (resource exposed) above NO_DRT_ACCESS (DRT cannot help) above
   CONFIG_GAP (sub-optimal). A generic assistant might rank "no DRT" as
   worse than "unprotected resource," but the ordering reflects that an
   exposed resource is the more immediate risk.

## Slash-command invocation

```
/aws:audit-shield-advanced-coverage
```

Or via the orchestrator:

```
/aws:pipeline
You: "audit our Shield Advanced DDoS coverage before the game launch"
```

The orchestrator emits
`[Phase: Audit | Skills routed: shield-advanced-coverage-auditor]` and
hands off to this skill for the VERDICT.

## Live-account follow-up (optional, requires AWS CLI)

After remediating the findings, validate the coverage posture:

```bash
# Verify the EIP protection was created
aws shield list-protections --profile default | jq '.Protections[].ResourceArn'

# Confirm DRT access
aws shield describe-drt-access --profile default

# Verify proactive engagement
aws shield describe-emergency-contact-settings --profile default

# Check for recent attacks
aws shield list-attacks --profile default
```

Then monitor CloudWatch for `AWS/DDoSProtection` metrics and review the
Shield Advanced dashboard for detected events.
