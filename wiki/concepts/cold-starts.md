---
title: Cold Starts
type: concept
status: draft
tags: [autoscaling, latency, scale-to-zero, kubernetes]
sources: [raw/roadmaps/2026-10-18-ai-infra-project-roadmap.md, raw/story-updates/2026-10-21-local-model-gateway-baseline.md, raw/story-updates/2026-10-21-openrouter-alias-first-runs.md]
related: [concepts/gpu-scheduling.md, concepts/quantization.md, projects/05-keda-scale-to-zero.md, projects/04-kserve-gpu-autoscaling.md, synthesis/2026-10-20-local-model-gateway-plan.md]
updated: 2026-10-21
---

# Cold Starts

**One line:** the time from "a request needs a replica that doesn't exist" to
"that replica serves its first token". For LLMs it is minutes, not
milliseconds, so it shapes every autoscaling decision.

Named as a core concept in the [roadmap](../../raw/roadmaps/2026-10-18-ai-infra-project-roadmap.md).

## Anatomy — measure each term separately

| Term | Bound by | How to measure | Mitigations |
|---|---|---|---|
| 1. GPU node provisioning | Cloud capacity, node boot, driver init | Pod `Pending` → node `Ready` | Warm spare node; placeholder pods ([GPU scheduling](gpu-scheduling.md)); faster provisioner (Karpenter) |
| 2. Image pull | Image size (serving images are several GB), registry bandwidth | Pod events `Pulling` → `Pulled` | Pre-pull DaemonSet; lazy-pulling snapshotters / image streaming; slimmer images ([01](../projects/01-dockerfile-generator.md)) |
| 3. Weight load | Storage → host → GPU bandwidth | vLLM logs: model loading time | Node-local NVMe cache or pre-filled PVC; safetensors; streaming loaders; smaller [quantized](quantization.md) weights |
| 4. Engine init | KV-cache allocation, CUDA graph capture, compilation | vLLM logs between load and ready | Compilation caches; `--enforce-eager` skips graph capture (slower steady state) |
| 5. Readiness | Probe period | `Started` → `Ready` | Short readiness period after a long `startupProbe` |

Terms 1–2 vanish if you keep a node warm with the image cached; terms 3–4
remain on every new replica. That is the basis of the hot / warm / cold tiers
in [05](../projects/05-keda-scale-to-zero.md#three-tiers-choose-per-model-from-its-traffic-pattern).

## Measured: reloading a model on Ollama (Apple silicon)

This is term 3 (weight load) for `deepseek-r1:14b` under Ollama 0.40.6 on the M3 Pro, from the
[local model gateway baseline](../../raw/story-updates/2026-10-21-local-model-gateway-baseline.md):

- **About 0.8 s** for a load 5 s or more after an unload, with the weights still in the macOS
  file cache. This was steady across five samples and three validator runs.
- **5.1–6.4 s** for a load within 2 s of an unload, one sample at each of three delays. So
  back-to-back unload-and-reload is the wrong way to measure a cold start. The
  [validator](../synthesis/2026-10-20-local-model-gateway-plan.md) now waits 5 s.
- **5.84 s** for one load after the model had been unloaded for hours.
- **6.83–8.15 s at 8.83 GiB** for four loads later the same day, each after Ollama had unloaded
  the idle model itself
  ([OpenRouter first-runs note](../../raw/story-updates/2026-10-21-openrouter-alias-first-runs.md)).
  The fast loads were at 8.23 GiB, so the slow ones also take more memory. Three of those four
  runs swapped, so memory pressure may add to it.
- **Unexplained so far:** all the slow cases. The hypotheses are Ollama waiting for freed GPU
  memory to be reported, weights that had left the file cache, and memory pressure. All are
  untested.

## Design implications

- Scale-out must start **before** the SLO is breached: autoscale on queue
  growth, not on latency already being bad ([04](../projects/04-kserve-gpu-autoscaling.md)).
- Scale-to-zero only suits models whose users tolerate the cold path, or whose
  traffic is predictable enough to pre-warm on a schedule.
- Requests arriving during a cold start must be **held** (KEDA HTTP add-on
  interceptor, Knative activator) or rejected with retry-after — decide which.

## Used by

[04](../projects/04-kserve-gpu-autoscaling.md) · [05](../projects/05-keda-scale-to-zero.md) ·
[02](../projects/02-k8s-vllm-serving.md)

## Sources

- [AI infra project roadmap](../../raw/roadmaps/2026-10-18-ai-infra-project-roadmap.md) — named as a core concept.
- [Local model gateway baseline (2026-10-21)](../../raw/story-updates/2026-10-21-local-model-gateway-baseline.md) — the Ollama reload measurements.
- [OpenRouter alias: first runs (2026-10-21)](../../raw/story-updates/2026-10-21-openrouter-alias-first-runs.md) — loads after Ollama's own idle unload.
