# Advanced Patterns — S3 Object Lambda Deployer

Deep-dive material moved from SKILL.md for progressive disclosure (agentskills.io). Load on demand.
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

## Step 8: optional features - multi-region / GetObjectACL / range downloads

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

