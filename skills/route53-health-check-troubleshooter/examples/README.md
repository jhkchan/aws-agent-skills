# Example usage: route53-health-check-troubleshooter

A walkthrough showing the skill diagnosing an HTTPS health check that
reports unhealthy due to a certificate name mismatch, demonstrating
the symptom-to-layer triage, the FQDN vs certificate SAN
identification, the evidence-backed ROOT_CAUSE_IDENTIFIED verdict, and
the certificate SAN update fix.

## Input (user prompt)

> Our Route 53 health check hc-prod-api reports unhealthy. The endpoint
> is reachable from the VPC via curl -k. DNS failover should redirect
> to the secondary, but the primary is still being served. We've been
> debugging this as a network issue for 30 minutes — please help us
> find the actual root cause.

```text
HealthCheckId: hc-prod-api
Type: HTTPS
FullyQualifiedDomainName: health.prod.example.com
IPAddress: 10.0.1.10 (public via ALB)
Port: 443
EnableSNI: true
RequestInterval: 30
FailureThreshold: 3
ResourcePath: /

RoutingPolicy: FAILOVER
PrimaryRecord: api.prod.example.com (Failover: PRIMARY, HealthCheckId: hc-prod-api)
SecondaryRecord: api.prod.example.com (Failover: SECONDARY)
TTL: 60

Certificate on the endpoint (openssl s_client):
  subject: CN=api.prod.example.com
  SAN: [api.prod.example.com, www.prod.example.com]
  Validity: NotBefore 2026-01-15, NotAfter 2027-01-15
  "health.prod.example.com" is NOT in the SAN list

Health check status (get-health-check-status):
  All 15+ regions reporting unhealthy
  StatusReason: "The SSL certificate failed validation"

Network verification:
  curl -k https://10.0.1.10:443/ — succeeds (200 OK)
  SG sg-prod-alb inbound: allows 0.0.0.0/0 on 443
```

## Skill output

```text
TARGET: health-check hc-prod-api / api.prod.example.com
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: HTTPS health check FQDN is health.prod.example.com but the
  endpoint serves a certificate with SAN [api.prod.example.com,
  www.prod.example.com]. Route 53 health checker validates the TLS
  certificate against the FQDN and rejects the mismatch, reporting
  unhealthy with "The SSL certificate failed validation" across all
  15+ regions (Step 3).
LAYER: CERTIFICATE_MISMATCH
EVIDENCE:
  - Symptom: health check hc-prod-api reports unhealthy; endpoint
    reachable via curl -k from within the VPC.
  - Probe: aws route53 get-health-check returns
    FullyQualifiedDomainName: "health.prod.example.com", Type: HTTPS,
    EnableSNI: true.
  - Probe: openssl s_client -connect 10.0.1.10:443 -servername
    health.prod.example.com returns certificate with subject
    CN=api.prod.example.com, SAN=[api.prod.example.com,
    www.prod.example.com]. "health.prod.example.com" is NOT in the
    SAN list.
  - Probe: aws route53 get-health-check-status returns all 15+
    regions unhealthy with StatusReason "The SSL certificate failed
    validation."
  - Passing: SG sg-prod-alb allows 0.0.0.0/0 on 443 (network is not
    the issue — confirmed by curl -k success); FailureThreshold = 3
    is standard (threshold math is correct); routing policy FAILOVER
    has the primary record correctly associated with the health check
    (routing is not the issue); TTL is 60 (DNS caching is not causing
    the delay).
REMEDIATION:
  1. Add health.prod.example.com to the ACM certificate SAN:
     aws acm request-certificate --domain-name api.prod.example.com \
       --subject-alternative-names www.prod.example.com,health.prod.example.com \
       --validation-method DNS --profile <p>
  2. Validate the new certificate (DNS or email validation).
  3. Deploy the new certificate on the ALB listener:
     aws elbv2 modify-listener --listener-arn <arn> \
       --certificates CertificateArn=<new-cert-arn> --profile <p>
  4. Alternatively, change the health check FQDN to match the existing
     cert SAN (api.prod.example.com) and update ResourcePath to a
     dedicated health endpoint:
     aws route53 update-health-check --health-check-id hc-prod-api \
       --fully-qualified-domain-name api.prod.example.com --profile <p>
  5. Verify: aws route53 get-health-check-status --health-check-id
     hc-prod-api should report Healthy across all regions within 3
     intervals (90 seconds at RequestInterval 30).
CONFIRM: Before requesting the certificate or changing the health
  check, emit: "CONFIRM: About to request a new ACM certificate with
  SAN health.prod.example.com and/or update the health check FQDN.
  Proceed? (yes/no)"
```

## What the skill caught that a generic assistant misses

1. **Identified the certificate name mismatch as the root cause, not a
   network issue.** A generic assistant says "check the security group"
   or "try TCP health check." The skill recognises that HTTPS health
   checks validate the certificate against the FQDN — `curl -k`
   succeeds because `-k` disables certificate validation, but the
   health checker does NOT skip validation.

2. **Used the per-region StatusReason as positive evidence.** The
   skill reads the `get-health-check-status` output showing "The SSL
   certificate failed validation" across all regions, which directly
   confirms the certificate mismatch diagnosis.

3. **Distinguished certificate mismatch from endpoint unreachability.**
   Both produce "unhealthy" status, but the StatusReason distinguishes
   them: "connection timed out" (network) vs "SSL certificate failed
   validation" (cert). The skill routes to CERTIFICATE_MISMATCH based
   on this evidence.

4. **Ruled out network, threshold, routing, and TTL.** The evidence
   section explicitly passes each of these layers: SG allows all
   inbound on 443, FailureThreshold is standard at 3, the FAILOVER
   routing policy has the health check correctly associated, and TTL
   is 60 (no caching issue). This eliminates the other plausible
   causes before declaring the cert mismatch.

5. **Provided two remediation paths.** The skill offers both adding
   the FQDN to the certificate SAN (if the health endpoint is on the
   same ALB) and changing the health check FQDN to match the existing
   cert (if a dedicated health endpoint exists on the same domain).

## Slash-command invocation

```
/aws:troubleshoot-route53-health-check
```

Or via the orchestrator:

```
/aws:pipeline
You: "diagnose why Route 53 health check hc-prod-api reports unhealthy"
```

## Live-account follow-up (optional, requires AWS CLI)

After remediating, validate the health check:

```bash
# Confirm the health check is now healthy
aws route53 get-health-check-status \
  --health-check-id hc-prod-api \
  --profile default --output json | \
  jq '.HealthCheckObservations[] | {Region, Status}'

# Confirm DNS failover switches back to primary
dig @8.8.8.8 api.prod.example.com +short

# Confirm the certificate SAN includes the FQDN
aws acm describe-certificate \
  --certificate-arn <new-cert-arn> \
  --profile default --output json | \
  jq '.Certificate.SubjectAlternativeNames'

# Confirm the ALB listener uses the new certificate
aws elbv2 describe-listeners --listener-arns <arn> \
  --profile default --output json | \
  jq '.Listeners[].Certificates'
```

Then monitor the health check status for 5-10 minutes to confirm all
regions report healthy consistently.
