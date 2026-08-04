# Eval prompt: lambda-overprovisioned-memory

Audit the following Compute Optimizer finding for the Lambda function. Emit
the standard VERDICT block (RESOURCE, VERDICT, REASON, RISK, FINDINGS,
REMEDIATION).

Resource type: Lambda function
Function ARN: arn:aws:lambda:us-east-1:111111111111:function:lambda-overprovisioned-memory
Current memory size: 2560 MB
Finding: Overprovisioned
Finding reasons: ["MemoryOverprovisioned"]
Utilization metrics:
  - name: Memory, statistic: Average, value: 400.0, unit: MB
  - name: Invocations, statistic: Sum, value: 50000.0, unit: Count
  - name: Duration, statistic: Average, value: 250.0, unit: Milliseconds
Recommendation options:
  - rank: 1, memorySize: 1280, performanceRisk: 1, savingsOpportunity: { estimatedMonthlySavings: 80.0 }
Last refresh timestamp: 2026-07-27
