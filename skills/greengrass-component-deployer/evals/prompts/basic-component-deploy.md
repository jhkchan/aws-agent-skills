# Eval: basic-component-deploy

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — basic component with install/startup/shutdown lifecycle hooks, S3 artifact, thing group targeting, configuration merge overrides

## Prompt

Create a Greengrass v2 component com.example.TemperatureSensor
version 1.0.0. The recipe should have install, startup, and
shutdown lifecycle hooks. Artifact is a Python script at
s3://my-greengrass-artifacts/artifacts/com.example.TemperatureSensor/1.0.0/sensor.py.
Deploy to thing group FactoryDevices (3 devices) in us-east-1.
Core device MyFactoryGateway is HEALTHY. Token exchange role
has s3:GetObject on the bucket. Configuration merge should
override interval to 10 and logLevel to debug. Tags:
Environment=production, Site=factory-1.
