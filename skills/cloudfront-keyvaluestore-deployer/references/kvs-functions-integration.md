# CloudFront Functions KVS API Integration — Detail Reference

Deep reference on the CloudFront Functions KVS runtime API, the
`cf.openKvs()` interface, function runtime requirements, KVS-to-function
linkage mechanics, and the read-only constraint. Loaded on demand by
the skill — kept out of the main SKILL.md body so the provisioning
procedure stays scannable.

## cloudfront-js-2.0 runtime

The `cloudfront-js-2.0` runtime is REQUIRED for KVS access. This
runtime introduced the `cloudfront` module with the `openKvs()` method.

### Runtime comparison

| Feature | cloudfront-js-1.0 | cloudfront-js-2.0 |
|---|---|---|
| KVS read access (`cf.openKvs()`) | No | Yes |
| ESM `import` syntax | No | Yes |
| `Math`, `Date`, `String` builtins | Yes | Yes |
| `JSON.parse` / `JSON.stringify` | Yes | Yes |
| `crypto` module | No | Limited |
| Max execution time | 1 ms | 1 ms |
| Max memory | 2 MB | 2 MB |

### Checking the runtime

```bash
aws cloudfront describe-function \
  --name "my-function" \
  --query 'FunctionSummary.FunctionConfig.Runtime'
# Expected: "cloudfront-js-2.0"
```

### Updating the runtime

If a function was created with `cloudfront-js-1.0`, you must update it
to `cloudfront-js-2.0` to use KVS. This requires `update-function` with
new function code AND a new function config:

```bash
aws cloudfront update-function \
  --name "my-function" \
  --if-match "$ETAG" \
  --function-config '{"Comment":"Updated for KVS","Runtime":"cloudfront-js-2.0"}' \
  --function-code fileb://function.js
```

After updating, you MUST `publish-function` again.

## cf.openKvs() API

The `cf.openKvs()` method returns a KVS handle for reading key-value
data at the edge.

### Import patterns

**ESM import (recommended for cloudfront-js-2.0):**

```javascript
import cf from 'cloudfront';

const kvs = cf.openKvs();  // opens the KVS linked to this function
```

**The KVS handle is a module-level constant.** Do NOT call `openKvs()`
inside the `handler` function — this would re-open the KVS on every
request, adding latency. Open it once at module scope.

### Methods

| Method | Signature | Returns | Notes |
|---|---|---|---|
| `get` | `kvs.get(key: string)` | `string \| undefined` | READ-ONLY. Returns `undefined` if key not found. |
| `has` | `kvs.has(key: string)` | `boolean` | Check key existence without reading value. |

There are NO `set`, `put`, or `delete` methods on the KVS handle. The
function CANNOT modify KVS data. All writes go through the AWS API.

### Return value semantics

- `kvs.get('existing-key')` returns the value as a string.
- `kvs.get('non-existent-key')` returns `undefined`.
- `kvs.get('Non-Existent-Key')` returns `undefined` (case-sensitive).
- The value is always a string. Numbers and booleans must be parsed
  in function code: `parseInt(kvs.get('percentage'), 10)`.

### Common pitfall: undefined vs empty string

```javascript
// WRONG: treats empty string as falsy
const value = kvs.get('flag');
if (value) { /* only runs if value is non-empty */ }

// CORRECT: explicitly check for undefined
const value = kvs.get('flag');
if (value !== undefined) { /* runs if key exists, even with empty value */ }
```

## KVS-function linkage

The KVS is linked to the function at creation or update time via the
`--key-value-store-associations` parameter. This is a FUNCTION-level
association, not a distribution-level one.

### Linking a KVS during function creation

```bash
aws cloudfront create-function \
  --name "my-function" \
  --function-config '{"Comment":"KVS-enabled function","Runtime":"cloudfront-js-2.0"}' \
  --function-code fileb://function.js \
  --key-value-store-associations '["arn:aws:cloudfront::123456789012:key-value-store/my-kvs-id"]'
```

### Linking a KVS during function update

```bash
aws cloudfront update-function \
  --name "my-function" \
  --if-match "$ETAG" \
  --function-config '{"Comment":"KVS-enabled function","Runtime":"cloudfront-js-2.0"}' \
  --function-code fileb://function.js \
  --key-value-store-associations '["arn:aws:cloudfront::123456789012:key-value-store/my-kvs-id"]'
```

### Multiple KVS per function

A function can be associated with multiple KVS stores:

```bash
--key-value-store-associations '["arn:...kvs-1", "arn:...kvs-2"]'
```

In function code, `cf.openKvs()` opens ALL linked stores as a single
merged view. If two stores have the same key, the behavior is undefined
— avoid key collisions across stores.

### Unlinking a KVS

To unlink, update the function with an empty associations list:

```bash
--key-value-store-associations '[]'
```

After unlinking, `cf.openKvs()` returns a handle where all `get()` calls
return `undefined`.

## Function lifecycle and publishing

| Stage | Where it runs | How to test |
|---|---|---|
| `DEVELOPMENT` | Only via `test-function` API | `aws cloudfront test-function --if-match <etag>` |
| `LIVE` | At the edge (production) | `aws cloudfront publish-function --if-match <etag>` |

A function MUST be in `LIVE` stage to execute on a distribution. The
publish step is separate from create/update:

```bash
# After create or update, publish to make it live
FUNCTION_ETAG=$(aws cloudfront describe-function \
  --name "my-function" --query 'ETag' --output text)

aws cloudfront publish-function \
  --name "my-function" \
  --if-match "$FUNCTION_ETAG"
```

### Testing before publishing

```bash
aws cloudfront test-function \
  --name "my-function" \
  --if-match "$FUNCTION_ETAG" \
  --event-object fileb://test-event.json
```

The test-event.json simulates a viewer request. For KVS-enabled
functions, the test uses the linked KVS data.

## Distribution association

The function is associated with a CloudFront distribution via
`FunctionAssociations` in the distribution config.

### Event types

| EventType | When it runs | Use case |
|---|---|---|
| `viewer-request` | Before cache lookup | Routing, redirects, A/B testing, IP filtering |
| `viewer-response` | After cache lookup, before response to viewer | Header manipulation, logging |

For KVS-driven routing (A/B testing, feature flags, IP allowlists), use
`viewer-request` — the function must run BEFORE CloudFront checks the
cache so it can modify the request URI/headers.

### Association in distribution config

```json
{
  "DefaultCacheBehavior": {
    "FunctionAssociations": {
      "Quantity": 1,
      "Items": [{
        "FunctionARN": "arn:aws:cloudfront::123456789012:function/my-function",
        "EventType": "viewer-request"
      }]
    }
  }
}
```

The function ARN (not name) is used in the association. The ARN format
is `arn:aws:cloudfront::<account-id>:function/<function-name>`.

## Common pitfalls

1. **Using cloudfront-js-1.0.** KVS API does not exist in 1.0. Always
   verify the runtime is `cloudfront-js-2.0`.
2. **Calling openKvs() inside handler.** Open KVS at module scope, not
   per-request. Per-request calls add unnecessary latency.
3. **Forgetting to publish.** A function in DEVELOPMENT stage never
   runs at the edge. Always `publish-function` after create/update.
4. **Key case sensitivity.** `get('Flag')` vs `get('flag')` return
   different results. Enforce a naming convention.
5. **Treating undefined as empty string.** `kvs.get()` returns
   `undefined` for missing keys, not `""`. Check explicitly.
6. **Linking KVS at distribution level.** KVS is linked to the function,
   not the distribution. The distribution references the function only.
7. **Exceeding 1 MB.** Monitor KvsSize. The function cannot write, so
   all data must fit within the limit via the write path.
