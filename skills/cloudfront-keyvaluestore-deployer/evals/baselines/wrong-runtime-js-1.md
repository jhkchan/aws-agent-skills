# Baseline (no-skill) — wrong-runtime-js-1

> This is the response a model produces **without** the skill
> definition. It does not recognize that cloudfront-js-1.0 lacks the
> cf.openKvs() API and gives generic advice that would fail at runtime.
> The skill correctly identifies this as PREREQUISITES_MISSING.

---

To read from a KeyValueStore in your edge-router function:

1. Make sure the KVS is created:
```bash
aws cloudfront create-key-value-store --name config-kvs
```

2. In your function code, use:
```javascript
var value = cloudfront.getKeyValueStore().get('key');
```

3. Link the KVS to the function and attach to the distribution.

That should work fine.
