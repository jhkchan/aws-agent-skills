# End-to-end usage scenario: vpc-lattice-auth-auditor

A walkthrough showing the skill auditing a VPC Lattice service network that
has a public wildcard Invoke grant (PUBLIC_SERVICE_NETWORK) and an IP target
group routing to an external address (CONFIG_GAP), demonstrating verdict
aggregation, the default-open concept, and the assume-breach remediation
workflow.

## Input (user prompt)

> Review this VPC Lattice service network before we go to production.
> It serves our payments API across two VPCs.

```text
Service network id: sn-prod-payments-001
Service network ARN: arn:aws:vpc-lattice:us-east-1:111111111111:servicenetwork/sn-prod-payments-001
Owning account: 111111111111

Auth policy state: ACTIVE

Auth policy:
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "OpenAccess",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "vpc-lattice:*",
      "Resource": "*"
    }
  ]
}

VPC associations:
  - vpc-prod-east (cidr: 10.0.0.0/16, security-group: sg-prod-east)
  - vpc-prod-west (cidr: 10.1.0.0/16, security-group: sg-prod-west)

Services:
  - svc-payments-api (protocol HTTPS, port 443)
  - svc-payments-webhook (protocol HTTPS, port 8443)

Target groups:
  - tg-payments-primary: type INSTANCE, targets [i-prod-001, i-prod-002] in vpc-prod-east
  - tg-payments-dr: type IP, targets [203.0.113.50, 203.0.113.51]

RAM resource shares: none
```

## Skill output

```text
SERVICE NETWORK: sn-prod-payments-001
VERDICT: PUBLIC_SERVICE_NETWORK
REASON: Auth policy Statement "OpenAccess" grants vpc-lattice:* to
Principal "*" with no restrictive condition — any AWS principal can invoke
every service in the network (Rule 5a). Additionally, target group
tg-payments-dr has IP targets (203.0.113.50, 203.0.113.51) outside the
associated VPC CIDRs (10.0.0.0/16, 10.1.0.0/16).
FINDINGS:
  - [PUBLIC_SERVICE_NETWORK] Principal: "*" + vpc-lattice:* + no condition
    (Rule 5a) — any AWS principal with a route to the Lattice endpoint can
    invoke svc-payments-api and svc-payments-webhook
  - [CONFIG_GAP] IP target group tg-payments-dr has targets 203.0.113.50,
    203.0.113.51 outside VPC CIDRs 10.0.0.0/16 and 10.1.0.0/16 (Step 6) —
    potential data-exfiltration path or routing black hole if these are not
    intentional on-premises endpoints
  - [OK] Auth policy is present (not default-open NO_AUTH_POLICY)
REMEDIATION:
  1. PUBLIC_SERVICE_NETWORK — Replace Principal: "*" with specific same-
     account role ARNs (e.g., arn:aws:iam::111111111111:role/payments-api-role).
     Add aws:SourceVpc condition to scope invocation to vpc-prod-east and
     vpc-prod-west.
  2. PUBLIC_SERVICE_NETWORK — Audit CloudTrail for vpc-lattice:Invoke events
     from unexpected principals during the exposure window. The payments API
     may have been callable by any AWS principal.
  3. CONFIG_GAP — Verify 203.0.113.50 and 203.0.113.51 are intentional
     on-premises endpoints reachable via Direct Connect. If unintentional,
     remove them: aws vpc-lattice deregister-targets --target-group-identifier
     tg-payments-dr --targets 203.0.113.50,203.0.113.51
  4. Back up the current auth policy before changes:
     aws vpc-lattice get-auth-policy --resource-arn
     arn:aws:vpc-lattice:us-east-1:111111111111:servicenetwork/sn-prod-payments-001
     --output json > /tmp/sn-prod-payments-001-backup.json
```

## What the skill caught that a generic assistant misses

1. **The default-open trap is NOT triggered here — but noted as OK.** The
   auth policy EXISTS (state: ACTIVE), so this is not NO_AUTH_POLICY. A
   generic assistant might confuse "auth policy present" with "auth policy
   secure." The skill evaluates the policy CONTENT, not just its presence.

2. **Principal: "*" + vpc-lattice:* is PUBLIC_SERVICE_NETWORK, not "broad
   access."** The skill explains that any AWS principal with a route to
   the Lattice endpoint can invoke the payments API. This is total
   service-call exposure — every endpoint, every method.

3. **IP targets outside the VPC CIDR are a separate finding (CONFIG_GAP).**
   A generic assistant sees "IP target group" and moves on. The skill flags
   targets 203.0.113.50 and 203.0.113.51 as outside both associated VPC
   CIDRs — a potential exfiltration path or routing black hole.

4. **Verdict aggregation with per-finding breakdown.** The verdict is
   PUBLIC_SERVICE_NETWORK (worst finding), but the FINDINGS list shows the
   individual severities. The IP target finding is CONFIG_GAP, and the auth
   policy presence is OK (better than NO_AUTH_POLICY).

## Slash-command invocation

```
/aws:audit-vpc-lattice-auth
```

Or via the orchestrator:

```
/aws:pipeline
You: "audit this VPC Lattice service network before production"
```

The orchestrator emits
`[Phase: Audit | Skills routed: vpc-lattice-auth-auditor]` and hands off
to this skill for the VERDICT.

## Live-account follow-up (optional, requires AWS CLI)

After remediating the policy, validate the service network posture:

```bash
# Verify the auth policy was updated
aws vpc-lattice get-auth-policy \
  --resource-arn arn:aws:vpc-lattice:us-east-1:111111111111:servicenetwork/sn-prod-payments-001 \
  --profile default --output json | jq '.Statement[] | .Principal'

# List all services to check for service-level auth policy overrides
aws vpc-lattice list-services \
  --service-network-identifier sn-prod-payments-001 \
  --profile default --output json

# Check RAM resource shares
aws ram list-resources \
  --resource-owner SELF \
  --resource-arn arn:aws:vpc-lattice:us-east-1:111111111111:servicenetwork/sn-prod-payments-001 \
  --profile default
```

Then monitor CloudTrail for `vpc-lattice:Invoke` events from unexpected
principals for 1-2 weeks.
