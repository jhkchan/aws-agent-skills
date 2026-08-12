# Example usage: route53-dns-troubleshooter

A walkthrough showing the skill diagnosing an NS delegation mismatch
that mimics a missing DNS record, demonstrating the delegation-chain
triage, the authoritative-server-vs-public-resolver comparison, the
evidence-backed ROOT_CAUSE_IDENTIFIED verdict, and the registrar-side
root cause.

## Input (user prompt)

> We migrated api.example.com from our old DNS provider to Route 53
> two days ago. We added all the records to the new hosted zone, but
> the domain still returns NXDOMAIN from everywhere. We've been
> debugging this as a record issue for hours.

```text
Domain: api.example.com
HostedZoneId: Z2ABCDEFGHIJ
PrivateZone: false

Hosted zone NS records (list-resource-record-sets):
  NS: ns-1.awsdns.com, ns-2.awsdns.net,
      ns-3.awsdns.org, ns-4.awsdns.co.uk
  A (ALIAS to ALB):
    dualstack.alb-xxx.us-east-1.elb.amazonaws.com

Registrar NS (GoDaddy, via dig):
  ns-old.provider.net
  ns-old2.provider.net

dig +trace NS example.com @8.8.8.8:
  TLD delegates to ns-old.provider.net (not Route 53)

dig api.example.com @ns-1.awsdns.com +short:
  (returns the ALB IP — record IS in the zone)
```

## Skill output

```text
TARGET: api.example.com (zone Z2ABCDEFGHIJ)
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: The hosted zone NS servers are
  ns-1.awsdns.com, ns-2.awsdns.net, ns-3.awsdns.org, ns-4.awsdns.co.uk
  but the registrar (GoDaddy) has NS records pointing at
  ns-old.provider.net, ns-old2.provider.net. The TLD delegates to the
  old provider, not Route 53. The delegation chain is broken — the
  records exist in the zone but the world cannot reach them (Step 2).
LAYER: NS_DELEGATION
EVIDENCE:
  - Symptom: api.example.com returns NXDOMAIN from all public
    resolvers. The domain was migrated to Route 53 two days ago.
  - Probe: dig +trace NS example.com @8.8.8.8 shows the TLD
    (.com gtld-servers) delegating to ns-old.provider.net and
    ns-old2.provider.net — not the Route 53 NS servers.
  - Probe: aws route53 list-resource-record-sets returns NS records:
    ns-1.awsdns.com, ns-2.awsdns.net, ns-3.awsdns.org,
    ns-4.awsdns.co.uk.
  - Probe: dig api.example.com @ns-1.awsdns.com +short returns
    the ALB IP — the record IS in the zone and resolves correctly
    when querying the authoritative server directly.
  - Passing: DNSSEC is not enabled (no SERVFAIL risk); the zone is
    public (not a private-zone VPC association issue); no conflicting
    CNAME for api.example.com.
REMEDIATION:
  1. Update the registrar (GoDaddy) NS records to match the Route 53
     hosted zone NS servers:
     ns-1.awsdns.com, ns-2.awsdns.net, ns-3.awsdns.org,
     ns-4.awsdns.co.uk
     If using Route 53 Registrar:
     aws route53domains update-domain-nameservers \
       --domain-name example.com \
       --nameservers Name=ns-1.awsdns.com Name=ns-2.awsdns.net \
                     Name=ns-3.awsdns.org Name=ns-4.awsdns.co.uk \
       --profile <p>
  2. Verify after 24-48 hours (TLD TTL is typically 48 hours):
     dig NS example.com @8.8.8.8 +short
     dig api.example.com @8.8.8.8 +short
CONFIRM: Before updating NS at the registrar, emit and await:
  "CONFIRM: About to update NS delegation for example.com at GoDaddy
   to point at Route 53 NS servers. This change takes 24-48 hours to
   propagate. Proceed? (yes/no)"
```

## What the skill caught that a generic assistant misses

1. **Identified the delegation chain break, not a missing record.** A
   generic assistant says "check your records in Route 53." The skill
   recognises that the records exist in the zone (proven by
   `dig @ns-1.awsdns.com`) — the problem is that the TLD does not
   delegate to the Route 53 NS servers.

2. **Used the authoritative-server bypass to isolate the issue.** The
   skill queries the Route 53 NS server directly and confirms the
   record resolves. This proves the zone is correct and the issue is
   upstream at the delegation layer.

3. **Traced the symptom to the migration timeline.** The domain was
   migrated two days ago. The migration team added records to Route 53
   but forgot to update the registrar NS — a common migration
   oversight.

4. **Recommended the registrar-side fix, not a Route 53 fix.** The
   primary remediation is updating NS records at GoDaddy, not changing
   anything in Route 53.

5. **Set realistic propagation expectations.** TLD NS TTL is typically
   48 hours. The skill advises waiting 24-48 hours and provides
   verification commands.

## Slash-command invocation

```
/aws:troubleshoot-route53-dns
```

Or via the orchestrator:

```
/aws:pipeline
You: "diagnose why api.example.com returns NXDOMAIN after Route 53 migration"
```

The orchestrator emits
`[Phase: Troubleshoot | Skills routed: route53-dns-troubleshooter]`
and hands off to this skill for the diagnostic block.

## Live-account follow-up (optional, requires AWS CLI)

After remediating, validate the delegation:

```bash
# Confirm the registrar NS now matches the hosted zone NS
dig NS example.com @8.8.8.8 +short

# Confirm the domain resolves from a public resolver
dig api.example.com @8.8.8.8 +short

# Trace the full delegation chain
dig +trace +additional NS example.com @8.8.8.8
```

Then monitor the domain for 48 hours to confirm resolution stabilises
across all resolvers.
