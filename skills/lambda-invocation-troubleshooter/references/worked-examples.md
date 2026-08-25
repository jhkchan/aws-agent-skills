# Worked Examples — Lambda Invocation Troubleshooter

Secondary worked examples and templates moved verbatim from SKILL.md.
Load on demand.

### Pre-flight — malformed input NEED_MORE_INFO output template

If the input is malformed (missing FunctionName, absent symptom
description, no caller context for live diagnosis), emit:

```text
TARGET: <function-name or unknown>
VERDICT: NEED_MORE_INFO
REASON: Input is missing required context — at minimum a symptom
  description (the error string or observed behaviour) and the
  FunctionName (with qualifier if the function uses aliases).
LAYER: UNKNOWN
EVIDENCE:
  - Missing: <list specific missing fields>
REMEDIATION: Re-prompt the operator for: (1) the exact error string or
  observed symptom, (2) the FunctionName and qualifier (alias or
  version), and (3) for live diagnosis, the invocation type (sync
  RequestResponse vs async Event) and the caller context (source ARN,
  source service).
```

### Worked example — OutOfMemory, memory raised


```text
TARGET: fn-image-resizer (alias: prod, version 7)
VERDICT: ROOT_CAUSE_FOUND
REASON: Function MemorySize is 256 MB; CloudWatch MemoryUtilization is
  100% on invocations with image payloads > 4 MB. Logs show
  "Runtime.ExitError: ErrorType: OutOfMemory" on the same invocations.
  The function reads the full image into memory for resizing (Step 3).
LAYER: MEMORY_CONFIG
EVIDENCE:
  - Symptom: invocations with image payloads > 4 MB fail; smaller
    payloads succeed.
  - Probe: aws logs filter-log-events returns "ErrorType: OutOfMemory"
    12 times in the last hour; all preceding log lines show
    "Processing image of size <4-8 MB>".
  - Probe: aws cloudwatch get-metric-statistics on AWS/Lambda
    MemoryUtilization Maximum = 100 for the same invocations.
  - Passing: function Timeout is 60s; Duration p99 is 1.2s (timeout is
    not the issue); function is not VPC-attached (network is not the
    issue).
REMEDIATION:
  1. Raise MemorySize to 1024 MB (≥4x the largest payload, with
     headroom for the resize operation):
     aws lambda update-function-configuration --function-name \
       fn-image-resizer --memory-size 1024 --profile <p>
  2. Publish a new version and shift the prod alias:
     aws lambda publish-version --function-name fn-image-resizer
     aws lambda update-alias --name prod --function-version <new>
  3. Verify with a 6 MB image payload; Duration should drop (CPU
     proportion triples) and Max Memory Used should be < 800 MB.
```

### Worked example — ESCALATE, regional Lambda incident


```text
TARGET: fn-prod-processor (alias: prod, version 42)
VERDICT: ESCALATE
REASON: Region-wide Lambda invocation failures in us-east-1; AWS Health
  event reports elevated 5xx rates and increased error rates for
  Lambda invoking functions in the region. Customer-side action cannot
  resolve a regional service degradation.
LAYER: UNKNOWN
EVIDENCE:
  - aws health describe-events returns an OPEN event for
    AWS_LAMBDA_SERVICE in us-east-1 starting 14 minutes ago.
  - Function config and recent deploys are unchanged.
  - Failures began at the AWS Health event start time across multiple
    unrelated functions in the account.
REMEDIATION:
  1. Monitor the AWS Health Dashboard for the event resolution
     announcement.
  2. If the function backs a user-facing API, enable failover to a
     different region if architecture permits.
  3. If impact persists beyond the AWS Health ETA, open a Support case
     quoting the AWS Health event ARN.
```
