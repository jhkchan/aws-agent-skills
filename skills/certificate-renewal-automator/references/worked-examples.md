# certificate-renewal-automator — worked examples (moved from SKILL.md)

Progressive-disclosure reference. Content below was moved verbatim from SKILL.md; the agent loads it only when needed.

## Worked example — REVIEW_REQUIRED (imported orphaned cert)

```text
CERTIFICATE: arn:aws:acm:us-east-1:111111111111:certificate/def-456-ghi-789
VERDICT: REVIEW_REQUIRED
CHECKLIST:
  [x] DaysToExpiry: 14 (NotBefore 2025-08-11, NotAfter 2026-08-26)
  [ ] Renewal method: MANUAL_REIMPORT (imported cert — ACM holds no private key)
  [ ] RenewalEligibility: INELIGIBLE
  [ ] DNS validation: N/A (imported certs bypass DNS validation)
  [ ] InUseBy: ORPHANED (InUseBy: [] — managed renewal disabled)
  [ ] RenewalStatus: FAILED (no managed path; daily scan flagged HIGH risk at < 30d)
  [x] Detection: CloudWatch alarm firing (DaysToExpiry < 30) + EventBridge scan flagged HIGH
GAP: Imported private-key certificate is orphaned and INELIGIBLE for managed renewal. Required: (1) Renew at external CA; (2) export new cert + private key + chain PEM; (3) re-import via `aws acm import-certificate --certificate file://cert.pem --private-key file://key.pem --certificate-chain file://chain.pem`; (4) re-attach to listener/distribution. Migrate to DNS-validated ACM cert or PCA-issued cert for managed renewal path.
TEMPLATE: (held in draft — external CA renewal + manual acm import-certificate flow required; see references/imported-cert-manual-renewal.md)
```
