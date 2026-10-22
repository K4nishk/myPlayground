# Sovereign AI Engine — blueprint (Aish's framework, as provided 2026-10-18)

Source: transcribed from the session brief. Framework credited to Aish.

## Goal

Run open-weight models (e.g. Qwen, Gemma, Llama in the 2–4B parameter range)
locally or on private infrastructure.

## Baseline

Establish a frontier API baseline (OpenAI / Anthropic / Gemini) to measure the
performance gap.

## Three primary optimizations

1. Parameter-Efficient Fine-Tuning (PEFT) using LoRA / QLoRA.
2. Weight quantization to reduce memory footprint, evaluating precision vs.
   performance trade-offs.
3. Inference optimization via continuous batching and KV caching to support
   high concurrency.

## Evaluation metrics

- Quality: rubrics / LLM-as-a-judge.
- Operational latency: P95 / P99.
- Throughput.
- Volume crossover threshold required to justify migrating from a closed
  vendor API to a sovereign setup.
