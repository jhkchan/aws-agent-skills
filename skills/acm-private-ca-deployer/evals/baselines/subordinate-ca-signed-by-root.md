# Baseline (no-skill) — subordinate-ca-signed-by-root

> This is the response a model produces **without** the skill
> definition. It creates the subordinate CA but misses the parent CA
> create-permission requirement (parent must grant permission to issue),
> the parent-signed certificate activation workflow (CSR must be issued
> by parent then imported), the ACM service principal permission for
> managed cert lifecycle, and the READY_TO_DEPLOY checklist format.
> Generated for with-skill-vs-baseline comparison.

---

Create the subordinate CA:

```bash
aws acm-pca create-certificate-authority \
  --certificate-authority-configuration \
    "KeyAlgorithm=RSA_2048,SigningAlgorithm=SHA256withRSA,Subject={CN=Example Subordinate CA,O=Example Org,C=US}" \
  --certificate-authority-type SUBORDINATE
```

Then have the parent sign it and import the certificate.
