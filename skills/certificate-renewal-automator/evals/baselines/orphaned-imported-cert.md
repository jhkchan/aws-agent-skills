# Baseline (no-skill) response: orphaned-imported-cert

This file captures what a generic assistant produces WITHOUT the
certificate-renewal-automator skill loaded.

---

This certificate was imported from DigiCert and isn't attached to any
resource. ACM won't auto-renew it. You'll need to renew it manually at
DigiCert and re-import it.

You can use `aws acm import-certificate` to import the renewed cert.
You'll need the certificate, private key, and chain from DigiCert.

Since it's not attached to anything, you might also consider whether
you still need it.
