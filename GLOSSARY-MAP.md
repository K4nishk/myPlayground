# Glossary Map

## Contexts

- [Local model gateway](problem_first_ai/litellm/GLOSSARY.md): one OpenAI-compatible front door
  to local, cluster, OpenRouter and frontier models, and the validator that checks every alias.
  ADRs: `problem_first_ai/litellm/docs/adr/`.

## Relationships

- **Local model gateway → second brain**: baselines and experiments become `raw/story-updates/`
  notes that the wiki compiles; the gateway's `JOURNAL.md` and docs are watched sources. The
  second brain's own vocabulary (source, ingest, synthesis, story) lives in `wiki/WIKI_SCHEMA.md`.
