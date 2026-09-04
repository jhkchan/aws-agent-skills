# AI/ML skills (16)

Precise call: `@skills:gh:jhkchan/aws-agent-skills/skills/<name>` (swap `<name>` for a row below).

| Skill | Task type | What it does |
|---|---|---|
| `bedrock-guardrail-coverage-auditor` | audit | Audits Amazon Bedrock Guardrails configurations for model coverage gaps, weak or disabled content filters (hate, insult, sexual, violence), missing or |
| `bedrock-guardrail-deployer` | deploy | Provisions Amazon Bedrock Guardrails with production defaults: guardrail creation (name, description, KMS key), content filters (hate, insults, sexual |
| `bedrock-model-access-inventory` | audit | Audits Amazon Bedrock model access posture — invocation logging coverage (S3/CloudWatch/DataFirehose destinations and per-modality delivery flags), cu |
| `bedrock-model-cost-optimizer` | optimize | Optimises Amazon Bedrock inference cost across seven dimensions: model selection (Claude Haiku is ~60x cheaper per token than Opus; Nova Micro cheaper |
| `comprehend-classifier-deployer` | deploy | Provisions Amazon Comprehend custom document classifiers with production defaults: multi-class vs multi-label mode, training data formats (CSV + Augme |
| `lex-bot-deployer` | deploy | Provisions Amazon Lex V2 conversational bots with production defaults: bot creation (create-bot), locale setup (en-US and other supported locales), in |
| `personalize-campaign-deployer` | deploy | Deploys Amazon Personalize recommendation pipelines with production defaults: dataset group creation (CUSTOM or DOMAIN), dataset types (Interactions,  |
| `polly-voice-deployer` | deploy | Deploys Amazon Polly text-to-speech configurations with production defaults: engine selection (standard vs neural vs long-form vs generative), voice s |
| `rekognition-collection-deployer` | deploy | Provisions Amazon Rekognition face collections and detection pipelines: collection creation with KMS encryption (must be set at create time), face ind |
| `sagemaker-endpoint-auditor` | audit | Audits SageMaker real-time and async endpoints for security posture and production readiness — KMS encryption-at-rest and inter-container traffic encr |
| `sagemaker-endpoint-deployer` | deploy | Provisions SageMaker real-time, serverless, and asynchronous inference endpoints with production defaults: model creation (S3 artifact, container imag |
| `sagemaker-model-registry-operator` | operate | Operates SageMaker Model Registry lifecycles safely — creates model package groups; registers versioned model packages (model artifacts, inference ima |
| `sagemaker-pipeline-deployer` | deploy | Defines Amazon SageMaker Pipelines for ML workflows with production defaults: step collection (ProcessingStep with sklearn/Spark container, TrainingSt |
| `sagemaker-training-job-operator` | operate | Operates Amazon SageMaker training jobs end-to-end — job creation (algorithm spec, input data S3 channels, output S3, instance type, volume size, hype |
| `textract-document-deployer` | deploy | Deploys Amazon Textract document-analysis pipelines with production defaults: synchronous APIs (DetectDocumentText, AnalyzeDocument) for single-page r |
| `transcribe-job-deployer` | deploy | Deploys Amazon Transcribe configurations with production defaults: transcription job types (batch from S3 via start-transcription-job async, real-time |
