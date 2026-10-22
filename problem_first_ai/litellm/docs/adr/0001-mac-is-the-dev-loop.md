---
status: accepted
---

# The Mac is the dev loop; capacity is measured on the cluster

This Mac (Ollama now, vllm-metal later) is where aliases, cases and the gateway are built and checked, not where project 06's capacity numbers come from. Capacity and resource utilization are measured on the `cluster` tier (Kubernetes on your own NVIDIA hardware). Scaling past that hardware means renting cloud GPUs, so the crossover is priced against a cloud bill and the owned hardware stays the fallback. The project 06 wiki page assumed the Kubernetes stack from projects 02–05; this narrows the Mac's role rather than replacing that stack.
