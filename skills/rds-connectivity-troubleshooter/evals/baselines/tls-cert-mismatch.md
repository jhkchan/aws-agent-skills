# Baseline (no-skill) response: tls-cert-mismatch

---

The error "unable to get local issuer certificate" means the Java client
doesn't trust the RDS certificate. This happened after the CA was
rotated, so the new CA isn't in your truststore.

You should download the new CA bundle from the AWS docs and add it to
your Java truststore using keytool. After updating the truststore, the
connection should work again.
