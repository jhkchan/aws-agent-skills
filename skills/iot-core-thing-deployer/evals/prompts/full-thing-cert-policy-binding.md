# Eval: full-thing-cert-policy-binding

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — thing, certificate, policy, both bindings, thing type, thing group

## Prompt

Create an IoT thing "sensor-001" in us-east-1 with X.509
certificate. Create IoT policy "sensor-publish-policy" allowing
connect with client ID sensor-*, publish to device/+/telemetry,
and subscribe to device/+/commands. Attach the certificate to
the thing and the policy to the certificate. Thing type:
temperature-sensor. Thing group: factory-floor-sensors. Tags:
Environment=production, DeviceType=sensor.
