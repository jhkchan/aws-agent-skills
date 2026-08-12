# Baseline (no-skill) response: acm-dns-alb-auto-renewal

This file captures what a generic assistant produces WITHOUT the
certificate-renewal-automator skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, renewal pipeline
template, detection/verification steps, expert ACM knowledge).

---

ACM automatically renews certificates that are DNS-validated and
attached to a supported service like an ALB. Since this cert is
attached to an ALB and uses DNS validation, ACM will handle the
renewal for you.

You might want to set up a CloudWatch alarm on the DaysToExpiry
metric. You can find the metric in the AWS/CertificateManager
namespace.

The cert should be fine as long as the DNS validation CNAME stays in
Route 53.
