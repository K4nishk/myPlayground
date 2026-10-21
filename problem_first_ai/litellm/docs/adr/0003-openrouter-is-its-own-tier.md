---
status: accepted
---

# OpenRouter is its own tier, not the frontier

A vendor's model reached through OpenRouter gets `openrouter-<role>` aliases, never `frontier-<role>`. OpenRouter adds a hop and picks among several providers for one model (OpenAI, Azure and Amazon Bedrock all serve `gpt-6-luna` there), so its timings aren't the vendor's own, and it accepts a different set of parameters (none of `gpt-6-luna`'s OpenRouter endpoints takes a temperature). Keeping `frontier-<role>` for a vendor API called directly, with that vendor's own key, means a frontier baseline never quietly includes an aggregator. OpenRouter came first because that's where the budget is; the cost is a fourth tier name, and a true frontier comparison waits for a direct key.
