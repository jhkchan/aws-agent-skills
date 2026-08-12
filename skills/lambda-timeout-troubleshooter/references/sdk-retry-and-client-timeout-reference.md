# SDK Retry and HTTP Client Timeout Reference

Supplementary reference for the Lambda Timeout Troubleshooter skill.
Loaded on-demand when a diagnostic needs SDK retry multiplier maths,
HTTP client default-timeout behaviour, or connect-vs-read timeout
semantics.

## AWS SDK retry behaviour by language

| SDK | Default mode | Default maxRetries | Backoff base | Backoff cap |
|---|---|---|---|---|
| AWS SDK v3 (Node) | standard | 3 | 100 ms | 20 s |
| AWS SDK v3 (Node) | adaptive | 3 | 100 ms | 20 s + client-side queue |
| boto3 (Python) | legacy | 3 (4 total attempts) | 100 ms | 20 s |
| boto3 (Python) | standard | 3 | 25 ms | 5 s |
| boto3 (Python) | adaptive | 3 | 25 ms | 5 s + token bucket |
| AWS SDK for Java v2 | standard | 3 | 100 ms | 20 s |
| AWS SDK for Go v2 | standard | 3 | 100 ms | 20 s |
| AWS SDK for .NET v3 | standard | 3 | 100 ms | 20 s |

### Retry budget multiplier maths

For `maxRetries: N`, the worst-case wall clock for a single SDK call
(assuming each attempt consumes the full per-attempt budget):

```
total = (N + 1) * requestTimeout + sum(backoff_i for i in 1..N)
```

Examples (assuming each attempt consumes the full `requestTimeout`):

| maxRetries | requestTimeout | Backoff sum (approx) | Total wall clock | Lambda Timeout headroom |
|---|---|---|---|---|
| 3 | 9000 ms | ~700 ms | ~36.7 s | exceeds 30 s |
| 3 | 5000 ms | ~700 ms | ~20.7 s | fits in 30 s |
| 2 | 5000 ms | ~300 ms | ~15.3 s | fits in 30 s |
| 0 | any | 0 | 1 * requestTimeout | maximum headroom |

**Recommendation:** on hot Lambda paths, set `maxAttempts: 0` (or 1)
and let Lambda async retries / Step Functions retries / SQS redrive
handle failure recovery at the right granularity.

### SDK config snippets

```javascript
// AWS SDK v3 (Node) — disable retries
const { DynamoDBClient } = require('@aws-sdk/client-dynamodb');
const client = new DynamoDBClient({ maxAttempts: 0 });
```

```python
# boto3 — disable retries
from botocore.config import Config
config = Config(retries={'max_attempts': 0})
client = boto3.client('dynamodb', config=config)
```

```java
// AWS SDK for Java v2 — disable retries
S3Client client = S3Client.builder()
    .overrideConfiguration(o -> o.retryPolicy(r -> r.numRetries(0)))
    .build();
```

```go
// AWS SDK for Go v2 — disable retries
client := s3.New(s3.Options{
    Retryer: aws.NoOpRetryer{},
})
```

## HTTP client default-timeout matrix

These defaults are dangerous on Lambda because a dead host consumes the
entire function Timeout on one TCP SYN.

| Client | Language | Default connect timeout | Default request timeout | Notes |
|---|---|---|---|---|
| axios | Node | none (system default ~75s on Linux) | none | Pass `{ timeout, proxy: false }` |
| Node fetch (undici) | Node | none | none | Pass `{ signal: AbortSignal.timeout(ms) }` |
| Node http.request | Node | none | none | Use `socket.setTimeout` and `setTimeout` |
| requests | Python | none (system default) | none | Pass `timeout=(connect, read)` tuple |
| urllib3 | Python | none | none | Pass `Timeout(connect=, read=)` |
| httpx | Python | 5 s | none | Pass `timeout=httpx.Timeout(connect, read, write, pool)` |
| Apache HttpClient | Java | none | none | Set `RequestConfig.custom().setConnectTimeout` |
| OkHttp | Java | 10 s | none | Pass `.connectTimeout` and `.readTimeout` |
| net/http | Go | 30 s (Dialer) | none (Client) | Pass `http.Client{Timeout: }` |

### Safe client configurations

```javascript
// axios — Node
const axios = require('axios');
const client = axios.create({
  timeout: 3000,        // total request budget (ms)
  proxy: false,         // avoid env-var proxy surprises on Lambda
});
// For connect-only: not directly tunable in axios; rely on timeout.
```

```javascript
// Node fetch (undici)
const res = await fetch(url, {
  signal: AbortSignal.timeout(3000),
});
```

```python
# requests — Python (connect, read) tuple
import requests
requests.get(url, timeout=(0.5, 3.0))
```

```python
# httpx — Python
import httpx
with httpx.Client(timeout=httpx.Timeout(3.0, connect=0.5)) as client:
    r = client.get(url)
```

```java
// OkHttp — Java
OkHttpClient client = new OkHttpClient.Builder()
    .connectTimeout(500, TimeUnit.MILLISECONDS)
    .readTimeout(3, TimeUnit.SECONDS)
    .build();
```

## Connect vs read vs write vs pool timeouts

| Timeout | Measures | Default behaviour if unset |
|---|---|---|
| connect | TCP handshake (SYN, SYN-ACK, ACK) | System default (~75 s on Linux, indefinite on some stacks) |
| TLS handshake | SSL/TLS negotiation after connect | Bound by connect/read |
| read (per-byte) | Time between bytes received | Often unset; falls back to request timeout |
| write (per-byte) | Time between bytes sent | Often unset |
| request (total) | Wall clock for the entire request | Often unset on Lambda-friendly clients |
| pool / acquire | Time to acquire a connection from the pool | Often unset |

**Rule of thumb for Lambda:** set total request timeout to
`< (Lambda Timeout / 2)` so a single downstream call can't consume the
whole budget. Set connect timeout to `< 1000 ms` — anything higher is
likely a dead host.

## SDK requestTimeout vs maxAttempts interaction

In AWS SDK v3:

- `requestTimeout` is the wall-clock cap per HTTP attempt (including
  connect, send, receive). Defaults vary by service client (~20-30 s
  for most).
- `maxAttempts` (formerly `maxRetries`) caps total attempts.
- The retry multiplier applies AFTER each `requestTimeout` exhaustion.

A function with `requestTimeout: 25000` and `maxAttempts: 4` (default 3
retries) can consume 100 s of wall clock on a single SDK call — far
beyond any reasonable Lambda Timeout. Always tune both together.

## Common timeout-misdiagnosis patterns

| Symptom | Misdiagnosis | Actual cause |
|---|---|---|
| Lambda times out; last log is SDK call | "Slow downstream" | SDK retry multiplier exhausting budget |
| Lambda times out; no logs | "Lambda service bug" | Init-phase timeout — handler never ran |
| Lambda times out; last log is HTTP call | "Partner API slow" | HTTP client has no connect timeout; dead host |
| Lambda times out; MaxMemoryUsed ≈ MemorySize | "Need higher Timeout" | OOM-before-timeout — raise memory |
| Step Functions `States.Timeout` | "Lambda timed out" | Task-level `TimeoutSeconds` < Lambda Timeout |
| API Gateway 504 | "Lambda failed" | Integration 29 s cap fired; Lambda still running |
