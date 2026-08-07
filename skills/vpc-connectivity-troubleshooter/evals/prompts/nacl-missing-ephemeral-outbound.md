# Eval prompt: nacl-missing-ephemeral-outbound

Diagnose the VPC connectivity failure for the following source-destination
pair. Walk the OSI-aligned diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: application on `i-web-client` (private IP 10.0.10.10, subnet
subnet-web, SG sg-web, VPC vpc-app 10.0.0.0/16) cannot reach
`i-api-server` (private IP 10.0.20.10, subnet subnet-api, SG sg-api,
same VPC) on tcp/443. `nc -vz 10.0.20.10 443` hangs and times out.

```text
Same-VPC routing: route table for subnet-web has local route to
10.0.0.0/16. subnet-api route table has local route to 10.0.0.0/16.

SG sg-api inbound: tcp/443 from 10.0.0.0/16 (allow).
SG sg-web egress: allow all.

NACL acl-web (subnet-web): default (allow all in and out).
NACL acl-api (subnet-api): custom NACL with rules:
  - Inbound rule 100: tcp/443 from 10.0.0.0/8 (allow)
  - Outbound rule 100: tcp/443 to 10.0.0.0/8 (allow)
  - Default rule *: DENY all (inbound and outbound)

Note: there is no outbound rule for the ephemeral port range
(1024-65535) on acl-api. The default rule denies everything not
explicitly allowed.
```

NACLs are stateless. The SYN-ACK from i-api-server back to the client
uses an ephemeral destination port (e.g., 54312). Without an outbound
NACL rule on the ephemeral range, the SYN-ACK is dropped on the
subnet-api outbound evaluation.
