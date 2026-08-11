# Eval: feature-flags-kvs

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — KVS for feature flags, read-only function notes, toggle-via-put-key pattern, flat key-value schema

## Prompt

I want to use CloudFront KeyValueStore to manage feature flags at
the edge. I need flags for flag-new-checkout, flag-beta-api, and
flag-maintenance-mode. Create a KVS named feature-flags-kvs and a
CloudFront Function named flag-evaluator that reads these flags.
Distribution E987654321DEF. Account ID: 123456789012.
