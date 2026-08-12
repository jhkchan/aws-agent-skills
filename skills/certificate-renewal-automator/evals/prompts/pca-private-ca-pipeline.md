# Eval prompt: pca-private-ca-pipeline

Design a certificate renewal automation pipeline for the following
PCA-issued private certificate. Emit the standard RENEWAL block
including PCA lifecycle monitoring (CERTIFICATE, CLASSIFICATION,
DETECTION, RENEWAL_FLOW, VALIDATION, NOTIFICATION, AUDIT, VERDICT,
TEMPLATE).

Design reference: pca-private-ca-pipeline
Account: 111111111111
Region: us-east-1

PCA CA: arn:aws:acm-pca:us-east-1:111111111111:certificate-authority/pca-abc
CA Status: ACTIVE, CA NotAfter: 2028-06-15
End-certificate: internal-api.example.com (arn:aws:acm:us-east-1:111111111111:certificate/pca-cert-001)
Validation method: DNS
Status: ISSUED
Attached to: ALB listener
DaysToExpiry: 55
CA remaining validity: approximately 2 years
