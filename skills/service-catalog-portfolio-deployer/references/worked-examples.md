# Worked Examples — Service Catalog Portfolio Deployer

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

### Perfect example output — PREREQUISITES_MISSING

```text
PORTFOLIO: Cross-Region VPC Products (products: 0, shares: o-abc123def456 in us-east-1)
VERDICT: PREREQUISITES_MISSING
CHECKLIST:
  [✓] Intent + consumer scope: Distribute VPC-creator products to the whole organization, scope ORGANIZATION
  [✗] Portfolio created: pending — deferred until launch role prerequisite is resolved
  [✗] Product(s): pending — CloudFormation template URL not validated
  [—] Product-portfolio association: deferred until product exists
  [✗] Constraint(s): no LAUNCH role exists. Create sc-launch-vpc-role with ec2:* + iam:PassRole (with tag condition) before applying the LAUNCH constraint — without it, products launch as the end-user's role = privilege escalation.
  [—] TagOptions: deferred
  [✗] Share(s): Organizations not enabled for Service Catalog — enable-aws-service-access for servicecatalog.amazonaws.com before sharing at the org level. Region us-east-1 confirmed for caller; document for consumers.
VERIFICATION_COMMANDS:
  aws organizations describe-organization --query 'Organization.Id'
  aws organizations list-delegated-administrators --service-principal servicecatalog.amazonaws.com
  aws iam get-role --role-name sc-launch-vpc-role
  aws cloudformation validate-template --template-url https://s3.amazonaws.com/platform-templates/vpc.yaml
```
