# Eval: device-shadow-named

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — named shadows (config, firmware) for multi-aspect device state management

## Prompt

Create an IoT thing "actuator-001" in us-east-1 with X.509
certificate and IoT policy for pub/sub. Configure named device
shadows: "config" for configuration state and "firmware" for
firmware version state. The device should receive delta
notifications. Thing group: factory-actuators. Tags:
Environment=production, DeviceType=actuator.
