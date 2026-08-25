---
name: s3-object-lambda-deployer
description: 'Provisions S3 Object Lambda Access Points and the supporting transform Lambda function with production defaults: standard Access Point creation, Lambda function for GetObject response transformation (redact PII, enrich data, convert formats), Object Lambda AP creation, routing (Object Lambda AP → standard AP → S3), supported operations (GetObject, HeadObject, ListObjects, ListObjectVersions), multi-region Object Lambda, GetObjectACL, and range downloads. Emits READY_TO_DEPLOY / PREREQUISITES_MISSING with every item verified and copy-pasteable s3control / lambda / s3api commands. Use when transforming S3 objects on retrieval without maintaining a second copy. Triggers: S3 Object Lambda, transform GetObject, redact PII on retrieval, enrich S3 data, convert CSV to Parquet on read, Object Lambda access point, multi- region Object Lambda.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Live provisioning uses AWS CLI v2 with s3control (create-access-point, create-access-point-for-object-lambda, get-access-point-for-object-lambda, get-access-point-configuration- for-object-lambda), lambda (create-function, put-function- concurrency, put-function-event-invoke-config), iam (create-role, attach-role-policy), s3api (put-bucket-policy, get-bucket-policy), and cloudformation / terraform...
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Storage
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  when_to_use: Creating an S3 Object Lambda Access Point to transform objects on retrieval (redact PII, enrich data, convert formats), authoring the supporting transform Lambda function, configuring routing between the Object Lambda AP and a standard Access Point, enabling GetObject/HeadObject/ListObjects/ListObjectVersions operations on an Object Lambda AP, deploying multi-region Object Lambda for DR or latency, enabling GetObjectACL or range downloads, or generating IaC (CloudFormation / Terraform) for any of the above. Do NOT invoke for plain Access Points without Object Lambda (use s3-access-points-deployer), or for S3 on Outposts Object Lambda (not supported).
  activation_triggers: S3 Object Lambda, Object Lambda access point, transform GetObject, redact PII on retrieval, enrich S3 data on read, convert CSV to Parquet on read, Object Lambda with GetObjectACL, Object Lambda range download, multi-region Object Lambda, transformation configuration
  invocation_schema: 'Input: either (a) a bucket ARN/name + Object Lambda AP name + transform Lambda spec (function ARN or build-from-template), or (b) a multi-region Object Lambda spec (regions + per-region transform functions). Output: deterministic OBJECT_LAMBDA_SPEC / VERDICT / CHECKLIST / VERIFICATION_COMMANDS block per the STRICT output contract, where VERDICT is READY_TO_DEPLOY or PREREQUISITES_MISSING.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: aws, s3, s3-object-lambda, object-lambda, access-point, transform-on-read, pii-redaction, data-enrichment, format-conversion, lambda, multi-region, getobjectacl, range-download, cloudops, deploy
  tags: aws, s3, object-lambda, access-point, lambda, transform, deploy, storage
  dependencies: aws-orchestrator
---

# S3 Object Lambda Deployer

## What this skill does

Provisions S3 Object Lambda Access Points and the supporting transform
Lambda function with correct defaults. The skill walks a 9-step
procedure, surfaces the silent-failure modes unique to Object Lambda
(most dangerous: the Lambda function throttles surface as S3
`AccessDenied` to the client, not as a Lambda error; the supporting
standard AP must exist BEFORE the Object Lambda AP or creation
succeeds but routing breaks; CloudWatch logs land in a separate
log group prefixed `/aws/s3/`), and emits a READY_TO_DEPLOY checklist
verifying every item against actual state. The single most common
incident this skill prevents: an operator creates an Object Lambda AP
with no reserved concurrency on the transform function, traffic
spikes, Lambda throttles, and clients see S3-shaped `AccessDenied`
errors — operators blame S3 and file a ticket that goes nowhere
because the actual failure is in Lambda.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **Quick reference** | Provisioning summary (9 steps), verdict thresholds, dependency graph | Before any operation |
| **Activation keywords** | Phrases that route to this skill | Disambiguating routing |
| **Invocation contract** | Required literal labels in the response | Formatting the response |
| **Reasoning framework** | Why the 9-step order matters; routing semantics | Understanding the deploy model |
| **Dependency graph** | Which configs silently no-op without their prerequisite | Debugging "transform doesn't fire" |
| **Expert heuristic** | The throttle-as-AccessDenied trap; routing chain; concurrency budget | Pre-empt production incidents |
| **Prerequisites** | What to verify before emitting any command | Avoid PREREQUISITES_MISSING rework |
| **9-step procedure** | The actual provisioning with copy-pasteable CLI | Executing the deploy |
| **NEVER (top 5)** | Hard rules that prevent silent exposure / data-plane bugs | Review before deploy |
| **STRICT output contract** | Required OBJECT_LAMBDA_SPEC / VERDICT / CHECKLIST / VERIFICATION_COMMANDS block | Formatting the response |
| **Recent AWS features** | GetObjectACL, range downloads, multi-region Object Lambda | Stay current |

## Quick reference — provisioning summary (9 steps)

| Step | Action | Reversible? | Key risk if skipped |
|---|---|---|---|
| 1 | Confirm bucket baseline (BPA, SSE, versioning) | — | Object Lambda inherits bucket weaknesses |
| 2 | Create or confirm the supporting standard Access Point | Yes | **Object Lambda AP creation succeeds but routing breaks** if AP missing |
| 3 | Create or confirm the IAM execution role for the transform Lambda | Yes | Lambda cannot read GetObject context without `s3-object-lambda` trust |
| 4 | Author the transform Lambda function (GetObject → transform → write back) | Yes | malformed response → client sees truncated/empty object, no error |
| 5 | Set reserved concurrency on the transform Lambda | Yes | **throttle surface as S3 AccessDenied — clients blame S3** |
| 6 | Create the Object Lambda Access Point | Yes | wrong SupportingAccessPoint ARN → silent routing failure |
| 7 | Attach the TransformationConfiguration (Lambda ARN + operations) | Yes | operations not enabled → transform silently not invoked for that op |
| 8 | Optional: multi-region Object Lambda / GetObjectACL / range downloads | Yes | see per-feature silent failures |
| 9 | Verify every configuration item against actual state + emit checklist | — | silent no-ops |

**Critical ordering constraints:** bucket baseline before standard AP
(Object Lambda inherits bucket-level weaknesses); standard AP BEFORE
Object Lambda AP (the OLAP references the standard AP ARN, and the API
does not always reject a forward reference cleanly); IAM role BEFORE
Lambda function creation; Lambda function BEFORE Object Lambda AP
creation (the OLAP creation references the Lambda ARN); reserved
concurrency BEFORE traffic starts (the throttle-as-AccessDenied trap).
Rationale and the silent-failure table are below.

## Activation keywords

S3 Object Lambda, Object Lambda Access Point, OLAP, transform GetObject,
redact PII on retrieval, mask PII on read, enrich S3 data on read,
convert CSV to Parquet on read, transform-on-read, supporting Access
Point, TransformationConfiguration, Object Lambda routing chain, Object
Lambda concurrency, multi-region Object Lambda, Object Lambda with
GetObjectACL, Object Lambda range download, GetObject transform,
HeadObject transform, ListObjects transform, ListObjectVersions
transform, WriteGetObjectResponse.

## Invocation contract (hard requirement)

When this skill is invoked with an S3 Object Lambda provisioning
request, the agent MUST respond with the checklist defined in
§"STRICT output contract" using the literal all-caps labels
`OBJECT_LAMBDA_SPEC:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels
breaks automation silently.

## Reasoning framework (why the provisioning order matters)

S3 Object Lambda looks like "Lambda runs on GetObject." The underlying
model has four traps:

1. **The routing chain has three hops, each a separate failure
   surface.** Request → Object Lambda AP → supporting standard AP → S3
   bucket. The transform Lambda is invoked synchronously between the
   AP hop and the S3 hop. A failure at any hop produces an S3-shaped
   error. Operators who see `AccessDenied` assume the bucket policy is
   wrong — the actual failure is often Lambda throttling at hop 2.

2. **The transform Lambda uses `WriteGetObjectResponse`, not a return
   value.** Operators author a Lambda that `return`s the transformed
   body. The Lambda runs, exits cleanly, and the client receives an
   empty object — no error surfaced. The correct API is
   `s3:WriteGetObjectResponse`.

3. **The transform Lambda receives a presigned GetObject URL, not the
   object body.** The Lambda must fetch the original object from the
   presigned URL, transform it, and write it back via
   `WriteGetObjectResponse`. Operators who expect "S3 hands me the body
   in the event" produce transforms that operate on `undefined`.

4. **Concurrency budget is the throughput ceiling.** Object Lambda
   invokes the transform function synchronously on every GET. There is
   no S3-side queue. At throttle, clients see S3-shaped errors
   (`AccessDenied`, `SlowDown`), NOT Lambda `ThrottledException`.

## Dependency graph (silent-failure table)

| Configuration | Hard dependencies (API error without) | Silent failure mode (returns 200, does nothing) | Enables downstream |
|---|---|---|---|
| Supporting standard Access Point | bucket exists in same region | **OLAP creation with forward-ref AP ARN may succeed at API but routing returns 404 to client** | OLAP routing |
| Object Lambda AP | standard AP exists; Lambda ARN in same region | wrong SupportingAccessPoint region → routing returns 404; CloudWatch shows no transform invocations | transform-on-read |
| TransformationConfiguration | OLAP exists; Lambda ARN valid | **operations list omits HeadObject → HeadObject bypasses transform silently; client gets raw metadata** | per-op transforms |
| Transform Lambda IAM role | trust policy `s3-object-lambda.amazonaws.com`; perm `s3-object-lambda:WriteGetObjectResponse` | role lacks `WriteGetObjectResponse` → Lambda exits cleanly, client gets empty object, no error | transform invocation |
| Transform Lambda code | uses `WriteGetObjectResponse` API | **Lambda `return`s body instead of writing → client gets empty object, no error** | correct transform |
| Lambda reserved concurrency | function exists | **concurrency exhausted → client sees S3 AccessDenied, NOT Lambda ThrottledException; operators blame S3** | throughput ceiling |
| Object Lambda AP policy | OLAP exists | policy references wrong ARN format → matches nothing; clients get AccessDenied regardless of intent | client scoping |
| Multi-region Object Lambda | per-region OLAP in each region | client routed to wrong-region OLAP → reads stale or no data; no cross-region replication by default | DR / latency |
| Range download (`Range` header) | TransformationConfiguration enables it; Lambda handles `Range` | Lambda ignores `Range` → returns full object; client billed for full GET, no error | partial GETs |

**The four silent-failure rows are the ones a baseline model misses.**
Missing operations in TransformationConfiguration, missing
`WriteGetObjectResponse` permission, return-vs-write confusion, and
concurrency exhaustion all return success or S3-shaped errors and
only post-config verification (Step 9) catches the gap. This is why
the procedure verifies every item rather than trusting the API
response.

## Expert heuristic: the throttle-as-AccessDenied trap

The most dangerous Object Lambda misconfiguration: no reserved
concurrency on the transform function.

```text
Operator thinks:              What actually happens:
Traffic spike →               Lambda throttles at account concurrency
S3 will queue/retry       →   ceiling; S3 has NO queue for Object
                               Lambda invocations; the client receives
                               an S3-shaped AccessDenied or SlowDown;
                               the operator's CloudWatch S3 metrics
                               show 5xx; they blame S3.
```

The tell-tale signal: `AccessDenied` from the Object Lambda AP hostname
that correlates with Lambda `Throttles` metrics, not with bucket-policy
denials. Remedy: set reserved concurrency equal to expected peak GET
rate BEFORE traffic starts; alarm on Lambda `Throttles` and `Errors`;
log the original GET ARN for correlation. The transform Lambda's
concurrency budget IS the access point's throughput ceiling — there is
no S3-side backstop.

## Expert heuristic: the WriteGetObjectResponse API

The transform Lambda does NOT return the transformed body. It calls
`WriteGetObjectResponse` with the transformed payload, status, and
headers. Operators who author a Lambda that `return`s the body
produce a function that runs cleanly (no error) and a client that
receives an empty object — the silent failure surface.

```python
# WRONG — return does nothing; client gets empty object
def handler(event, context):
    obj = fetch_from_presigned_url(event)
    return {"body": transform(obj)}   # silently dropped

# CORRECT — WriteGetObjectResponse writes back to S3 Object Lambda
def handler(event, context):
    obj = fetch_from_presigned_url(event)
    transformed = transform(obj)
    s3.write_get_object_response(
        RequestRoute=event["requestRoute"],
        RequestToken=event["getRequest"]["token"],
        Body=transformed
    )
```

The `RequestRoute` and `RequestToken` come from the event payload and
are required for `WriteGetObjectResponse` to route the response back
to the waiting client. Omitting either produces a Lambda that exits
cleanly with no client response.

## Expert heuristic: the routing chain and the standard AP

The routing chain for an Object Lambda GET is:

```text
Client → Object Lambda AP hostname
              ↓ (synchronous invoke)
         Transform Lambda
              ↓ (presigned GetObject URL)
         Supporting Standard AP → S3 bucket
              ↓ (object body)
         Transform Lambda (transforms body)
              ↓ (WriteGetObjectResponse)
         Object Lambda AP → Client
```

Three operational truths:

1. **The supporting standard AP must exist BEFORE the OLAP.** The OLAP
   creation references the standard AP ARN. If the standard AP is
   missing or in a different region, the OLAP may create but every GET
   returns 404 with no clear error.

2. **The standard AP's policy controls whether the OLAP can read.**
   The transform Lambda assumes a role that calls GetObject on the
   standard AP. The AP policy MUST allow the Lambda's role; otherwise
   the presigned URL fetch fails with AccessDenied.

3. **The OLAP policy controls which clients can invoke the transform.**
   This is a separate document from the standard AP policy. Operators
   who conflate the two produce either an open OLAP or a dead OLAP.

## Prerequisites (verify before provisioning)

Before emitting any provisioning command, verify these prerequisites.
If any are missing, the verdict is **PREREQUISITES_MISSING** with a
specific gap citation.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Bucket exists and meets baseline | Object Lambda inherits bucket-level weaknesses (no BPA, no SSE) | `aws s3api get-public-access-block`, `get-bucket-encryption` |
| Standard Access Point exists (or will be created) | The OLAP references the standard AP ARN; missing AP breaks routing | `aws s3control get-access-point --account-id <ACCOUNT> --name <AP_NAME>` |
| Lambda function ARN (existing or to be created) | The OLAP's TransformationConfiguration references the Lambda ARN | `aws lambda get-function --function-name <FUNC>` |
| IAM execution role with `s3-object-lambda` trust | Lambda must be assumable by `s3-object-lambda.amazonaws.com` | `aws iam get-role --role-name <ROLE>` |
| Lambda role policy includes `WriteGetObjectResponse` | Without it the Lambda exits cleanly, client gets empty object | `aws iam list-attached-role-policies` / `list-role-policies` |
| Account ID | Required for OLAP ARN construction | `aws sts get-caller-identity --query Account --output text` |
| Region | OLAP and supporting AP must be in same region | `aws configure get region` |
| Expected peak GET rate (for concurrency) | Reserved concurrency must be set before traffic | application knowledge / `get-metric-statistics` on GetObject |
| Source bucket in each region (multi-region only) | Multi-region OLAP requires per-region source buckets | `aws s3api list-buckets --region <REGION>` per region |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## 9-step provisioning procedure

### Step 1 — Confirm bucket baseline

An Object Lambda AP does NOT remediate bucket-level weaknesses. Before
creating the OLAP, confirm the underlying bucket meets the production
baseline: Block Public Access (account + bucket), default encryption
(SSE-S3 or SSE-KMS with BucketKeyEnabled), and versioning if the
workload needs non-current version transforms. See the
s3-secure-bucket-deployer skill for the bucket baseline procedure.

```bash
aws s3api get-public-access-block --bucket <BUCKET>
aws s3api get-bucket-encryption --bucket <BUCKET>
aws s3api get-bucket-versioning --bucket <BUCKET>
```

**Common mistake:** skipping this step because "the OLAP will enforce
access." The OLAP policy controls who invokes the transform; bucket-level
controls still apply cumulatively.

### Step 2 — Create or confirm the supporting standard Access Point

The OLAP references a standard AP ARN (NOT the bucket ARN directly).
Create the standard AP first if it does not exist.

```bash
# Create standard AP (Internet origin is typical for OLAP)
aws s3control create-access-point \
  --account-id <ACCOUNT_ID> --name <STANDARD_AP_NAME> --bucket <BUCKET>

# Attach a policy allowing the Lambda's role to GetObject
aws s3control put-access-point-policy \
  --account-id <ACCOUNT_ID> --name <STANDARD_AP_NAME> \
  --policy file://ap-policy.json
```

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"AWS": "arn:aws:iam::<ACCOUNT>:role/<LAMBDA_ROLE>"},
    "Action": ["s3:GetObject", "s3:GetObjectVersion"],
    "Resource": "arn:aws:s3:<REGION>:<ACCOUNT>:accesspoint/<STANDARD_AP_NAME>/*"
  }]
}
```

**Common mistake:** creating the OLAP with a forward-reference to a
standard AP that does not yet exist. The OLAP creation may succeed
but every GET returns 404. Always verify
`get-access-point` returns the standard AP BEFORE creating the OLAP.

### Step 3 — Create or confirm the IAM execution role

```bash
aws iam create-role \
  --role-name <LAMBDA_ROLE> \
  --assume-role-policy-document file://trust-policy.json
```

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "s3-object-lambda.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
```

The role's permission policy MUST include
`s3-object-lambda:WriteGetObjectResponse`. Without it, the Lambda
exits cleanly and the client receives an empty object — no error.

```bash
aws iam put-role-policy \
  --role-name <LAMBDA_ROLE> \
  --policy-name ObjectLambdaExec \
  --policy-document file://exec-policy.json
```

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {"Effect": "Allow", "Action": "s3-object-lambda:WriteGetObjectResponse", "Resource": "*"},
    {"Effect": "Allow", "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"], "Resource": "arn:aws:logs:<REGION>:<ACCOUNT>:*"},
    {"Effect": "Allow", "Action": ["s3:GetObject", "s3:GetObjectVersion"], "Resource": "arn:aws:s3:<REGION>:<ACCOUNT>:accesspoint/<STANDARD_AP_NAME>/*"}
  ]
}
```

**Common mistake:** trusting only `lambda.amazonaws.com` in the trust
policy. Object Lambda invocations come from
`s3-object-lambda.amazonaws.com` — a service-linked invocation path
distinct from standard Lambda triggers.

### Step 4 — Author the transform Lambda function

The transform Lambda receives an event with a presigned GetObject URL,
fetches the original object, transforms it, and writes the result back
via `WriteGetObjectResponse`. The Lambda MUST call
`WriteGetObjectResponse`; returning the body does nothing.

```bash
aws lambda create-function \
  --function-name <FUNC_NAME> \
  --runtime python3.12 \
  --role arn:aws:iam::<ACCOUNT>:role/<LAMBDA_ROLE> \
  --handler index.handler \
  --zip-file fileb://transform.zip \
  --timeout 30 --memory-size 512
```

```python
# transform.py — PII redaction example
import boto3, urllib.request, re

s3 = boto3.client("s3")

def handler(event, context):
    # Fetch the original object via the presigned URL
    presigned_url = event["getObjectContext"]["inputS3Url"]
    with urllib.request.urlopen(presigned_url) as resp:
        body = resp.read().decode("utf-8")

    # Transform: redact SSN pattern
    transformed = re.sub(r"\d{3}-\d{2}-\d{4}", "***-**-****", body)

    # Write back via WriteGetObjectResponse (NOT return)
    s3.write_get_object_response(
        RequestRoute=event["getObjectContext"]["outputRoute"],
        RequestToken=event["getObjectContext"]["outputToken"],
        Body=transformed
    )
```

**Common mistake:** using `event["requestRoute"]` and
`event["getRequest"]["token"]` (older docs). The current event schema
uses `event["getObjectContext"]["outputRoute"]` and
`event["getObjectContext"]["outputToken"]`. Verify the event structure
in CloudWatch Logs before relying on a specific key path.

### Step 5 — Set reserved concurrency on the transform Lambda

```bash
aws lambda put-function-concurrency \
  --function-name <FUNC_NAME> \
  --reserved-concurrent-executions 50
```

The reserved concurrency value IS the access point's throughput
ceiling. Set it equal to the expected peak GET rate. Alarm on Lambda
`Throttles` and `Errors`. Without it, a traffic spike throttles the
Lambda and clients see S3-shaped `AccessDenied`.

### Step 6 — Create the Object Lambda Access Point

```bash
aws s3control create-access-point-for-object-lambda \
  --account-id <ACCOUNT_ID> --name <OLAP_NAME> \
  --configuration SupportingAccessPoint=arn:aws:s3:<REGION>:<ACCOUNT>:accesspoint/<STANDARD_AP_NAME>
```

**Common mistake:** using the bucket ARN or bucket name as the
`SupportingAccessPoint` value. The value MUST be the standard AP ARN
(`arn:aws:s3:<region>:<account>:accesspoint/<name>`), NOT the bucket
ARN.

### Step 7 — Attach the TransformationConfiguration

```bash
aws s3control put-access-point-configuration-for-object-lambda \
  --account-id <ACCOUNT_ID> --name <OLAP_NAME> \
  --configuration '{
    "SupportingAccessPoint": "arn:aws:s3:<REGION>:<ACCOUNT>:accesspoint/<STANDARD_AP_NAME>",
    "TransformationConfigurations": [{
      "Actions": ["GetObject"],
      "ContentTransformation": {"AwsLambda": {"FunctionArn": "arn:aws:lambda:<REGION>:<ACCOUNT>:function:<FUNC_NAME>"}}
    }]
  }'
```

For multi-operation transforms (GetObject + HeadObject + ListObjects +
ListObjectVersions), add each action explicitly:

```json
"TransformationConfigurations": [
  {"Actions": ["GetObject"], "ContentTransformation": {"AwsLambda": {"FunctionArn": "arn:aws:lambda:<REGION>:<ACCOUNT>:function:<FUNC_NAME>"}}},
  {"Actions": ["HeadObject"], "ContentTransformation": {"AwsLambda": {"FunctionArn": "arn:aws:lambda:<REGION>:<ACCOUNT>:function:<FUNC_HEAD>"}}}
]
```

**Common mistake:** omitting `HeadObject` from the actions list. A
client issuing `HeadObject` against the OLAP gets the raw metadata
(no transform) with no error surfaced — the transform silently does
not apply to that operation.

### Step 8 — Optional: multi-region / GetObjectACL / range downloads

#### 8a. Multi-region Object Lambda

For DR or latency, deploy a per-region OLAP in each region with a
per-region transform Lambda. There is no built-in cross-region
replication for OLAPs — each OLAP is region-scoped and routes to a
standard AP in the same region.

```bash
# Repeat Steps 2-7 in each region
for REGION in us-east-1 eu-west-1 ap-southeast-2; do
  aws s3control create-access-point-for-object-lambda \
    --account-id <ACCOUNT_ID> --name <OLAP_NAME> --region $REGION \
    --configuration SupportingAccessPoint=arn:aws:s3:$REGION:<ACCOUNT>:accesspoint/<STANDARD_AP_NAME>
done
```

**Common mistake:** expecting the OLAP to failover across regions.
Each OLAP is independent; client-side routing (Route 53 latency-based
or geolocation-based) is required.

#### 8b. Object Lambda with GetObjectACL

To transform ACL responses, add `GetObjectACL` to the actions list
and author a Lambda that handles the ACL event shape:

```json
{"Actions": ["GetObjectACL"], "ContentTransformation": {"AwsLambda": {"FunctionArn": "arn:aws:lambda:<REGION>:<ACCOUNT>:function:<FUNC_ACL>"}}}
```

The ACL transform Lambda receives a different event shape than the
GetObject transform — verify the event structure in CloudWatch Logs
before authoring.

#### 8c. Range downloads

For range downloads (`Range: bytes=0-1023` header), the transform
Lambda must handle the `Range` header and return only the requested
byte range. The presigned URL includes the range; the Lambda fetches
the ranged bytes, transforms them, and writes back via
`WriteGetObjectResponse` with the appropriate `ContentRange` header.

**Common mistake:** ignoring the `Range` header and returning the full
object. The client is billed for the full GET and the range semantics
are silently broken.

### Step 9 — Verification

Run every verification command and confirm each output matches the
expected state.

```bash
aws s3control get-access-point --account-id <ACCOUNT_ID> --name <STANDARD_AP_NAME>
aws s3control get-access-point-policy --account-id <ACCOUNT_ID> --name <STANDARD_AP_NAME>
aws s3control get-access-point-for-object-lambda --account-id <ACCOUNT_ID> --name <OLAP_NAME>
aws s3control get-access-point-configuration-for-object-lambda --account-id <ACCOUNT_ID> --name <OLAP_NAME>
aws lambda get-function --function-name <FUNC_NAME>
aws lambda get-function-concurrency --function-name <FUNC_NAME>
# Invoke a real GET against the OLAP hostname and verify the transform fires
aws s3api get-object --bucket arn:aws:s3-object-lambda:<REGION>:<ACCOUNT>:accesspoint/<OLAP_NAME> --key sample.txt output.txt
aws cloudwatch get-metric-statistics --namespace AWS/Lambda --metric-name Invocations \
  --dimensions Name=FunctionName,Value=<FUNC_NAME> \
  --start-time $(date -u -v1H +%Y-%m-%dT%H:%M:%SZ) --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 --statistics Sum
```

For multi-region OLAP, verify each region independently with
`get-access-point-for-object-lambda --region <REGION>`.

## NEVER do these things

These anti-patterns cause silent exposure, data-plane bugs, or
compliance violations. Each is observed in real production incidents
— the "why it's wrong" line is the post-mortem finding.

1. **NEVER deploy an Object Lambda AP without reserved concurrency on
   the transform function.** Why it's wrong: Object Lambda invokes
   synchronously; the function's concurrency budget IS the AP's
   throughput ceiling. At throttle, clients see S3-shaped errors
   (`AccessDenied`, `SlowDown`) — operators blame S3. Set reserved
   concurrency + a CloudWatch alarm on Lambda `Throttles`.

2. **NEVER author a transform Lambda that `return`s the body instead
   of calling `WriteGetObjectResponse`.** Why it's wrong: the Lambda
   runs, exits cleanly, and the client receives an empty object with
   no error surfaced. The correct API is `WriteGetObjectResponse`
   with `RequestRoute` and `RequestToken` from the event payload.

3. **NEVER create the OLAP before the supporting standard Access
   Point.** Why it's wrong: the OLAP references the standard AP ARN,
   and creation may succeed against a forward reference. Every GET
   then returns 404 with no clear error. Always verify the standard
   AP with `get-access-point` BEFORE creating the OLAP.

4. **NEVER omit operations from the TransformationConfiguration and
   assume they are silently skipped.** Why it's wrong: operations
   not listed (e.g., HeadObject, ListObjects) bypass the transform
   silently — the client gets the raw response with no error. The
   transform appears to "not fire" for those operations while the
   OLAP is technically healthy.

5. **NEVER trust only `lambda.amazonaws.com` in the execution role's
   trust policy.** Why it's wrong: Object Lambda invocations come from
   `s3-object-lambda.amazonaws.com`, a distinct service-linked path.
   The Lambda may appear to have the right permissions but fail to be
   assumed on invocation.

## Output format

```
OBJECT_LAMBDA_SPEC: <olap-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Bucket baseline (BPA, SSE, versioning): verified
  [✓|✗] Supporting standard AP: created (<STANDARD_AP_NAME>) with Lambda-read policy
  [✓|✗] IAM execution role: trust=s3-object-lambda, perms include WriteGetObjectResponse
  [✓|✗] Transform Lambda: authored (runtime, handler, uses WriteGetObjectResponse)
  [✓|✗] Reserved concurrency: set (<n>) to expected peak GET rate
  [✓|✗] Object Lambda AP: created, SupportingAccessPoint=<STANDARD_AP_NAME> ARN
  [✓|✗] TransformationConfiguration: operations=[GetObject, HeadObject, ...]
  [✓|✗] Optional: multi-region | GetObjectACL | range downloads | none
VERIFICATION_COMMANDS:
  <copy-pasteable verification commands>
```

## STRICT output contract

The rules below are hard constraints. Violating any one produces a
checklist that looks complete but contains a silent misconfiguration.
Self-check EVERY emitted block against these rules before returning.

### Required output structure

Every response MUST be a single block using these literal labels, in
this order. Do NOT preface with prose, headings, or disclaimers.

```text
OBJECT_LAMBDA_SPEC: <olap-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Bucket baseline (BPA, SSE, versioning): verified
  [✓|✗] Supporting standard AP: created (<STANDARD_AP_NAME>) with Lambda-read policy
  [✓|✗] IAM execution role: trust=s3-object-lambda, perms include WriteGetObjectResponse
  [✓|✗] Transform Lambda: authored (runtime, handler, uses WriteGetObjectResponse)
  [✓|✗] Reserved concurrency: set (<n>) to expected peak GET rate
  [✓|✗] Object Lambda AP: created, SupportingAccessPoint=<STANDARD_AP_NAME> ARN
  [✓|✗] TransformationConfiguration: operations=[GetObject, HeadObject, ...]
  [✓|✗] Optional: multi-region | GetObjectACL | range downloads | none
VERIFICATION_COMMANDS:
  <copy-pasteable verification commands — one per [✓] item>
```

### Decision tree: Object Lambda deployment path

```text
Object Lambda — START
  │
  Q1: Transform objects on READ (not write)?
  ├── NO  → Use S3 Batch Operations or Lambda on upload (not Object Lambda)
  └── YES → Q2
  │
  Q2: Is the transform per-request (different output per caller / role)?
  ├── NO  → Pre-materialize a transformed copy (cheaper for static transforms)
  └── YES → Q3
  │
  Q3: Will peak GET rate exceed the Lambda concurrency budget?
  ├── YES → Set reserved concurrency BEFORE traffic; add CloudFront caching
  │         at edge to reduce origin GETs (cache TTL = transform freshness)
  └── NO  → Q4
  │
  Q4: Need HeadObject / ListObjects transforms beyond GetObject?
  ├── YES → Add each operation to TransformationConfiguration explicitly
  └── NO  → Q5
  │
  Q5: Multi-region DR or latency required?
  ├── YES → Per-region OLAP + per-region Lambda + Route 53 latency routing
  └── NO  → Single-region OLAP; optional CloudFront for edge caching
             CloudFront: origin = OLAP hostname, CachePolicy includes
             headers needed by transform, TTL based on transform freshness
```

### FORBIDDEN output patterns

1. **NEVER emit `VERDICT: READY_TO_DEPLOY` without showing ALL 8
   checklist items.** Every item MUST appear with a status marker:
   `[✓]` (applied and verified), `[✗]` (not applied or misconfigured),
   or `[OPTIONAL]` (not needed for this workload). Omitting a row
   implies it was not evaluated.

2. **NEVER mark Transform Lambda as `[✓]` without confirming the code
   calls `WriteGetObjectResponse`.** A Lambda that `return`s the body
   produces a function that runs cleanly and a client that receives
   an empty object. The verification MUST cite `WriteGetObjectResponse`
   in the rationale.

3. **NEVER mark Reserved concurrency as `[✓]` without a specific
   number.** A bare `[✓]` with no concurrency value implies the
   default (account-level unreserved), which is the
   throttle-as-AccessDenied trap. The value MUST be cited.

4. **NEVER mark TransformationConfiguration as `[✓]` without listing
   the operations.** Operations not listed bypass the transform
   silently. The verification MUST include the explicit operations
   list (e.g., `[GetObject, HeadObject]`).

5. **NEVER mark the supporting standard AP as `[✓]` without confirming
   the AP policy allows the Lambda's role.** Without read permission,
   the presigned URL fetch fails with AccessDenied — the transform
   never runs. The verification MUST include `get-access-point-policy`.

6. **NEVER emit `VERDICT: PREREQUISITES_MISSING` without citing the
   specific gap.** Each `[✗]` item MUST have a one-line reason:
   `[✗] Lambda role missing s3-object-lambda:WriteGetObjectResponse
   — add permission before deploy`. A bare `[✗]` with no explanation
   is non-compliant.

7. **NEVER deploy an Object Lambda AP behind CloudFront without
   confirming the cache behavior accounts for transform output
   variance.** CloudFront caches the OLAP response; if the transform
   produces role-specific output (e.g., PII redaction varies by
   caller), caching MUST be disabled or keyed on the authorization
   header. A single cached response served to all callers defeats the
   per-request transform and can leak data across principals.

### Perfect example output — READY_TO_DEPLOY

Scenario: CSV-to-JSON transformation on retrieval. Analysts query S3
CSV reports via BI tools; the Object Lambda AP converts CSV to JSON
on the fly. CloudFront sits in front for edge caching (CSV refreshes
hourly, cache TTL = 3600s). Reserved concurrency = 100 for peak load.

```text
OBJECT_LAMBDA_SPEC: csv-json-olap
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Bucket baseline: analytics-reports, BPA all 4 True, SSE-KMS, versioning Enabled
  [✓] Supporting standard AP: reports-std-ap with Lambda-read policy on
        arn:aws:iam::444455556666:role/olap-transform-exec
  [✓] IAM execution role: olap-transform-exec, trust=s3-object-lambda.amazonaws.com,
        perms include s3-object-lambda:WriteGetObjectResponse + s3:GetObject on
        arn:aws:s3:us-east-1:444455556666:accesspoint/reports-std-ap/*
  [✓] Transform Lambda: csv-to-json-fn (python3.12, index.handler,
        uses WriteGetObjectResponse; see Lambda code below)
  [✓] Reserved concurrency: 100 (expected peak ~80 GETs/sec)
  [✓] Object Lambda AP: csv-json-olap,
        SupportingAccessPoint=arn:aws:s3:us-east-1:444455556666:accesspoint/reports-std-ap
  [✓] TransformationConfiguration: operations=[GetObject]
  [✓] CloudFront: distribution E2Q1U3V5EXAMPLE, origin = OLAP hostname
        (csv-json-olap-444455556666.s3-object-lambda.us-east-1.amazonaws.com),
        DefaultTTL=3600 (CSV refreshes hourly), CachePolicy=CachingOptimized
  [OPTIONAL] Multi-region / GetObjectACL / range downloads: none
VERIFICATION_COMMANDS:
  aws s3control get-access-point --account-id 444455556666 --name reports-std-ap
  aws s3control get-access-point-policy --account-id 444455556666 --name reports-std-ap
  aws s3control get-access-point-for-object-lambda --account-id 444455556666 --name csv-json-olap
  aws s3control get-access-point-configuration-for-object-lambda --account-id 444455556666 --name csv-json-olap
  aws lambda get-function --function-name csv-to-json-fn
  aws lambda get-function-concurrency --function-name csv-to-json-fn
  aws cloudfront get-distribution-config --id E2Q1U3V5EXAMPLE
```

CSV-to-JSON transform Lambda (uses WriteGetObjectResponse, NOT return):

```python
import boto3, urllib.request, csv, io, json

s3 = boto3.client("s3")

def handler(event, context):
    # Fetch original CSV via the presigned URL from Object Lambda event
    presigned_url = event["getObjectContext"]["inputS3Url"]
    with urllib.request.urlopen(presigned_url) as resp:
        csv_body = resp.read().decode("utf-8")

    # Transform: CSV rows -> JSON array (one object per row)
    reader = csv.DictReader(io.StringIO(csv_body))
    json_output = json.dumps(list(reader), indent=2)

    # Write back via WriteGetObjectResponse (return is a silent no-op)
    s3.write_get_object_response(
        RequestRoute=event["getObjectContext"]["outputRoute"],
        RequestToken=event["getObjectContext"]["outputToken"],
        Body=json_output,
        ContentType="application/json"
    )
```

CloudFront integration (cache transform output at edge to reduce
Lambda invocations):

```bash
aws cloudfront create-distribution \
  --origin-domain-name csv-json-olap-444455556666.s3-object-lambda.us-east-1.amazonaws.com \
  --default-cache-behavior 'TargetOriginId=csv-json-olap-origin,ViewerProtocolPolicy=redirect-to-https,DefaultTTL=3600,MinTTL=0,MaxTTL=86400'
```

### Perfect example output — PREREQUISITES_MISSING

```text
OBJECT_LAMBDA_SPEC: pii-redact-olap
VERDICT: PREREQUISITES_MISSING
CHECKLIST:
  [✓] Bucket baseline: prod-data-lake, BPA all 4 True, SSE-KMS
  [✓] Supporting standard AP: dlake-team-a-ap with Lambda-read policy
  [✗] IAM execution role: trust policy only has lambda.amazonaws.com — add s3-object-lambda.amazonaws.com principal
  [✗] Transform Lambda: not yet authored — create function with WriteGetObjectResponse call
  [✗] Reserved concurrency: not set — Lambda will throttle under load and clients will see S3 AccessDenied
  [OPTIONAL] Object Lambda AP: pending (waiting on role + Lambda + TransformationConfiguration)
  [OPTIONAL] Multi-region / GetObjectACL / range downloads: none
VERIFICATION_COMMANDS:
  aws iam get-role --role-name olap-exec
  aws lambda list-functions --query 'Functions[?FunctionName==`pii-redact-fn`]`
```

**Self-check before emit:**
- [ ] All 8 checklist rows present (no omitted items)?
- [ ] Every `[✓]` has a matching verification command?
- [ ] Transform Lambda rationale cites `WriteGetObjectResponse`?
- [ ] Reserved concurrency has a specific number?
- [ ] TransformationConfiguration lists explicit operations?
- [ ] Supporting AP policy allows the Lambda role?
- [ ] CloudFront cache behavior accounts for transform output variance (if deployed behind CF)?
- [ ] Every `[✗]` cites the specific gap and what the operator must provide?

## Recent AWS features

- **Object Lambda with GetObjectACL**: transformation can be applied
  to ACL responses by adding `GetObjectACL` to the actions list. The
  ACL transform Lambda receives a different event shape — verify the
  event structure before authoring.
- **Range downloads via Object Lambda**: the transform Lambda can
  handle `Range` headers and return only the requested byte range. The
  Lambda must respect the `Range` header from the presigned URL and
  write back via `WriteGetObjectResponse` with `ContentRange`.
- **Multi-region Object Lambda**: per-region OLAPs in each region with
  per-region transform Lambdas. No built-in cross-region replication;
  client-side routing (Route 53 latency or geolocation) is required.
- **TransformationConfiguration for multiple operations**: a single
  OLAP can have separate TransformationConfigurations for GetObject,
  HeadObject, ListObjects, and ListObjectVersions — each routing to a
  different Lambda function.
- **Object Lambda runtime deprecation signals**: AWS guidance is to
  prefer S3 Batch Operations for transformation at write time when
  feasible; Object Lambda remains supported for transform-on-read.
- **CloudWatch Logs for Object Lambda**: transform Lambda logs land in
  `/aws/lambda/<func>`. Object Lambda wraps Lambda errors as S3 5xx —
  grep the Lambda log group, not S3 logs.
