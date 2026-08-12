# Baseline (no-skill) response: san-validation-gap

This file captures what a generic assistant produces WITHOUT the
certificate-renewal-automator skill loaded.

---

The certificate's RenewalEligibility is INELIGIBLE, which means ACM
won't auto-renew it. This is probably because something is wrong with
the DNS validation.

You should check the DNS records for all domains in the certificate
and make sure the validation CNAMEs are in place. Once you fix the DNS
records, ACM should start renewing the certificate again.

You can check the status with `aws acm describe-certificate`.
