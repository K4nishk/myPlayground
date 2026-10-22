# myPlayground — a second brain for AI infrastructure

A persistent, self-maintaining knowledge base built on Andrej Karpathy's
[LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).
You drop raw material in; an LLM agent (Claude Code) compiles it into an
interlinked wiki, keeps a story bank of your project narratives in sync, and
answers questions from what it has compiled — instead of re-deriving
everything from scratch on each question like RAG does.

## How you use it

| You want to… | Do this |
|---|---|
| Add knowledge | Drop a file in [`raw/`](raw/README.md) (roadmap, notes, notebook export, article). Open Claude Code: the session-start hook reports it, and the agent absorbs it (`/ingest`). |
| Log progress on a project | Copy [`raw/story-updates/_TEMPLATE.md`](raw/story-updates/_TEMPLATE.md), fill in what you did and measured. `/ingest` updates the project page and the story. |
| Ask or brainstorm | Just ask (`/query`). Answers cite wiki pages; useful ones get filed back into [`wiki/synthesis/`](wiki/index.md#synthesis). |
| Write a project update / interview answer | `/story <id> <status\|interview\|resume\|linkedin>` |
| Check health | `/lint` (report) · `/heal` (repair: broken links, stale stories, unbacked numbers) |

## What's in here

```
raw/            your sources — the only folder you need to write to
wiki/           compiled knowledge (agent-maintained)
  index.md        start here: catalog of every page
  overview.md     how the six projects connect
  projects/       01 Dockerfile generator … 06 Sovereign AI Engine
  concepts/       KV cache, continuous batching, GPU scheduling, cold starts,
                  PEFT, quantization, LLM evaluation, LangGraph state graphs
  notebooks/      LangGraph two-call extension plan
  log.md          what happened when
  WIKI_SCHEMA.md  the rules
story-bank/     living STAR narratives, one per project
labs/           runnable code the wiki documents
  langgraph-two-call/   generate→critique + classify→respond graphs, tests, notebook
  sovereign-ai/         API-vs-self-hosting crossover calculator
tools/brain.py  drift detection + lint + log (stdlib Python)
.claude/        skills (ingest, query, lint, heal, story) + session-start hook
CLAUDE.md       the agent's operating manual
```

## How "self-healing" works

1. `tools/brain.py` hashes every file in `raw/` (plus anything matched by
   `.brain/watch.txt`, like `problem_first_ai/*.ipynb`) and compares against
   `.brain/manifest.json`. New or edited sources show up as pending.
2. On every Claude Code session start a hook prints that status, so the agent
   absorbs changes before answering.
3. Lint checks links (including `#anchors`), frontmatter, index coverage,
   orphans, log order, cited sources, story health, and credential-shaped
   strings (reported by type and length, never by value). A story goes **stale**
   when its project page changes after the story was last synced, and gets
   flagged when it claims results without evidence.
4. `/heal` repairs what lint finds and re-syncs stale stories — writing numbers
   only from cited `raw/story-updates/` files.

## Commands

```bash
python3 tools/brain.py status                 # pending raw changes + health
python3 tools/brain.py lint                   # full report (exit 1 on errors)
python3 -m unittest discover -s tests         # tooling + calculator tests
python3 labs/sovereign-ai/crossover.py --example
cd labs/langgraph-two-call && pip install -r requirements.txt && python -m unittest test_two_call
```

## Checks and CI

`tools/check.sh` runs every check: the brain lint, the tooling tests, the docs checks (no two
ADRs sharing a number, the gateway docs using its glossary's words) and the gateway's tests. The
pre-commit hook runs the checks for what's staged; turn it on once per clone with
`git config core.hooksPath .githooks`. CI runs every check on each push and pull request.

Reading CI results:

- **Claude reads the status** from GitHub's public API with `curl`, since the repo is public:

  ```bash
  curl -s 'https://api.github.com/repos/K4nishk/myPlayground/actions/runs?branch=sandbox&per_page=3' \
    | jq -r '.workflow_runs[] | [.head_sha[0:7], .status, .conclusion] | @tsv'
  ```

  `gh` doesn't work inside Claude's sandbox: a Go program there can't verify TLS certificates
  (`x509: OSStatus -26276`, seen 2026-10-21).
- **You read the logs.** GitHub serves step logs only to signed-in users, so this part is on
  your end. Type these in Claude's prompt (the `!` runs them in your own shell, and the output
  lands in the conversation), or open the repo's Actions tab:

  ```bash
  ! gh run list --repo K4nishk/myPlayground --branch sandbox --limit 3
  ! gh run view <run id> --repo K4nishk/myPlayground --log-failed
  ```
