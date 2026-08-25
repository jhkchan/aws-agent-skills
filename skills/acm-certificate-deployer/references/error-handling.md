# Error Handling — ACM Certificate Deployer

Load-on-demand error-handling detail moved verbatim from SKILL.md.

## Step 6 — common import errors

- `MalformedCertificate`: PEM is invalid or missing BEGIN/END markers.
- `CertificateValidator Timeout`: private key does not match the
  certificate.
- `InvalidCertificate`: chain is incomplete or out of order.

## Error handling

### Certificate stuck in `PENDING_VALIDATION`
- **DNS validation:** CNAME not added, or added incorrectly. Retrieve
  the expected CNAME via `describe-certificate`, verify the Route53
  record matches. Use `dig`/`nslookup` to confirm propagation.
- **Email validation:** email not received or not clicked. Use
  `resend-validation-email`; check spam filters. Switch to DNS
  validation by re-requesting the certificate.

### CloudFront returns "certificate does not exist"
- Certificate is not in us-east-1, or not in `ISSUED` status. Verify
  the ARN starts with `arn:aws:acm:us-east-1:`. If wrong region, re-
  request in us-east-1.

### Imported certificate rejected (`MalformedCertificate`)
- PEM files invalid, out of order, or key mismatch. Verify BEGIN/END
  markers. Verify key matches cert (`openssl x509`/`openssl rsa`
  modulus comparison). Chain must be root → intermediate (no leaf).

### Renewal failed (imported certificate)
- Imported certificates are NOT auto-renewed. Renew with the external
  CA, re-import using the same ARN. Set CloudWatch monitoring on
  `DaysToExpiry` < 30.
