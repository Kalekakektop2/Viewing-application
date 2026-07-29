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

## Deploy to players (always after player-facing updates)

Whenever you change code that ships in the beta for players (UI, capture, AI client, hotkeys, etc.):

1. Build: `.\.venv\Scripts\python -m PyInstaller --noconfirm build_exe.spec`  
   (prefer **without** `--clean` if `--clean` crashes on this machine)
2. Upload the asset to the latest GitHub Release (download URL used by the site):

```bat
gh release upload v0.1.0-beta dist\Viewing.exe --clobber -R Kalekakektop2/Viewing-application
```

3. Players get it from:  
   https://github.com/Kalekakektop2/Viewing-application/releases/latest/download/Viewing.exe  
   (buttons «Скачать бета» on game-vision-site point here)

Do this **every time** after such updates — do not leave a newer local `dist\Viewing.exe` unpublished.
