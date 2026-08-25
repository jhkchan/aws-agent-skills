# Diagnostic Commands (load on demand) — Config Aggregator Deployer

Pre-provisioning safety check commands, moved verbatim from SKILL.md.


---

## Pre-flight safety checks (run before any provisioning CLI) (moved from SKILL.md)

- **Confirm Organizations all features enabled:**
  ```bash
  aws organizations describe-organization --query 'Organization.FeatureSet' --output text
  aws organizations list-aws-service-access-for-organization --filter config.amazonaws.com
  aws organizations list-delegated-administrators --service-principal config.amazonaws.com
  ```

- **Confirm Config recorder and delivery channel on source accounts:**
  ```bash
  aws configservice describe-configuration-recorder-status --configuration-recorder-names default
  aws configservice describe-delivery-channels
  aws configservice describe-conformance-pack-templates
  ```
