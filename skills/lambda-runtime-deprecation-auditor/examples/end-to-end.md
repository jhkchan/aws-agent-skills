# End-to-end usage scenario: lambda-runtime-deprecation-auditor

A walkthrough showing the skill auditing a Lambda function that has both
a deprecated runtime (nodejs16.x, Phase 2 blocked) and a public function
URL (AuthType NONE), demonstrating severity aggregation, the runtime
lifecycle concept, and the worst-finding-wins verdict logic.

## Input (user prompt)

> Review this Lambda function before we do a security sweep. It is one of
> our legacy API endpoints.

```json
{
  "Runtime": "nodejs16.x",
  "Handler": "index.handler",
  "PackageType": "Zip",
  "Architectures": ["x86_64"],
  "LastModified": "2023-08-10T10:00:00.000+0000",
  "TracingConfig": { "Mode": "Active" },
  "Timeout": 15,
  "MemorySize": 256
}
```

Execution role: `arn:aws:iam::111111111111:role/lambda-legacy-role`

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["dynamodb:GetItem"],
      "Resource": "arn:aws:dynamodb:us-east-1:111111111111:table/legacy-table"
    },
    {
      "Effect": "Allow",
      "Action": ["logs:CreateLogStream", "logs:PutLogEvents"],
      "Resource": "arn:aws:logs:us-east-1:111111111111:log-group:/aws/lambda/nodejs16-public-and-deprecated:*"
    }
  ]
}
```

Function URL config:

```json
{
  "FunctionUrl": "https://xyz789abc012.lambda-url.us-east-1.on.aws",
  "AuthType": "NONE",
  "Cors": { "AllowOrigins": ["*"], "AllowMethods": ["GET"] }
}
```

## Skill output

```text
FUNCTION: nodejs16-public-and-deprecated
VERDICT: DEPRECATED_RUNTIME
REASON: Runtime nodejs16.x is in Phase 2 block — invocations are already
failing with Runtime.UnsupportedException (Step 1). A public Function URL
(AuthType NONE) is a secondary finding that compounds the exposure.
FINDINGS:
  - [DEPRECATED_RUNTIME] nodejs16.x is blocked (Phase 2) — function
    invocations fail with Runtime.UnsupportedException. LastModified
    2023-08-10 (>180 days stale — likely forgotten, no update pipeline).
  - [PUBLIC_EXPOSURE] Function URL AuthType NONE at
    https://xyz789abc012.lambda-url.us-east-1.on.aws — publicly invocable
    by anyone on the internet (Step 2). (Downgraded in severity because
    the function is already non-functional from the runtime block.)
  - [OK] Execution role scoped to dynamodb:GetItem on a specific table +
    CloudWatch Logs (Step 3).
  - [OK] TracingConfig Active — X-Ray traces are being recorded (Step 4).
REMEDIATION:
  1. DEPRECATED_RUNTIME — Update the runtime immediately:
     aws lambda update-function-configuration
       --function-name nodejs16-public-and-deprecated
       --runtime nodejs20.x --profile <p>
     Test code compatibility first — Node 16 to 20 has breaking changes
     (e.g., removed url.parse, changes to crypto timingSafeEqual).
     Publish a new version and test before shifting traffic.
  2. PUBLIC_EXPOSURE — Once the function is updated, restrict the URL:
     aws lambda update-function-url-config
       --function-name nodejs16-public-and-deprecated
       --auth-type AWS_IAM --profile <p>
     If public access is required, add CloudFront + WAF for rate-limiting.
```

## What the skill caught that a generic assistant misses

1. **The runtime is not "old" — it is BLOCKED.** A generic assistant says
   "Node.js 16 is an older version, consider upgrading." The skill
   recognises that nodejs16.x is in Phase 2 — the function is already
   non-functional. Invocations are returning
   `Runtime.UnsupportedException`. This is an active outage, not a
   recommendation.

2. **Verdict priority: DEPRECATED over PUBLIC.** The function has a public
   URL (PUBLIC_EXPOSURE) AND a deprecated runtime. A naive auditor might
   flag the public URL as the headline. The skill recognises that a
   deprecated runtime outranks public exposure — a blocked function is
   already broken, making the public URL a secondary concern.

3. **The stale LastModified date is a risk amplifier.** The function was
   last touched in August 2023 (>180 days). The skill surfaces this
   because it indicates the team has no active deployment pipeline —
   upgrading the runtime requires reviving stale code, not a simple
   config change.

4. **The execution role is clean.** Despite the two high-severity
   findings, the role is correctly scoped to one DynamoDB table + Logs.
   The skill explicitly calls this out as OK so the operator knows the
   role does NOT need scoping work during the runtime fix.

## Slash-command invocation

```
/aws:audit-lambda-runtime-deprecation
```

Or via the orchestrator:

```
/aws:pipeline
You: "audit all my Lambda functions for deprecated runtimes"
```

The orchestrator emits
`[Phase: Audit | Skills routed: lambda-runtime-deprecation-auditor]` and
hands off to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "check my Lambda runtimes for deprecation"
# [Phase: Audit | Skills routed: lambda-runtime-deprecation-auditor]
```

## Live-account follow-up (optional, requires AWS CLI)

After remediating the runtime, validate the function posture:

```bash
# Verify the runtime was updated
aws lambda get-function-configuration \
  --function-name nodejs16-public-and-deprecated \
  --profile default --query 'Runtime'

# Verify the URL auth type was changed
aws lambda get-function-url-config \
  --function-name nodejs16-public-and-deprecated \
  --profile default --query 'AuthType'

# Sweep for other functions on deprecated runtimes
aws lambda list-functions --profile default --output json \
  | jq '.Functions[] | select(.Runtime == "python3.9" or .Runtime == "nodejs16.x" or .Runtime == "nodejs18.x") | .FunctionName'
```

Then monitor CloudWatch Logs for runtime errors for 24-48 hours after
the upgrade.
