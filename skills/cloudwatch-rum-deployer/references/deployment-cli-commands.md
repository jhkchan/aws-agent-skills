# Deployment CLI commands — deep reference

This reference expands the SKILL.md deployment steps with the
full copy-pasteable CLI command sequence, Terraform equivalents,
CloudFormation snippets, and per-framework (React, Vue, Angular,
Next.js) integration code. Load when wiring the RUM SDK end-to-end
or migrating from CDN to npm.

## App monitor lifecycle

### Create

```bash
aws rum create-app-monitor \
  --name checkout-web-prod \
  --app-monitor-configuration '{
    "AllowList": ["https://checkout.example.com"],
    "SessionSampleRate": 1.0,
    "Telemetries": ["errors", "performance", "http"],
    "EnableXRay": true,
    "GuestRoleArn": "arn:aws:iam::111122223333:role/checkout-web-rum-guest",
    "IdentityPoolId": "us-east-1:abcd1234-efgh-5678"
  }' \
  --cw-log-group-name /aws/rum/checkout-web-prod \
  --domain checkout.example.com \
  --tags team=payments,env=prod \
  --region us-east-1
```

### Read

```bash
aws rum get-app-monitor --name checkout-web-prod --region us-east-1
aws rum list-app-monitors --region us-east-1
```

### Update

```bash
aws rum update-app-monitor \
  --name checkout-web-prod \
  --app-monitor-configuration '{
    "AllowList": [
      "https://checkout.example.com",
      "https://checkout-beta.example.com"
    ],
    "SessionSampleRate": 0.1,
    "Telemetries": ["errors", "performance", "http"],
    "EnableXRay": true
  }' \
  --region us-east-1
```

### Delete

```bash
aws rum delete-app-monitor --name checkout-web-prod --region us-east-1
```

## Guest IAM role (Cognito identity pool)

```bash
# Create the identity pool with unauth role
aws cognito-identity create-identity-pool \
  --identity-pool-name checkout-web-rum-pool \
  --allow-unauthenticated-identities \
  --region us-east-1

# Capture IdentityPoolId from the response
POOL_ID=us-east-1:abcd1234-efgh-5678

# Trust policy for the unauth role
cat > /tmp/guest-trust.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Federated": "cognito-identity.amazonaws.com" },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "cognito-identity.amazonaws.com:aud": "us-east-1:abcd1234-efgh-5678"
      },
      "ForAnyValue:StringLike": {
        "cognito-identity.amazonaws.com:amr": "unauth"
      }
    }
  }]
}
EOF

aws iam create-role \
  --role-name checkout-web-rum-guest \
  --assume-role-policy-document file:///tmp/guest-trust.json

# Inline permission policy — resource-locked to the app monitor ARN
cat > /tmp/guest-permission.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": "rum:PutRumEvents",
    "Resource": "arn:aws:rum:us-east-1:111122223333:appmonitor/checkout-web-prod"
  }]
}
EOF

aws iam put-role-policy \
  --role-name checkout-web-rum-guest \
  --policy-name CheckoutWebRUMPutEvents \
  --policy-document file:///tmp/guest-permission.json

# Wire the role to the identity pool's unauth role
aws cognito-identity set-identity-pool-roles \
  --identity-pool-id $POOL_ID \
  --roles unauthenticated=arn:aws:iam::111122223333:role/checkout-web-rum-guest
```

## Custom metrics destination

```bash
aws rum put-metrics-destination \
  --app-monitor-name checkout-web-prod \
  --metric-definition-namespace AWS/RUM \
  --metric-definition-name CartValueTotal \
  --metric-definition-value-key '$.event.data.cartValue' \
  --region us-east-1

aws rum list-metrics-destinations \
  --app-monitor-name checkout-web-prod \
  --region us-east-1
```

## Terraform equivalents

```hcl
resource "aws_cognito_identity_pool" "rum" {
  identity_pool_name               = "checkout-web-rum-pool"
  allow_unauthenticated_identities = true
}

resource "aws_iam_role" "rum_guest" {
  name = "checkout-web-rum-guest"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Federated = "cognito-identity.amazonaws.com" }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "cognito-identity.amazonaws.com:aud" = aws_cognito_identity_pool.rum.id
        }
        "ForAnyValue:StringLike" = {
          "cognito-identity.amazonaws.com:amr" = "unauth"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "rum_guest" {
  name = "CheckoutWebRUMPutEvents"
  role = aws_iam_role.rum_guest.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "rum:PutRumEvents"
      Resource = aws_rum_app_monitor.checkout.arn
    }]
  })
}

resource "aws_rum_app_monitor" "checkout" {
  name     = "checkout-web-prod"
  domain   = "checkout.example.com"
  cw_log_group_enabled = true

  app_monitor_configuration {
    allow_list           = ["https://checkout.example.com"]
    session_sample_rate  = 1.0
    telemetries          = ["errors", "performance", "http"]
    enable_xray          = true
    guest_role_arn       = aws_iam_role.rum_guest.arn
    identity_pool_id     = aws_cognito_identity_pool.rum.id
  }

  tags = { team = "payments", env = "prod" }
}
```

## CloudFormation snippet

```yaml
RumAppMonitor:
  Type: AWS::RUM::AppMonitor
  Properties:
    Name: checkout-web-prod
    Domain: checkout.example.com
    CwLogGroupEnabled: true
    AppMonitorConfiguration:
      AllowList:
        - https://checkout.example.com
      SessionSampleRate: 1.0
      Telemetries:
        - errors
        - performance
        - http
      EnableXRay: true
      GuestRoleArn: !GetAtt RumGuestRole.Arn
      IdentityPoolId: !Ref RumIdentityPool
    Tags:
      - { Key: team, Value: payments }
      - { Key: env, Value: prod }
```

## Per-framework SDK integration

### React

```typescript
// src/rum.ts
import { AwsRum, AwsRumConfig } from 'aws-rum-web';

const config: AwsRumConfig = {
  sessionSampleRate: 1.0,
  guestRoleArn: 'arn:aws:iam::111122223333:role/checkout-web-rum-guest',
  identityPoolId: 'us-east-1:abcd1234-efgh-5678',
  endpoint: 'https://dataplane.rum.us-east-1.amazonaws.com',
  telemetries: ['errors', 'performance', 'http'],
  allowCookies: true,
  cookieDomain: '.example.com',
  enableXRay: true
};

export const awsRum = new AwsRum(
  'checkout-web-prod', '1.0.0', 'us-east-1', config
);
```

```typescript
// src/main.tsx
import { awsRum } from './rum';
import React from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './App';

// Record a page view on every route change (using a router hook)
// See the Application Signals correlation guide for the full pattern.

createRoot(document.getElementById('root')!).render(<App />);
```

### Next.js (SSR-safe)

```typescript
// src/lib/rum.ts
let awsRum: AwsRum | undefined;
if (typeof window !== 'undefined') {
  const { AwsRum } = require('aws-rum-web');
  awsRum = new AwsRum(
    'checkout-web-prod', '1.0.0', 'us-east-1', {
      sessionSampleRate: 1.0,
      guestRoleArn: 'arn:aws:iam::111122223333:role/checkout-web-rum-guest',
      identityPoolId: 'us-east-1:abcd1234-efgh-5678',
      telemetries: ['errors', 'performance', 'http'],
      cookieDomain: '.example.com',
      enableXRay: true
    }
  );
}
export { awsRum };
```

### Vue

```typescript
// src/rum.ts
import { AwsRum } from 'aws-rum-web';

export const awsRum = new AwsRum(
  'checkout-web-prod', '1.0.0', 'us-east-1', {
    sessionSampleRate: 1.0,
    guestRoleArn: 'arn:aws:iam::111122223333:role/checkout-web-rum-guest',
    identityPoolId: 'us-east-1:abcd1234-efgh-5678',
    telemetries: ['errors', 'performance', 'http'],
    cookieDomain: '.example.com',
    enableXRay: true
  }
);
```

```typescript
// src/router/index.ts
import { awsRum } from '@/rum';
import { createRouter } from 'vue-router';

const router = createRouter({ /* routes */ });

router.afterEach((to) => {
  awsRum?.recordPageView(to.path);
});
```

## Verification suite (run after deployment)

```bash
# App monitor state
aws rum get-app-monitor --name checkout-web-prod --region us-east-1

# Metrics flowing in AWS/RUM
aws cloudwatch list-metrics --namespace AWS/RUM \
  --dimensions Name=ApplicationName,Value=checkout-web-prod \
  --region us-east-1

# Application Signals client correlation
aws cloudwatch list-metrics --namespace AWS/ApplicationSignalsClient \
  --region us-east-1

# X-Ray sampling rule for server-side correlation
aws xray get-sampling-rules --region us-east-1

# Guest role policy
aws iam list-attached-role-policies --role-name checkout-web-rum-guest
aws iam get-role-policy \
  --role-name checkout-web-rum-guest \
  --policy-name CheckoutWebRUMPutEvents

# CloudWatch Logs group
aws logs describe-log-streams \
  --log-group-name /aws/rum/checkout-web-prod \
  --limit 1 --order-by LastEventTime --descending

# Tag verification
aws rum list-tags-for-resource \
  --resource-arn arn:aws:rum:us-east-1:111122223333:appmonitor/checkout-web-prod
```

## Common pitfalls (extended)

### CORS rejection

RUM CORS policy is governed by the app monitor's `AllowList`. The
scheme, host, and port must all match. `https://app.example.com`
and `https://app.example.com:8443` are different origins. Always
include `https://` in every entry.

### Stale CDN script

The SDK is versioned independently of the service. Pin to a
specific version (`aws-rum-web@1.18.0`) in the CDN script tag.
Auto-upgrading can break event schemas. Use Subresource Integrity
(`integrity="sha384-<hash>"`) to detect CDN tampering.

### Guest role ARN mismatch

The `rum:PutRumEvents` resource must EXACTLY match the app
monitor ARN. A typo (wrong Region, wrong account, wrong name)
produces `AccessDenied` in the browser console with no error in
the app monitor.

### Cookie domain over-broad

Setting `cookieDomain: '.com'` (or any public suffix) corrupts
session counts across unrelated sites and risks cross-customer
contamination. Use the parent organizational domain (e.g.,
`.example.com`) or omit to default to the current host.
