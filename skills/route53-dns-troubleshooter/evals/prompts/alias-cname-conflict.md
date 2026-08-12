# Eval prompt: alias-cname-conflict

Diagnose the Route 53 record creation failure for the following domain.
Walk the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: attempting to create an A (ALIAS) record for
`api.example.com` pointing at a new ALB fails with
`ConflictingDomainExists`.

```text
Domain: api.example.com
HostedZoneId: Z6HIJKLMNOP

Change request (failed):
  Action: CREATE
  Name: api.example.com.
  Type: A
  AliasTarget:
    HostedZoneId: Z35SXDOTRQ7X7K (ALB hosted zone)
    DNSName: dualstack.alb-new.us-east-1.elb.amazonaws.com

Error:
  { "__type": "ConflictingDomainExists",
    "message": "A CNAME record already exists with the same name." }

Existing record (list-resource-record-sets):
  CNAME: api.example.com -> old-cdn.cloudfront.net (TTL 300)
```

An existing CNAME record for `api.example.com` conflicts with the new
ALIAS record. A name cannot have both a CNAME and an ALIAS (or A)
record. The CNAME must be deleted before the ALIAS can be created.
