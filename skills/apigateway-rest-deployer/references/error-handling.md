# Error handling - API Gateway REST Deployer

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Remediation guidance

**Ordering principle:** authorization first (active exposure if wrong),
then deployment snapshot (changes not live), then throttling/quotas
(abuse prevention), then optimization (logging, canary, custom domain).

### For PREREQUISITES_MISSING — ACM cert in wrong region

1. Re-issue or import the cert in the correct region:
   - EDGE API: us-east-1
   - REGIONAL API: API region
2. Update the custom domain configuration with the new cert ARN.

### For PREREQUISITES_MISSING — VPC Link to ALB

1. Create an NLB that targets the ALB (or ALB's targets directly).
2. Verify NLB has target groups in the API's region across multiple AZs.
3. Create the VPC Link targeting the NLB ARN.
4. Update the HTTP integration with `connectionType: VPC_LINK`.

### For PREREQUISITES_MISSING — Lambda in different region

1. Recreate the function in the API's region.
2. Update the integration URI with the new function ARN.
3. Re-issue `lambda:AddPermission` for the API Gateway principal.


