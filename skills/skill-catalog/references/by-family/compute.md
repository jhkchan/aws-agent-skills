# Compute skills (44)

Precise call: `@skills:gh:jhkchan/aws-agent-skills/skills/<name>` (swap `<name>` for a row below).

| Skill | Task type | What it does |
|---|---|---|
| `apprunner-autoscaling-optimizer` | optimize | Optimises AWS App Runner autoscaling configuration for cost and performance — auto-scaling configuration (MinSize/MaxSize provisioning), concurrency s |
| `apprunner-service-deployer` | deploy | Deploys AWS App Runner services with production-grade configuration: source selection (ECR image vs source code repository), right-sized compute (CPU/ |
| `autoscaling-group-auditor` | audit | Audits AWS Auto Scaling Groups for launch-template health (legacy launch configuration, IMDSv2), ELB health-check integrity (missing target group, gra |
| `autoscaling-lifecycle-operator` | operate | Operates EC2 Auto Scaling lifecycle hook workflows end-to-end — launch lifecycle hook management (pending:wait transition, bootstrap registration, ELB |
| `autoscaling-policy-deployer` | deploy | Provisions Amazon EC2 Auto Scaling policies and surrounding primitives with production defaults: target tracking (CPUUtilization, ALBRequestCountPerTa |
| `batch-compute-environment-deployer` | deploy | Provisions AWS Batch compute environments, job queues, and job definitions with production defaults: EC2 vs Fargate vs EKS compute environment types,  |
| `compute-optimizer-findings-auditor` | audit | Audits AWS Compute Optimizer findings for EC2, EBS, Lambda, Auto Scaling Group, and ECS resources — classifies overprovisioned (underutilized) waste,  |
| `ec2-backup-operator` | operate | Operates EC2 backup and snapshot workflows safely — EBS snapshot create and cross-region/cross-account copy, AMI creation and deregistration lifecycle |
| `ec2-instance-recovery-operator` | operate | Operates EC2 instance recovery — system status check failure (hardware degradation, stop/start, EC2 recover action), CloudWatch alarm recovery (reboot |
| `ec2-instance-rightsizer` | optimize | Right-sizes EC2 instances for cost optimization using a utilization-driven decision matrix across CPU, memory, network, and disk. |
| `ec2-launch-template-deployer` | deploy | Provisions EC2 Launch Templates with production defaults: AMI and architecture validation (x86_64 / arm64 Graviton), instance type, key pair, security |
| `ec2-reserved-capacity-optimizer` | optimize | Optimizes EC2 Reserved Instance and Savings Plans commitments across seven dimensions: RI utilization analysis (underused Standard or Convertible RIs) |
| `ec2-rightsizing-optimizer` | optimize | Right-sizes EC2 instances for cost optimization using a structured utilization-driven decision framework — gathers 14-30 day CloudWatch utilization da |
| `ec2-spot-fleet-deployer` | deploy | Provisions EC2 Spot Fleets with production defaults: launch template configuration, Spot Fleet request (target capacity, allocation strategy: lowestPr |
| `ec2-spot-interruption-operator` | operate | Operates Amazon EC2 Spot Instance interruption handling workflows end-to-end — EventBridge Instance Interruption Warning (2-minute notice), Spot Insta |
| `ecs-cluster-autoscaling-optimizer` | optimize | Optimises Amazon ECS cluster autoscaling across eleven dimensions: capacity provider strategy (spot vs on-demand weight and base — the spot base + on- |
| `ecs-fargate-deployer` | deploy | Deploys AWS ECS Fargate services with production-grade configuration: right-sized task definition (CPU/memory combos, Fargate sizing), container defin |
| `ecs-task-cost-optimizer` | optimize | Optimises Amazon ECS task cost across seven dimensions: launch type selection (Fargate per-second pricing vs EC2 break-even at ~30% steady utilization |
| `ecs-task-definition-auditor` | audit | Audits ECS task definitions for privileged containers, plaintext secrets in environment variables (instead of Secrets Manager / SSM), host network mod |
| `ecs-task-troubleshooter` | troubleshoot | Diagnoses AWS ECS task failures via a stoppedReason-first decision tree covering ResourceInitializationError (ENI trunking, subnet IP exhaustion), Can |
| `eks-add-on-deployer` | deploy | Provisions Amazon EKS add-ons with production defaults: add-on types (vpc-cni, coredns, kube-proxy, aws-ebs-csi-driver, metrics-server, adot, guarddut |
| `eks-autoscaling-automator` | automate | Designs and implements EKS cluster autoscaling automation. |
| `eks-cluster-auditor` | audit | Audits AWS EKS cluster configurations for public API endpoint exposure, disabled control-plane logging, IAM auth mapRoles misconfiguration (system:mas |
| `eks-cost-optimizer` | optimize | Optimizes EKS cluster costs via a layered analysis framework — right-sizes EC2 managed node groups from 14-30 day CloudWatch and Container Insights ut |
| `eks-hybrid-node-deployer` | deploy | Provisions Amazon EKS Hybrid Nodes with production defaults: hybrid node IAM role creation, activation code/ID for on-prem registration (NOT IAM acces |
| `eks-nodegroup-troubleshooter` | troubleshoot | Diagnoses Amazon EKS managed node group issues through a node-state- driven diagnostic tree: nodes stuck NotReady (kubelet errors, container runtime c |
| `eks-pod-troubleshooter` | troubleshoot | Diagnoses why Kubernetes pods fail on Amazon EKS — CrashLoopBackOff, ImagePullBackOff / ErrImagePull, Pending (FailedScheduling), OOMKilled, unhealthy |
| `eks-security-optimizer` | optimize | Optimises Amazon EKS cluster security posture across eight dimensions: pod security standards (Pod Security Admission — privileged/baseline/restricted |
| `eks-upgrade-operator` | operate | Operates EKS cluster and node group upgrade workflows safely — pre- upgrade checks (current Kubernetes version, addon compatibility matrices, node gro |
| `elastic-beanstalk-deployer` | deploy | Provisions AWS Elastic Beanstalk environments with production defaults: application creation, environment tier (web server vs worker), platform (Amazo |
| `elastic-beanstalk-environment-optimizer` | optimize | Optimizes AWS Elastic Beanstalk environments for cost and performance. |
| `fargate-cost-optimizer` | optimize | Optimises AWS Fargate cost across seven dimensions: task right-sizing (CPU/memory from 28 allowed combos, CloudWatch CPUUtilization and MemoryUtilizat |
| `lambda-alias-deployer` | deploy | Provisions Lambda aliases with production defaults: alias creation pointing to a specific published version, traffic shifting (weighted aliases for ca |
| `lambda-cold-start-optimizer` | optimize | Optimises AWS Lambda cold-start latency across seven dimensions: memory allocation vs initialization time (Power Tuning latency-optimal memory), provi |
| `lambda-cost-optimizer` | optimize | Optimises AWS Lambda function cost across six dimensions: memory tuning (CPU scales with memory at 1769 MB = 1 vCPU; more memory can REDUCE total cost |
| `lambda-function-deployer` | deploy | Deploys AWS Lambda functions with production-grade configuration: least-privilege execution IAM role, supported runtime selection, right-sized memory  |
| `lambda-function-url-deployer` | deploy | Provisions AWS Lambda Function URLs with production defaults: auth mode (AWS_IAM vs NONE), CORS configuration (allowOrigins, allowMethods, allowHeader |
| `lambda-invocation-troubleshooter` | troubleshoot | Diagnoses AWS Lambda invocation failures through an eight-category diagnostic tree: TaskTimeoutException (timeout config vs slow downstream), Runtime. |
| `lambda-layer-deployer` | deploy | Provisions AWS Lambda Layers with production defaults: layer creation (zip with dependencies), compatible runtimes (nodejs, python, java, ruby, provid |
| `lambda-memory-optimizer` | optimize | Optimises AWS Lambda memory configuration across six dimensions: memory-to-CPU proportional allocation (Lambda couples vCPU to memory at 1769 MB = 1 v |
| `lambda-runtime-deprecation-auditor` | audit | Audits AWS Lambda functions for deprecated/EOL runtimes (python3.9, nodejs16.x, etc.), over-permissioned execution roles (admin wildcards, privilege-e |
| `lambda-timeout-troubleshooter` | troubleshoot | Diagnoses AWS Lambda TaskTimeoutException through a focused timeout decision tree: configured timeout vs observed Duration, init-phase (cold-start) ti |
| `lightsail-container-deployer` | deploy | Provisions Amazon Lightsail Container Services with production defaults: container service creation (power scale nano/micro/small/ medium/large/xlarge |
| `lightsail-instance-deployer` | deploy | Provisions production-grade Amazon Lightsail instances with secure defaults: blueprint selection (OS-only vs app+OS bundle), bundle (plan) sizing for  |
