# Eval prompt: timeout-http-client-no-connect

Diagnose the Lambda timeout for the following function. Walk the
timeout-focused diagnostic tree and emit the standard diagnostic block
(TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: `fn-http-client-no-connect` started failing after a partner
rotated their firewall rules. Every invocation now returns
`TaskTimeoutException` at exactly 10 s. Logs show the `axios.get` call
as the last line; no further output. The function is not VPC-attached.

```text
FunctionName: fn-http-client-no-connect
Qualifier: prod (version 4)
Runtime: nodejs20.x
Timeout: 10
MemorySize: 256
Handler: index.handler
VpcConfig: (none)

Function code (excerpt):
  const axios = require('axios');
  exports.handler = async (event) => {
    console.log('calling partner API');
    const res = await axios.get('https://api.partner.example.com/verify');
    console.log('partner responded', res.status);
    return { status: res.status };
  };

Recent log pattern (every invocation):
  INFO  calling partner API
  (no further log line)
  END RequestId: ... Duration: 10000.00 ms
    Memory Size: 256 MB Max Memory Used: 78 MB
  Task timed out after 10.00 seconds

CloudWatch metrics (last hour):
  - Duration p50: 10s, p99: 10s, Maximum: 10s
  - MemoryUtilization Maximum: 30%
  - Errors: 100%

Partner API context:
  - DNS resolves to 3.18.12.63 (verified)
  - TCP connect from EC2 in same region: SYN black-hole
    (firewalled after partner rotation)
```

`axios` ships with no default connect timeout; a firewalled host
consumes the entire Lambda budget on one SYN. Identify the layer and
recommend the fix.
