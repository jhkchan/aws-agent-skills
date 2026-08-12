# Eval: missing-safety-rule

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — no safety rule provided; safety rules are mandatory for production failover

## Prompt

Create ARC routing controls for my application. Cell-A in
us-east-1, Cell-B in us-west-2. Cluster: unsafe-cluster. I want
two routing controls but do not want any safety rules. The
failover should just toggle freely without any guardrails.
