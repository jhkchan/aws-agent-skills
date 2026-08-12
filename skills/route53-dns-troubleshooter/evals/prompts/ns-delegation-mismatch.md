# Eval prompt: ns-delegation-mismatch

Diagnose the Route 53 DNS resolution failure for the following domain.
Walk the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: `api.example.com` returns NXDOMAIN from all public resolvers.
The domain was migrated from a legacy DNS provider to Route 53 two days
ago. Records were added to the Route 53 hosted zone, but the migration
team forgot to update the NS records at the registrar.

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

The NS delegation chain is broken: the registrar points at the old
provider's NS servers, not the Route 53 hosted zone NS servers.
Verify the four-link delegation chain before diagnosing record-level
issues.
