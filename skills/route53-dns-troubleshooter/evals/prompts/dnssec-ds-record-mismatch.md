# Eval prompt: dnssec-ds-record-mismatch

Diagnose the Route 53 DNSSEC validation failure for the following domain.
Walk the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: `app.example.com` returns SERVFAIL from Cloudflare DNS
(1.1.1.1) but resolves correctly from Google DNS (8.8.8.8). The
SERVFAIL started after a KSK rotation yesterday.

```text
Domain: app.example.com
HostedZoneId: Z3DEFGHIJKL

DNSSEC status (get-dnssec):
  KeySigningKeys[0]:
    KeyTag: 12345
    KeyState: ACTIVE
    DigestAlgorithm: 2 (SHA-256)
  ZoneSigningKeys[0]:
    KeyState: ACTIVE

DS record at parent (dig +dnssec DS example.com @8.8.8.8):
  67890 13 2 <old-digest>
  (Key tag 67890 does NOT match KSK key tag 12345)

Resolution test:
  dig +dnssec app.example.com @1.1.1.1:
    status: SERVFAIL, ad: false
  dig +dnssec app.example.com @8.8.8.8:
    status: NOERROR, ANSWER: 203.0.113.50
```

The DS record at the parent zone has the old KSK key tag (67890), not
the current KSK key tag (12345). Validating resolvers (Cloudflare)
return SERVFAIL because the chain of trust is broken. Non-validating
resolvers (Google) ignore DNSSEC and resolve correctly.
