# Auth Policy and Cross-Account Access — VPC Lattice Deployer

Deep reference on IAM auth policies (service-level scope, not rule-level),
resource-based service policies (cross-account invocation), RAM resource
sharing (cross-account service network access), and access log delivery.
Loaded on demand by the skill — kept out of the main SKILL.md body so the
provisioning procedure stays scannable.

## IAM auth policy scope: SERVICE level, not rule level

### Why auth cannot be scoped per rule

The VPC Lattice auth policy is a property of the SERVICE resource, not
of individual listener rules. When you call `put-auth-policy`, the
resource identifier is the service ID — there is no API to attach an
auth policy to a specific rule within a service.

```text
Service: payments-svc (svc-bbb222)
  Auth Policy (attached to service — covers ALL rules)
    ├── Listener Rule 1: /api/*   ← auth policy applies
    ├── Listener Rule 2: /admin/* ← auth policy applies
    └── Default Rule: *           ← auth policy applies

If you need /api/* WITHOUT auth and /admin/* WITH auth:
  → Create TWO services:
    Service A: payments-api-svc (no auth policy)
    Service B: payments-admin-svc (IAM auth policy)
```

### Setting auth type and policy

```bash
# Step 1: Set the service auth type to AWS_IAM
aws vpc-lattice update-service \
  --service-identifier svc-bbb222 \
  --body '{"authType":"AWS_IAM"}'

# Step 2: Put the auth policy on the service
aws vpc-lattice put-auth-policy \
  --resource-identifier svc-bbb222 \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {
          "AWS": "arn:aws:iam::123456789012:role/PaymentsCaller"
        },
        "Action": "vpc-lattice-svcs:Invoke",
        "Resource": "*"
      }
    ]
  }'
```

### Auth policy conditions

Auth policies support IAM conditions for fine-grained control:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::123456789012:role/PaymentsCaller"},
      "Action": "vpc-lattice-svcs:Invoke",
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "vpc-lattice-svcs:RequestMethod": "GET"
        }
      }
    }
  ]
}
```

This allows GET requests only — POST/PUT still denied even for the
allowed principal. The condition applies to ALL paths on the service.

### Verifying auth policy

```bash
aws vpc-lattice get-auth-policy \
  --resource-identifier svc-bbb222 \
  --query 'policy' --output json | jq '.'
```

If the policy is empty or the auth type is `NONE`, no auth is enforced.

## Resource-based service policy (cross-account invocation)

The service policy is a resource-based IAM policy on the service. It
controls who can INVOKE the service from other accounts. This is
separate from the auth policy (which controls request-level
authentication).

```bash
aws vpc-lattice put-service-policy \
  --service-identifier svc-bbb222 \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {"AWS": "arn:aws:iam::999999999999:root"},
        "Action": "vpc-lattice-svcs:Invoke",
        "Resource": "*"
      }
    ]
  }'
```

This allows account 999999999999 to invoke this service. Combined with
RAM sharing, enables full cross-account access.

## Cross-account access via RAM

### Step 1: Create a RAM resource share

```bash
aws ram create-resource-share \
  --name lattice-cross-account-share \
  --resource-arns "arn:aws:vpc-lattice:us-east-1:123456789012:servicenetwork/sni-aaa111" \
  --principals 999999999999
```

### Step 2: Accept the invitation in the consumer account

```bash
# In account 999999999999
aws ram get-resource-share-invitations \
  --query 'resourceShareInvitations[?status==`PENDING`]'

aws ram accept-resource-share-invitation \
  --resource-share-invitation-arn <invitation-arn>
```

### Step 3: Associate the consumer VPC with the shared service network

```bash
# In account 999999999999
aws vpc-lattice create-service-network-vpc-association \
  --service-network-identifier sni-aaa111 \
  --vpc-identifier vpc-cross-acct-222
```

### Step 4: Put the service policy allowing cross-account invocation

(Covered above.)

**All four steps are required.** Missing any step results in
AccessDenied when the consumer account tries to invoke the service.

## Access log delivery

### CloudWatch Logs

```bash
aws vpc-lattice put-access-log-subscription \
  --resource-identifier sni-aaa111 \
  --service-network-log-type SERVICE \
  --log-destination '{
    "provider": "cloudwatch",
    "destinationArn": "arn:aws:logs:us-east-1:123456789012:log-group:/aws/vpc-lattice"
  }'
```

The log group must exist before creating the subscription. Lattice
writes JSON-formatted access logs to the group.

### S3 bucket

```bash
aws vpc-lattice put-access-log-subscription \
  --resource-identifier sni-aaa111 \
  --service-network-log-type SERVICE \
  --log-destination '{
    "provider": "s3",
    "destinationArn": "arn:aws:s3:::my-lattice-logs",
    "prefix": "lattice/"
  }'
```

The S3 bucket must exist and have a bucket policy allowing Lattice to
write. Lattice writes gzipped JSON log files to the prefix.

### Log fields

Access logs include: timestamp, service name, service DNS, listener
name, rule name, target group name, HTTP method, request path, response
status code, request bytes, response bytes, latency (ms), source IP,
destination IP, and Lattice trace ID.

### Log types

- `SERVICE`: logs for all services in the service network.
- `SERVICE_NETWORK`: aggregate logs at the service network level.

## Common auth pitfalls

1. **Trying to scope auth per rule.** Impossible in VPC Lattice. Auth
   policy is at the service level. Need different auth per path? Create
   separate services.

2. **Forgetting to set auth type.** Even if you PUT an auth policy, the
   service auth type must be `AWS_IAM` for enforcement. Use
   `update-service --body '{"authType":"AWS_IAM"}'`.

3. **Missing RAM or service policy for cross-account.** Both are
   required. RAM shares the network; service policy allows invocation.
   Missing either = AccessDenied.

4. **ACM cert in wrong region for custom domain.** Custom domains
   require the ACM certificate in us-east-1, not the service's region.

5. **Access logs not appearing.** Log delivery is async (5-10 minutes
   delay). Verify the CloudWatch log group or S3 bucket exists and has
   the correct permissions.
