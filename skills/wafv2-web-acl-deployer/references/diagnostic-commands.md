# Diagnostic and Pre-flight Commands - wafv2-web-acl-deployer

## Pre-flight safety checks (moved from SKILL.md)

- **Confirm the scope decision:**
  ```bash
  aws cloudfront get-distribution --id <dist-id> 2>/dev/null && echo "CLOUDFRONT scope needed"
  aws elbv2 describe-load-balancers --load-balancer-arns <alb-arn> 2>/dev/null && echo "REGIONAL scope needed"
  ```

- **Confirm the target resource exists:**
  ```bash
  aws elbv2 describe-load-balancers --names <alb-name> --region <region>
  aws apigateway get-rest-apis --region <region>
  aws cloudfront get-distribution --id <dist-id>
  ```

- **Confirm the logging destination exists and has the right policy:**
  ```bash
  aws firehose describe-delivery-stream --delivery-stream-name aws-waf-logs-<name>
  aws logs describe-resource-policies
  aws s3api get-bucket-policy --bucket <log-bucket>
  ```

- **Confirm IP sets and regex pattern sets exist (if referenced):**
  ```bash
  aws wafv2 list-ip-sets --scope <scope> --region <region>
  aws wafv2 list-regex-pattern-sets --scope <scope> --region <region>
  ```

- **Confirm managed rule group availability (ATP, Bot Control):**
  ```bash
  aws wafv2 list-available-managed-rule-groups --scope <scope> --region <region>
  ```
