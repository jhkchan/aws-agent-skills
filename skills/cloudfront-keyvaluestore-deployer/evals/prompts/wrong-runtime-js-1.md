# Eval: wrong-runtime-js-1

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — function created with cloudfront-js-1.0 which does not support cf.openKvs(); must update to cloudfront-js-2.0

## Prompt

I have a CloudFront Function named edge-router that I created
with the cloudfront-js-1.0 runtime. I want to read from a
KeyValueStore inside it using cf.openKvs(). The KVS is named
config-kvs. It's attached to distribution E111111111AAA.
Account ID: 123456789012.
