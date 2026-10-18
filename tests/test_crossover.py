"""Tests for labs/sovereign-ai/crossover.py: python3 -m unittest discover -s tests"""

import importlib.util
import sys
import unittest
from pathlib import Path

PATH = Path(__file__).resolve().parent.parent / "labs" / "sovereign-ai" / "crossover.py"
spec = importlib.util.spec_from_file_location("crossover", PATH)
crossover = importlib.util.module_from_spec(spec)
sys.modules["crossover"] = crossover  # dataclasses resolve annotations via sys.modules
spec.loader.exec_module(crossover)

Inputs = crossover.Inputs


class Crossover(unittest.TestCase):
    def setUp(self):
        self.p = Inputs(**crossover.EXAMPLE)

    def test_wiki_worked_example(self):
        self.assertAlmostEqual(self.p.api_cost_per_request, 0.0022)
        self.assertEqual(round(crossover.crossover(self.p)), 625_455)

    def test_costs_meet_at_crossover(self):
        v = crossover.crossover(self.p)
        self.assertAlmostEqual(crossover.api_cost(v, self.p), crossover.self_cost(v, self.p), places=6)
        self.assertGreater(crossover.api_cost(v * 0.9, self.p), 0)
        self.assertLess(crossover.api_cost(v * 0.9, self.p), crossover.self_cost(v * 0.9, self.p))

    def test_min_gpus_raises_threshold(self):
        ha = Inputs(**{**crossover.EXAMPLE, "min_gpus": 2})
        self.assertEqual(round(crossover.crossover(ha)), 1_023_636)

    def test_crossover_beyond_first_gpu(self):
        # Tiny capacity forces the crossover into a later GPU step.
        p = Inputs(**{**crossover.EXAMPLE, "capacity_rps": 0.5, "ops_monthly": 5000})
        v = crossover.crossover(p)
        self.assertEqual(crossover.gpus_needed(v, p), 6)
        self.assertLessEqual(crossover.self_cost(v, p), crossover.api_cost(v, p) + 1e-6)
        self.assertGreater(crossover.self_cost(v * 0.99, p), crossover.api_cost(v * 0.99, p))

    def test_no_crossover_when_gpu_cannot_pay_for_itself(self):
        p = Inputs(**{**crossover.EXAMPLE, "capacity_rps": 0.01})
        self.assertIsNone(crossover.crossover(p))


if __name__ == "__main__":
    unittest.main()
