# Eval: canary-traffic-shift

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — canary traffic shift between two published versions using alias routing config

## Prompt

I need to do a canary deployment for function my-function.
The prod alias currently points to version 5. I published
version 6 and want to shift 10% traffic to it. Keep 90% on
version 5. Region us-east-1. Account: 123456789012.
