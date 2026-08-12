# Eval prompt: keda-sqs-scale-to-zero

Deploy KEDA with an SQS trigger for a queue consumer that should
scale to zero when the queue is empty. Emit the standard AUTOSCALING
block including the KEDA Helm install and the ScaledObject manifest.

Design reference: keda-sqs-scale-to-zero
Account: 111111111111
Region: us-east-1

Cluster: prod-cluster, EKS 1.30
Workload: sqs-batch-processor (Deployment, currently 5 replicas)
Queue URL: https://sqs.us-east-1.amazonaws.com/111111111111/batch-jobs
Desired: scale to 0 when queue empty, scale up to 30 when lag > 10
KEDA: not yet installed (clean install needed)
IRSA role for KEDA: arn:aws:iam::111111111111:role/keda-sqs-role
