# Baseline (no-skill) — root-ca-with-crl

> This is the response a model produces **without** the skill
> definition. It creates the CA but misses the CRL S3 bucket policy
> requirement (the bucket must grant acm-pca.amazonaws.com write
> access), the self-signed root certificate activation step (the CA
> starts in PENDING_CERTIFICATE and must be activated), the
> RootCACertificate/V1 template, and the READY_TO_DEPLOY checklist
> format. Generated for with-skill-vs-baseline comparison.

---

Create the CA:

```bash
aws acm-pca create-certificate-authority \
  --certificate-authority-configuration \
    "KeyAlgorithm=RSA_2048,SigningAlgorithm=SHA256withRSA,Subject={CN=Example Root CA,O=Example Org,C=US}" \
  --certificate-authority-type ROOT
```

That should set up the root CA with CRL.
