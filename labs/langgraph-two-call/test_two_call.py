"""Offline tests for the two-call graphs: python -m unittest test_two_call (from this folder)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from langgraph.checkpoint.memory import InMemorySaver  # noqa: E402

from two_call import (  # noqa: E402
    ScriptedChat,
    build_classify_respond,
    build_generate_critique,
    parse_critique,
    run_with_trace,
)

PASS = '{"score": 8, "gaps": [], "failure_modes": [], "verdict": "pass"}'
REVISE = '{"score": 4, "gaps": ["no numbers"], "failure_modes": ["wrong flag"], "verdict": "revise"}'


def nodes(state):
    return [event["node"] for event in state["trace"]]


class GenerateCritique(unittest.TestCase):
    def test_two_calls_hand_off_through_state(self):
        chat = ScriptedChat(["DRAFT-123", PASS])
        out = build_generate_critique(chat).invoke({"question": "q?"})
        self.assertEqual(out["draft"], "DRAFT-123")
        self.assertEqual(out["critique"]["score"], 8)
        self.assertEqual(nodes(out), ["generate", "critique"])
        self.assertEqual(len(chat.calls), 2)
        self.assertIn("DRAFT-123", chat.calls[1][1], "critique must read the draft from state")

    def test_parses_fenced_json_and_derives_verdict(self):
        critique = parse_critique('Sure!\n```json\n{"score": 9, "gaps": ["x"]}\n```')
        self.assertEqual(critique["verdict"], "pass")
        self.assertEqual(critique["gaps"], ["x"])
        self.assertEqual(critique["failure_modes"], [])

    def test_unparseable_critique_is_recorded_and_ends(self):
        chat = ScriptedChat(["draft", "looks fine to me"])
        out = build_generate_critique(chat, max_revisions=2).invoke({"question": "q?"})
        self.assertIn("unparseable", out["critique_error"])
        self.assertNotIn("critique", out)
        self.assertEqual(len(chat.calls), 2, "must not revise on a review it couldn't read")

    def test_reflection_loop_revises_until_pass(self):
        chat = ScriptedChat(["v1", REVISE, "v2", PASS])
        out = build_generate_critique(chat, max_revisions=3).invoke({"question": "q?"})
        self.assertEqual(out["draft"], "v2")
        self.assertEqual(out["revisions"], 1)
        self.assertEqual(nodes(out), ["generate", "critique", "revise", "critique"])

    def test_reflection_loop_respects_budget(self):
        chat = ScriptedChat(["v1", REVISE, "v2", REVISE, "unused", PASS])
        out = build_generate_critique(chat, max_revisions=1).invoke({"question": "q?"})
        self.assertEqual(out["revisions"], 1)
        self.assertEqual(out["critique"]["verdict"], "revise")
        self.assertEqual(len(chat.calls), 4)


class ClassifyRespond(unittest.TestCase):
    def run_graph(self, classification):
        chat = ScriptedChat([classification, "REPLY"])
        return build_classify_respond(chat).invoke({"message": "m"}), chat

    def test_high_urgency_escalates(self):
        out, _ = self.run_graph('{"topic": "serving", "sentiment": "negative", "urgency": "high"}')
        self.assertEqual(out["responder"], "escalate")
        self.assertEqual(nodes(out), ["classify", "escalate"])

    def test_low_urgency_responds_with_tailored_tone(self):
        out, chat = self.run_graph('{"topic": "billing", "sentiment": "negative", "urgency": "low"}')
        self.assertEqual(out["responder"], "respond")
        system_prompt = chat.calls[1][0]
        self.assertIn("billing", system_prompt)
        self.assertIn("frustration", system_prompt)

    def test_bad_classification_fails_safe_to_escalate(self):
        out, _ = self.run_graph("no idea")
        self.assertIn("unparseable", out["classify_error"])
        self.assertEqual(out["responder"], "escalate")


class Tracing(unittest.TestCase):
    def test_run_with_trace_streams_updates_and_keeps_history(self):
        graph = build_generate_critique(ScriptedChat(["d", PASS]), checkpointer=InMemorySaver())
        lines = []
        out = run_with_trace(graph, {"question": "q?"}, thread_id="t1", show=lines.append)
        self.assertEqual(out["critique"]["verdict"], "pass")
        self.assertTrue(lines[0].startswith("[step 1] generate"))
        self.assertTrue(lines[1].startswith("[step 2] critique"))
        history = list(graph.get_state_history({"configurable": {"thread_id": "t1"}}))
        self.assertGreaterEqual(len(history), 3)   # input, after generate, after critique


if __name__ == "__main__":
    unittest.main()
