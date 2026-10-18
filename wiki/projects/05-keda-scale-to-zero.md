---
title: KEDA Scale-to-Zero
type: project
status: draft
tags: [keda, autoscaling, scale-to-zero, cost, kubernetes]
sources: [raw/roadmaps/2026-10-18-ai-infra-project-roadmap.md]
related: [projects/04-kserve-gpu-autoscaling.md, concepts/cold-starts.md, concepts/gpu-scheduling.md]
updated: 2026-10-18
---

# 05 — KEDA Scale-to-Zero

**Roadmap position** ([overview](../overview.md)): fifth ([source](../../raw/roadmaps/2026-10-18-ai-infra-project-roadmap.md)).
Idle models should cost zero GPU-hours, and the first request after idle should
still land inside an agreed cold-start budget.

Only the title was stated in the source; the design below is **Proposed**.

## The chicken-and-egg problem

At zero replicas there is no vLLM pod, so there is no `/metrics` to scale on.
The 0 → 1 signal has to come from **outside** the model pod:

| Activation source | How | Fits |
|---|---|---|
| KEDA HTTP add-on | Interceptor proxy holds requests while scaling from zero and reports pending count | Synchronous HTTP APIs |
| Gateway / ingress metrics | Prometheus query on request rate at the gateway | You already run a gateway |
| A queue | KEDA scaler on Redis / Kafka / SQS backlog | Async / batch inference |

Then 1 → N uses the in-pod signal (`vllm:num_requests_waiting`). KEDA takes the
maximum desired replica count across triggers, so both can live on one object.

## ScaledObject (Proposed — the gateway query is illustrative)

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: vllm-small
spec:
  scaleTargetRef:
    name: vllm-small            # the Deployment from project 02
  minReplicaCount: 0
  maxReplicaCount: 4
  cooldownPeriod: 900           # idle seconds before scaling to zero
  triggers:
    - type: prometheus          # 0 -> 1: traffic seen at the gateway
      metadata:
        serverAddress: http://prometheus.monitoring:9090
        query: sum(rate(gateway_requests_total{route="vllm-small"}[2m]))
        threshold: "1"
        activationThreshold: "0"
    - type: prometheus          # 1 -> N: queue building inside vLLM
      metadata:
        serverAddress: http://prometheus.monitoring:9090
        query: sum(vllm:num_requests_waiting{app="vllm-small"})
        threshold: "4"
```

## Cold-start budget

What the first request after idle waits for — details and mitigations in
[cold starts](../concepts/cold-starts.md):

1. GPU node provisioning (only if the node pool also went to zero) — usually the largest term.
2. Image pull — serving images are several GB.
3. Weight load — storage bandwidth bound.
4. Engine init — KV-cache allocation, CUDA graph capture, compilation.

## Three tiers (choose per model from its traffic pattern)

| Tier | Pods | GPU nodes | First-request wait | Idle cost |
|---|---|---|---|---|
| Hot | min ≥ 1 | ≥ 1 | none | full GPU |
| Warm | 0 | 1 spare kept | image (if not cached) + weights + init | one node |
| Cold | 0 | 0 | everything above + node provisioning | ~zero |

## Relation to KServe

KServe's Knative mode already scales to zero (its activator buffers requests).
KEDA is the route when running KServe — or plain Deployments — without Knative,
and the only route for queue-driven inference. Compare both in
[project 04](04-kserve-gpu-autoscaling.md).

## Experiments

- Measure each cold-start term separately for each tier (node, pull, load, init).
- Repeat with mitigations: pre-pulled image, node-local weight cache,
  [quantized](../concepts/quantization.md) (smaller) weights.
- Cost vs latency curve for a bursty daily traffic pattern.

## Milestones

1. Scale 1 ↔ N on queue depth.
2. Scale to zero with the HTTP add-on (or gateway metric) for activation.
3. Cold-start breakdown measured per tier.
4. Mitigations applied; before/after numbers in a story update.

## Story

[story-bank/stories/keda-scale-to-zero.md](../../story-bank/stories/keda-scale-to-zero.md)

## Sources

- [AI infra project roadmap (2026-10-18)](../../raw/roadmaps/2026-10-18-ai-infra-project-roadmap.md) — project title and sequence.
