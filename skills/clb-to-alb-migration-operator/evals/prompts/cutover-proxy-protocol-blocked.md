# Eval prompt: cutover-proxy-protocol-blocked

Plan the following DNS cutover from CLB to ALB and emit the standard
VERDICT block. The CLB has ProxyProtocolPolicyType enabled and the
backend Go service parses Proxy Protocol v2 frames.

Operation: cutover-dns
CLB name: prod-game-clb
ALB name: prod-game-alb (already provisioned, State: active)
Region: us-east-1

```json
{
  "CLB": {
    "ListenerDescriptions": [
      {"Protocol": "HTTPS", "LoadBalancerPort": 443, "InstanceProtocol": "HTTP", "InstancePort": 8080}
    ],
    "Policies": [
      {"ProxyProtocolPolicyType": {"enabled": true, "InstancePort": 8080}}
    ]
  },
  "Backend": "Go service using github.com/pires/go-proxyproto listener (parses Proxy Protocol v2 frames)",
  "ALB": {"State": "active"},
  "describe-target-health": "3/3 targets State: healthy"
}
```
