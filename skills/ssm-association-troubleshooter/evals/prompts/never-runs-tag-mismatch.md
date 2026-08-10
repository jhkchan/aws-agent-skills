# Eval prompt: never-runs-tag-mismatch

Diagnose the following SSM association that never runs. Emit the
standard DIAGNOSIS block.

Diagnosis reference: never-runs-tag-mismatch
Account: 111111111111
Region: us-east-1
Association-id: 234567890abcdef234567890abcdef234567890abcdef2
Association name: prod-patch-baseline
Instance-id: i-0aaa111ccc222ddd3 (expected target)
Symptom: NeverRuns (no executions)

Recent diagnostic output:
- describe-association: State=Enabled,
  ScheduleExpression=cron(0 2 * * ? *), NextExecutionDate is
  in the past, Targets=[{Key:tag:Environment,Values:[prod]}]
- describe-association-executions: returns empty list (no runs)
- ec2 describe-instances for the instance: Tags show
  Key=env (lowercase), Value=prod
- Instance has PingStatus=Active, IAM and connectivity are OK.

Emit the standard DIAGNOSIS block. Identify the root cause.
