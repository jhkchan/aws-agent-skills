# Baseline (no-skill) response: expiring-soon-amazon-15-days

This file captures what a generic assistant produces WITHOUT the
acm-certificate-expiry-auditor skill loaded.

---

Your certificate for api.example.com expires on August 19, 2026, which is
about 15 days away. The renewal status is PENDING_AUTORENEWAL, so ACM is
trying to renew it. Since it is an Amazon-issued certificate, renewal should
happen automatically as long as the DNS validation records are still in
place.

Check that the validation CNAME is still present in your DNS and wait for
ACM to complete the renewal. If it does not renew soon, you may need to
re-request the certificate.
