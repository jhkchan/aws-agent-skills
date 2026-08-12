# Baseline (no-skill) — missing-crl-bucket-policy

> This is the response a model produces **without** the skill
> definition. It creates the CA with CRL configured but does not flag
> that the S3 bucket is missing the policy granting
> acm-pca.amazonaws.com write access. CRL publication would silently
> fail — revoked certificates would appear valid to clients. Does not
> emit a PREREQUISITES_MISSING verdict. Generated for with-skill-vs-
> baseline comparison.

---

Sure, here's the CA with CRL:

```bash
aws acm-pca create-certificate-authority \
  --certificate-authority-configuration \
    "KeyAlgorithm=RSA_2048,SigningAlgorithm=SHA256withRSA,Subject={CN=Example Root CA,O=Example Org,C=US}" \
  --revocation-configuration \
    "CrlConfiguration={Enabled=true,S3BucketName=acm-pca-crl-123456789012-us-east-1,ExpirationInDays=7}" \
  --certificate-authority-type ROOT
```

Then activate the CA with a self-signed certificate.
