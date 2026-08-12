# Baseline (no-skill) response: pca-private-ca-pipeline

This file captures what a generic assistant produces WITHOUT the
certificate-renewal-automator skill loaded.

---

For PCA-issued certificates, you'll need to set up a renewal pipeline
since ACM doesn't fully auto-renew private certs the same way as
public ones. You can use `aws acm-pca issue-certificate` to issue a
new cert when the current one is close to expiring.

Make sure your PCA CA doesn't expire too. The CA looks like it has
about 2 years left, so you should be fine for now.

A Lambda function could automate the renewal process by checking
expiry dates and issuing new certs.
