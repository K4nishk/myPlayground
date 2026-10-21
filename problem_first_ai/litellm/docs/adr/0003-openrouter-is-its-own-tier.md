---
status: accepted
---

# OpenRouter is its own tier, not the frontier

A vendor's model reached through OpenRouter gets `openrouter-<role>` aliases, never `frontier-<role>`. OpenRouter adds a hop and picks among several upstreams for one model (it lists OpenAI, Azure and Amazon Bedrock for `gpt-6-luna`), so its timings aren't the vendor's own, and it accepts a different set of parameters (none of those upstreams takes a temperature for `gpt-6-luna`). Both facts are from OpenRouter's listing for the model, `openrouter.ai/api/v1/models/openai/gpt-6-luna/endpoints`, read on 2026-10-21. Keeping `frontier-<role>` for a vendor API called directly, with that vendor's own key, means a frontier baseline never quietly includes an aggregator. OpenRouter came first because that's where the budget is; the cost is a fourth tier name, and a true frontier comparison waits for a direct key.
