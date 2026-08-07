# Eval prompt: phz-cross-account-no-association

Diagnose the DNS resolution failure for the following scenario. Walk
the OSI-aligned diagnostic tree (focusing on Layer 7 DNS) and emit the
standard diagnostic block (TARGET, VERDICT, REASON, LAYER, EVIDENCE,
REMEDIATION).

Symptom: application on `i-app` in `vpc-consumer` (account
222222222222, us-east-1) cannot resolve
`db.corp.example.internal`. `dig` returns NXDOMAIN. The same hostname
resolves correctly from `i-app-source` in `vpc-source-owner` (account
111111111111, us-east-1).

```text
VPC peering: pcx-aaa between vpc-consumer and vpc-source-owner,
status Active. Routes both ways.

Route 53 hosted zone:
  - Hosted zone Z111 in account 111111111111 for
    corp.example.internal (private)
  - Associated VPCs: only vpc-source-owner (account 111111111111)
  - vpc-consumer is NOT associated with the hosted zone

Resolver rules in account 222222222222:
  - Default SYSTEM rule (.) → AmazonProvidedDNS
  - No FORWARD rule for corp.example.internal

VPC DNS settings (both VPCs):
  - enableDnsSupport: true
  - enableDnsHostnames: true

Peering DNS flag:
  - AllowDnsResolutionFromRemoteVpcDomainName: true on both sides

The hostname db.corp.example.internal only exists as a Route 53
record in the private hosted zone Z111.
```

The DNS settings on both VPCs are correct, the peering DNS flag is
true, but the private hosted zone is not associated with the consumer
VPC. Route 53 PHZ associations are per-VPC and per-account; peering
does not propagate PHZ associations to the peer VPC.
