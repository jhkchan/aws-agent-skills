# Eval: ecs-container-instance-drain

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — aws:ecs:drain-container-instances action on ecs-prod-cluster with FIS_Target=enabled tag, IAM role scoped to ECS drain permissions, CloudWatch task-pending alarm stop condition

## Prompt

Create a FIS experiment template in us-east-1 account
123456789012. Action: aws:ecs:drain-container-instances with
duration 5m. Target: ECS container instances in cluster
ecs-prod-cluster tagged FIS_Target=enabled, selectionMode
COUNT(1). Stop condition: CloudWatch alarm FIS-ECS-Task-Pending
(ARN
arn:aws:cloudwatch:us-east-1:123456789012:alarm:FIS-ECS-Task-Pending).
IAM role FISECSRole with ecs:ListContainerInstances,
ecs:UpdateContainerInstancesState, and
ecs:DescribeContainerInstances scoped to cluster
arn:aws:ecs:us-east-1:123456789012:cluster/ecs-prod-cluster.
Log group /aws/fis/ecs-drain. Tags: Environment=staging,
ExperimentType=ECS-Drain.
