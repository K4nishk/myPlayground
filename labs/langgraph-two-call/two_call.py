"""Two-call LangGraph workflows: generate -> critique, and classify -> respond.

Companion code for wiki/notebooks/langgraph-two-call-extension.md.

    python two_call.py generate-critique "Why does vLLM page its KV cache?"
    python two_call.py generate-critique "..." --max-revisions 1      # reflection loop
    python two_call.py classify-respond "vLLM pods OOM-looping since the 2pm deploy"
    python two_call.py generate-critique "..." --model "<provider>:<model-name>"
    python two_call.py generate-critique "..." --model "openai:<served-name>" \\
        --base-url http://localhost:8000/v1                           # local vLLM
    python two_call.py classify-respond "..." --mermaid               # print the graph

Without --model it runs offline on scripted replies, so the mechanics (state
handoff, edges, routing, trace) can be inspected with no API key.
"""

from __future__ import annotations

import argparse
import json
import operator
import re
import time
import uuid
from collections.abc import Callable
from typing import Annotated, Any, Literal, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

# (system prompt, user prompt) -> reply text. Real models and test doubles both
# fit this shape, so graph logic is testable without network calls.
ChatFn = Callable[[str, str], str]


# --------------------------------------------------------------------------- #
# Shared: execution trace
# --------------------------------------------------------------------------- #

class TraceEvent(TypedDict):
    node: str
    ms: float
    out_chars: int


def traced(name: str, fn: Callable[[Any], dict]) -> Callable[[Any], dict]:
    """Wrap a node so every run appends one TraceEvent to state["trace"]."""
    def node(state):
        start = time.perf_counter()
        update = fn(state)
        event = TraceEvent(
            node=name,
            ms=round((time.perf_counter() - start) * 1000, 1),
            out_chars=sum(len(v) for v in update.values() if isinstance(v, str)),
        )
        return {**update, "trace": [event]}
    return node


def parse_json_object(text: str) -> dict:
    """Pull the first JSON object out of a model reply (tolerates ```json fences and chatter)."""
    text = re.sub(r"```(?:json)?", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object in reply")
    value = json.loads(text[start:end + 1])
    if not isinstance(value, dict):
        raise ValueError("reply JSON is not an object")
    return value


def str_list(value: Any) -> list[str]:
    return [str(v) for v in value] if isinstance(value, list) else []


# --------------------------------------------------------------------------- #
# Pattern A: generate -> critique (optional bounded reflection loop)
# --------------------------------------------------------------------------- #

class Critique(TypedDict):
    score: int                              # 1-10
    gaps: list[str]                         # what the answer leaves out
    failure_modes: list[str]                # where acting on the answer goes wrong
    verdict: Literal["pass", "revise"]


class CritiqueInput(TypedDict):
    question: str


class CritiqueState(CritiqueInput, total=False):
    draft: str                              # written by generate, rewritten by revise
    critique: Critique                      # written by critique
    critique_raw: str                       # raw reviewer reply, kept for debugging
    critique_error: str                     # set when the reply couldn't be parsed
    revisions: int
    trace: Annotated[list[TraceEvent], operator.add]   # reducer: append, never overwrite


PASS_SCORE = 7

GENERATE_SYSTEM = (
    "You are a senior AI infrastructure engineer. Answer the question accurately "
    "and concretely in under 250 words. Prefer specifics (flags, numbers, failure "
    "cases) over generalities."
)

CRITIQUE_SYSTEM = (
    "You are a demanding technical reviewer. Evaluate the answer to the question. "
    "Return ONLY a JSON object, no prose:\n"
    '{"score": <integer 1-10>, "gaps": [<important missing points>], '
    '"failure_modes": [<ways someone acting on this answer would go wrong>], '
    '"verdict": "pass" or "revise"}\n'
    f'Use "revise" when score < {PASS_SCORE}.'
)

REVISE_SYSTEM = (
    "You are a senior AI infrastructure engineer. Rewrite your answer so it fixes "
    "every gap and failure mode in the review. Under 250 words. Output only the answer."
)


def parse_critique(text: str) -> Critique:
    data = parse_json_object(text)
    score = max(1, min(10, int(data.get("score", 0))))
    verdict = data.get("verdict")
    if verdict not in ("pass", "revise"):
        verdict = "pass" if score >= PASS_SCORE else "revise"
    return Critique(score=score, gaps=str_list(data.get("gaps")),
                    failure_modes=str_list(data.get("failure_modes")), verdict=verdict)


def build_generate_critique(chat: ChatFn, max_revisions: int = 0, checkpointer=None):
    """START -> generate -> critique -> END, or with max_revisions > 0:
    critique -> revise -> critique ... until it passes or the budget runs out."""

    def generate(state: CritiqueState) -> dict:
        return {"draft": chat(GENERATE_SYSTEM, state["question"]), "revisions": 0}

    def critique(state: CritiqueState) -> dict:
        reply = chat(CRITIQUE_SYSTEM, f"Question:\n{state['question']}\n\nAnswer to review:\n{state['draft']}")
        try:
            return {"critique": parse_critique(reply), "critique_raw": reply, "critique_error": ""}
        except (ValueError, TypeError) as exc:
            return {"critique_raw": reply, "critique_error": f"unparseable critique: {exc}"}

    def revise(state: CritiqueState) -> dict:
        review = json.dumps(state["critique"], indent=2)
        prompt = f"Question:\n{state['question']}\n\nYour answer:\n{state['draft']}\n\nReview:\n{review}"
        return {"draft": chat(REVISE_SYSTEM, prompt), "revisions": state.get("revisions", 0) + 1}

    def after_critique(state: CritiqueState) -> Literal["revise", "__end__"]:
        if state.get("critique_error"):
            return END                      # can't act on a review we couldn't read
        if state["critique"]["verdict"] == "revise" and state.get("revisions", 0) < max_revisions:
            return "revise"
        return END

    builder = StateGraph(CritiqueState, input_schema=CritiqueInput)
    builder.add_node("generate", traced("generate", generate))
    builder.add_node("critique", traced("critique", critique))
    builder.add_edge(START, "generate")
    builder.add_edge("generate", "critique")
    if max_revisions > 0:
        builder.add_node("revise", traced("revise", revise))
        builder.add_conditional_edges("critique", after_critique, ["revise", END])
        builder.add_edge("revise", "critique")
    else:
        builder.add_edge("critique", END)
    return builder.compile(checkpointer=checkpointer)


# --------------------------------------------------------------------------- #
# Pattern B: classify -> respond, routed by a conditional edge
# --------------------------------------------------------------------------- #

class Classification(TypedDict):
    topic: str
    sentiment: Literal["positive", "neutral", "negative"]
    urgency: Literal["low", "medium", "high"]


class TriageInput(TypedDict):
    message: str


class TriageState(TriageInput, total=False):
    classification: Classification
    classify_error: str
    response: str
    responder: str                          # which node wrote the response
    trace: Annotated[list[TraceEvent], operator.add]


CLASSIFY_SYSTEM = (
    "Classify the user's message about an AI platform. Return ONLY a JSON object:\n"
    '{"topic": <short label, e.g. "serving", "autoscaling", "billing", "fine-tuning">, '
    '"sentiment": "positive" | "neutral" | "negative", '
    '"urgency": "low" | "medium" | "high"}\n'
    '"high" means production is impaired right now.'
)

TONE = {
    "negative": "Acknowledge the frustration in one sentence first; no cheerfulness.",
    "neutral": "Be direct and concise.",
    "positive": "Match the energy briefly, then get to the point.",
}

ESCALATE_SYSTEM = (
    "You are the on-call incident commander. This message was classified HIGH urgency "
    "(topic: {topic}). Reply with: 1) a one-line acknowledgement, 2) immediate "
    "mitigation steps, 3) the information you need from the reporter, 4) who is being "
    "paged. Under 150 words."
)

# When classification fails, fail safe: treat it as urgent so a human sees it.
FALLBACK = Classification(topic="unknown", sentiment="neutral", urgency="high")


def parse_classification(text: str) -> Classification:
    data = parse_json_object(text)
    sentiment = data.get("sentiment") if data.get("sentiment") in TONE else "neutral"
    urgency = data.get("urgency") if data.get("urgency") in ("low", "medium", "high") else "high"
    return Classification(topic=str(data.get("topic", "unknown")), sentiment=sentiment, urgency=urgency)


def build_classify_respond(chat: ChatFn, checkpointer=None):
    """START -> classify -> (respond | escalate) -> END. Two LLM calls per run either way."""

    def classify(state: TriageState) -> dict:
        reply = chat(CLASSIFY_SYSTEM, state["message"])
        try:
            return {"classification": parse_classification(reply), "classify_error": ""}
        except (ValueError, TypeError) as exc:
            return {"classification": FALLBACK, "classify_error": f"unparseable classification: {exc}"}

    def respond(state: TriageState) -> dict:
        c = state["classification"]
        system = (f"You are a helpful platform engineer. Topic: {c['topic']}. Urgency: {c['urgency']}. "
                  f"{TONE[c['sentiment']]} Reply in under 150 words.")
        return {"response": chat(system, state["message"]), "responder": "respond"}

    def escalate(state: TriageState) -> dict:
        system = ESCALATE_SYSTEM.format(topic=state["classification"]["topic"])
        return {"response": chat(system, state["message"]), "responder": "escalate"}

    def route(state: TriageState) -> Literal["respond", "escalate"]:
        return "escalate" if state["classification"]["urgency"] == "high" else "respond"

    builder = StateGraph(TriageState, input_schema=TriageInput)
    builder.add_node("classify", traced("classify", classify))
    builder.add_node("respond", traced("respond", respond))
    builder.add_node("escalate", traced("escalate", escalate))
    builder.add_edge(START, "classify")
    builder.add_conditional_edges("classify", route, ["respond", "escalate"])
    builder.add_edge("respond", END)
    builder.add_edge("escalate", END)
    return builder.compile(checkpointer=checkpointer)


# --------------------------------------------------------------------------- #
# Running and tracing
# --------------------------------------------------------------------------- #

def run_with_trace(graph, inputs: dict, thread_id: str | None = None, show=print) -> dict:
    """Stream per-node updates as they happen, then return the final state.

    Needs a graph compiled with a checkpointer (for get_state / history)."""
    config = {"configurable": {"thread_id": thread_id or uuid.uuid4().hex}}
    for step, update in enumerate(graph.stream(inputs, config, stream_mode="updates"), 1):
        for node, delta in update.items():
            delta = delta or {}
            event = (delta.get("trace") or [{}])[-1]
            keys = ", ".join(k for k in delta if k != "trace")
            show(f"[step {step}] {node:<9} wrote: {keys or '-'}  ({event.get('ms', '?')} ms)")
    history = list(graph.get_state_history(config))
    show(f"thread {config['configurable']['thread_id'][:8]}: {len(history)} checkpoints")
    return graph.get_state(config).values


class ScriptedChat:
    """Test double: returns canned replies in order and records every call."""

    def __init__(self, replies: list[str]):
        self.replies = list(replies)
        self.calls: list[tuple[str, str]] = []

    def __call__(self, system: str, user: str) -> str:
        self.calls.append((system, user))
        if not self.replies:
            raise RuntimeError("ScriptedChat ran out of replies")
        return self.replies.pop(0)


def make_chat(model: str, base_url: str | None = None, temperature: float = 0.0) -> ChatFn:
    """A real model via LangChain, e.g. "anthropic:<model>", "openai:<model>", "google_genai:<model>".
    For a local vLLM / OpenAI-compatible server pass "openai:<served-name>" and base_url."""
    from langchain.chat_models import init_chat_model

    kwargs: dict[str, Any] = {"temperature": temperature}
    if base_url:
        kwargs.update(base_url=base_url, api_key="EMPTY")
    llm = init_chat_model(model, **kwargs)

    def chat(system: str, user: str) -> str:
        return llm.invoke([("system", system), ("user", user)]).text

    return chat


OFFLINE_REPLIES = {
    "generate-critique": [
        "vLLM splits each sequence's KV cache into fixed-size blocks allocated on demand, "
        "so memory isn't reserved for the maximum length up front.",
        '{"score": 5, "gaps": ["no mention of fragmentation numbers", "prefix sharing omitted"], '
        '"failure_modes": ["reader may set max-model-len too high and starve concurrency"], '
        '"verdict": "revise"}',
        "vLLM's PagedAttention stores KV in fixed-size blocks allocated as tokens arrive. This "
        "removes most fragmentation, lets requests share prefix blocks, and turns freed memory "
        "into extra concurrency; max-model-len still caps the worst case per request.",
        '{"score": 8, "gaps": [], "failure_modes": [], "verdict": "pass"}',
    ],
    "classify-respond": [
        '{"topic": "serving", "sentiment": "negative", "urgency": "high"}',
        "Ack — vLLM pods OOM-looping since the 2pm deploy. Mitigation: roll back to the previous "
        "image now; lower --gpu-memory-utilization if rollback isn't possible. Need: pod events "
        "and the deploy diff. Paging: on-call serving engineer.",
    ],
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("pattern", choices=["generate-critique", "classify-respond"])
    parser.add_argument("text", help="the question (generate-critique) or message (classify-respond)")
    parser.add_argument("--model", help='"provider:model"; omit to run offline on scripted replies')
    parser.add_argument("--base-url", help="OpenAI-compatible endpoint, e.g. a local vLLM server")
    parser.add_argument("--max-revisions", type=int, default=0, help="generate-critique reflection budget")
    parser.add_argument("--mermaid", action="store_true", help="print the graph as Mermaid and exit")
    args = parser.parse_args(argv)

    chat = make_chat(args.model, args.base_url) if args.model else ScriptedChat(OFFLINE_REPLIES[args.pattern])
    saver = InMemorySaver()
    if args.pattern == "generate-critique":
        graph = build_generate_critique(chat, args.max_revisions, checkpointer=saver)
        inputs = {"question": args.text}
    else:
        graph = build_classify_respond(chat, checkpointer=saver)
        inputs = {"message": args.text}

    if args.mermaid:
        print(graph.get_graph().draw_mermaid())
        return 0
    if not args.model:
        print("(offline: scripted replies — pass --model for a real LLM)\n")
    final = run_with_trace(graph, inputs)
    shown = {k: v for k, v in final.items() if k not in ("critique_raw",)}
    print("\nfinal state:\n" + json.dumps(shown, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
