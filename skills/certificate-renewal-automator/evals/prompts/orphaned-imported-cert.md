# Eval prompt: orphaned-imported-cert

Design a certificate renewal automation pipeline for the following
certificate. Emit the standard RENEWAL block (CERTIFICATE,
CLASSIFICATION, DETECTION, RENEWAL_FLOW, VALIDATION, NOTIFICATION,
AUDIT, VERDICT, GAP, TEMPLATE).

Design reference: orphaned-imported-cert
Account: 111111111111
Region: us-east-1

Certificate: api.internal.example.com (arn:aws:acm:us-east-1:111111111111:certificate/def-456)
Validation method: IMPORTED (private key from external DigiCert CA)
Status: ISSUED, RenewalEligibility: INELIGIBLE
InUseBy: [] (orphaned)
DaysToExpiry: 18

The operator wants full automation for this certificate's renewal.
