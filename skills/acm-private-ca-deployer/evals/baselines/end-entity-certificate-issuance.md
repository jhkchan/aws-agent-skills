# Baseline (no-skill) — end-entity-certificate-issuance

> This is the response a model produces **without** the skill
> definition. It issues the certificate but misses the correct
> certificate template (EndEntityCertificate_CertPassedPathLen_0),
> does not verify the CA is ACTIVE before issuing, and does not emit
> the READY_TO_DEPLOY checklist format. Generated for with-skill-vs-
> baseline comparison.

---

Issue the certificate:

```bash
aws acm-pca issue-certificate \
  --certificate-authority-arn arn:aws:acm-pca:us-east-1:123456789012:certificate-authority/dddd-eeee-ffff \
  --csr fileb://server.csr \
  --validity Value=365,Type=DAYS
```

Then get the certificate once issued.
