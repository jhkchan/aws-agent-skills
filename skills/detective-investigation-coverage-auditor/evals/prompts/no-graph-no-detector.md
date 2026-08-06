# Eval prompt: no-graph-no-detector

Audit the following Amazon Detective investigation coverage posture for the
target region. Emit the standard VERDICT block (GRAPH, VERDICT, REASON,
FINDINGS, REMEDIATION).

Audit scope: no-graph-no-detector
Region: us-east-1
Account: 111111111111 (standalone, not in an Organization)

Detective graph state:
  list-graphs: [] (empty — no behavior graph in this region)

GuardDuty detector status:
  list-detectors: [] (no detector in this region)

Organization configuration:
  N/A (standalone account)
