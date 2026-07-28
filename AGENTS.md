# Viewing-application — notes for coding agents

## Project

Windows game overlay (Viewing). Product docs: `docs/APP_SPEC.md`, design: `docs/DESIGN.md`.

## Graphify (team knowledge graph)

This repo uses **graphify** as a **developer-only** map of the codebase.

- Output: `graphify-out/` (graph.html, graph.json, GRAPH_REPORT.md)
- Guide: `docs/GRAPHIFY.md`
- Install (dev): `pip install -r requirements-dev.txt` then `graphify extract . --code-only`

When answering architecture questions about this repo, prefer consulting `graphify-out/graph.json` / `GRAPH_REPORT.md` or running:

```
graphify query "..."
graphify god-nodes
graphify path "A" "B"
```

Do **not** ship graphify in the player `.exe` or the public website.
