# Eval: missing-tolerated-failures

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — fault-tolerant workflow without ToleratedFailureCount/Percentage; single batch failure would fail entire Map state

## Prompt

Create a Distributed Map state named FaultTolerantProcess for
processing 3000 items. Each item calls Lambda function
unreliable-api. This is a fault-tolerant workflow — some items
are expected to fail. No ToleratedFailureCount or
ToleratedFailurePercentage specified. Tags: Environment=production.
