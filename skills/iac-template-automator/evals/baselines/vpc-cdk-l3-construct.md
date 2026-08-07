# Baseline (no-skill) response: vpc-cdk-l3-construct

This file captures what a generic assistant produces WITHOUT the
iac-template-automator skill loaded.

---

Here's some CDK code for a VPC:

```typescript
import * as ec2 from 'aws-cdk-lib/aws-ec2';

const vpc = new ec2.Vpc(this, 'MyVpc', {
  ipAddresses: ec2.IpAddresses.cidr('10.0.0.0/16'),
  maxAzs: 3,
});

// You can add subnets and NAT gateways as needed
```

This creates a basic VPC with the default configuration. The L3 Vpc
construct handles a lot of the details for you automatically.
