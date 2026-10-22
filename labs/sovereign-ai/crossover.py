#!/usr/bin/env python3
"""Volume crossover: when does self-hosting beat a vendor API?

Model (see wiki/projects/06-sovereign-ai-engine.md#crossover-analysis):

    C_api(V)  = V * (T_in * p_in + T_out * p_out)
    C_self(V) = G(V) * gpu_month + ops_month,  G(V) = max(min_gpus, ceil(V / capacity_per_gpu))

capacity_per_gpu must come from a load test at your latency SLO, or the
crossover will be optimistic.

    python3 labs/sovereign-ai/crossover.py --example
    python3 labs/sovereign-ai/crossover.py --in-tokens 1200 --out-tokens 250 \\
        --api-in-price 1.0 --api-out-price 4.0 --gpu-hourly 1.2 \\
        --ops-monthly 500 --capacity-rps 4 --utilization 0.6
"""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass

HOURS_PER_MONTH = 730

# Illustrative only — not price quotes or measurements.
EXAMPLE = dict(in_tokens=1000, out_tokens=300, api_in_price=1.00, api_out_price=4.00,
               gpu_hourly=1.20, ops_monthly=500.0, capacity_rps=4.0, utilization=0.6, min_gpus=1)


@dataclass(frozen=True)
class Inputs:
    in_tokens: float        # prompt tokens per request
    out_tokens: float       # generated tokens per request
    api_in_price: float     # $ per 1M input tokens
    api_out_price: float    # $ per 1M output tokens
    gpu_hourly: float       # $ per GPU-hour (reserved / always-on)
    ops_monthly: float      # $ per month: engineering time, monitoring, storage
    capacity_rps: float     # sustained req/s per GPU at your latency SLO
    utilization: float = 0.6  # planned average utilization (headroom for peaks)
    min_gpus: int = 1       # floor, e.g. 2 for high availability

    @property
    def api_cost_per_request(self) -> float:
        return (self.in_tokens * self.api_in_price + self.out_tokens * self.api_out_price) / 1e6

    @property
    def gpu_month(self) -> float:
        return self.gpu_hourly * HOURS_PER_MONTH

    @property
    def capacity_per_gpu(self) -> float:
        """Requests per GPU per month at the planned utilization."""
        return self.capacity_rps * self.utilization * 3600 * HOURS_PER_MONTH


def gpus_needed(v: float, p: Inputs) -> int:
    return max(p.min_gpus, math.ceil(v / p.capacity_per_gpu))


def api_cost(v: float, p: Inputs) -> float:
    return v * p.api_cost_per_request


def self_cost(v: float, p: Inputs) -> float:
    return gpus_needed(v, p) * p.gpu_month + p.ops_monthly


def crossover(p: Inputs) -> float | None:
    """Smallest monthly volume at which self-hosting is no more expensive, or None."""
    c, cap, gm = p.api_cost_per_request, p.capacity_per_gpu, p.gpu_month
    if c <= 0 or cap <= 0:
        return None
    k = p.min_gpus
    v = (k * gm + p.ops_monthly) / c
    if v <= k * cap:
        return v
    if c * cap <= gm:
        # Each extra GPU costs more than the API traffic it absorbs: never crosses.
        return None
    while True:
        k += 1
        v = (k * gm + p.ops_monthly) / c
        if v <= k * cap:
            return max(v, (k - 1) * cap)


def report(p: Inputs) -> str:
    lines = [
        f"API cost per request:     ${p.api_cost_per_request:.6f}",
        f"GPU cost per month:       ${p.gpu_month:,.0f}  (x{p.min_gpus} minimum)",
        f"Capacity per GPU / month: {p.capacity_per_gpu:,.0f} requests "
        f"({p.capacity_rps} req/s at SLO x {p.utilization:.0%} utilization)",
        f"Self-hosted marginal cost at full use: ${p.gpu_month / p.capacity_per_gpu:.6f} / request",
    ]
    v_star = crossover(p)
    if v_star is None:
        lines.append("\nNo crossover: at these numbers the API stays cheaper at every volume.")
        return "\n".join(lines)
    lines.append(f"\nCrossover V* = {v_star:,.0f} requests/month "
                 f"(~{v_star / (HOURS_PER_MONTH * 3600):.2f} req/s average)\n")
    lines.append(f"{'volume/month':>14} {'GPUs':>5} {'API $':>12} {'self $':>12} {'cheaper':>8}")
    for factor in (0.1, 0.5, 1.0, 2.0, 10.0, 50.0):
        v = v_star * factor
        a, s = api_cost(v, p), self_cost(v, p)
        lines.append(f"{v:>14,.0f} {gpus_needed(v, p):>5} {a:>12,.0f} {s:>12,.0f} "
                     f"{'self' if s <= a else 'API':>8}")
    lines.append("\nOnly meaningful if quality clears the bar — see the decision rule on the wiki page.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--example", action="store_true", help="use the illustrative numbers from the wiki")
    for name in ("in-tokens", "out-tokens", "api-in-price", "api-out-price",
                 "gpu-hourly", "ops-monthly", "capacity-rps", "utilization"):
        parser.add_argument(f"--{name}", type=float)
    parser.add_argument("--min-gpus", type=int)
    args = vars(parser.parse_args(argv))

    example = args.pop("example")
    values = dict(EXAMPLE) if example else {}
    values.update({k: v for k, v in args.items() if v is not None})
    missing = [k for k in EXAMPLE if k not in values and k not in ("utilization", "min_gpus")]
    if missing:
        parser.error("missing " + ", ".join("--" + m.replace("_", "-") for m in missing) + " (or pass --example)")
    if example:
        print("ILLUSTRATIVE NUMBERS — replace with current prices and your measured capacity.\n")
    print(report(Inputs(**values)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
