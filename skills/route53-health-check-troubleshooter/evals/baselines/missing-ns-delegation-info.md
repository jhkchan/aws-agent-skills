# Baseline (no-skill) response: missing-ns-delegation-info

---

Your DNS failover isn't working. This could be because the health
check isn't configured correctly, the routing policy isn't set up
properly, or there's a DNS delegation issue. Check that the health
check is associated with the primary record and that the failover
policy is configured.

Also make sure the NS records for your domain point to the right
hosted zone. You can verify this by running `dig NS example.com` and
comparing the results with the NS record in your Route 53 hosted zone.
