# Baseline (no-skill) response: multi-region-global-types-gap

---

All three regions (us-east-1, us-west-2, eu-west-1) have configuration
recorders running with allSupported enabled. The delivery channels are
all working. Each region has at least one Config rule deployed.

However, none of the regions have includeGlobalResourceTypes set to true.
This means global resources like IAM, CloudFront, and Route 53 are not
being recorded in any region.

You should enable includeGlobalResourceTypes in one region (recommended:
us-east-1) to start recording global resources.
