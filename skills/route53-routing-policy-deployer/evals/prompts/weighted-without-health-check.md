# Eval: weighted-without-health-check

**Difficulty:** medium
**Branch:** PREREQUISITES_MISSING — no HCs provided, weighted will route to dead targets

## Prompt

Create a weighted routing policy for "api.example.com" in zone
Z3DABCDEFGHIJK with primary 10.0.0.10 weight 90 and canary
10.0.0.20 weight 10. We don't have health checks set up yet and
don't want to add them. Just do the routing.
