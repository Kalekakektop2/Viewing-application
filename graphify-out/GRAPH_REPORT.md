# Graph Report - .  (2026-07-29)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 173 nodes · 359 edges · 11 communities (9 shown, 2 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 31 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `132fb51f`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Community 0
- Community 1
- Community 2
- Community 3
- Community 4
- Community 5
- Community 6
- Community 7
- Community 8
- Community 9
- Community 10

## God Nodes (most connected - your core abstractions)
1. `OverlayPanel` - 32 edges
2. `AppController` - 26 edges
3. `VisionClient` - 22 edges
4. `ItemCache` - 19 edges
5. `Settings` - 18 edges
6. `RegionSelector` - 16 edges
7. `GameSession` - 15 edges
8. `AnalysisResult` - 14 edges
9. `HotkeyService` - 13 edges
10. `Bridge` - 12 edges

## Surprising Connections (you probably didn't know these)
- `AnalysisResult` --uses--> `ItemCache`  [INFERRED]
  src/viewing_app/ai/client.py → src/viewing_app/cache/store.py
- `AnalysisResult` --uses--> `Settings`  [INFERRED]
  src/viewing_app/ai/client.py → src/viewing_app/config.py
- `AnalysisResult` --uses--> `GameSession`  [INFERRED]
  src/viewing_app/ai/client.py → src/viewing_app/session.py
- `OverlayPanel` --uses--> `AnalysisResult`  [INFERRED]
  src/viewing_app/ui/overlay.py → src/viewing_app/ai/client.py
- `Worker` --uses--> `AnalysisResult`  [INFERRED]
  src/viewing_app/ui/overlay.py → src/viewing_app/ai/client.py

## Import Cycles
- None detected.

## Communities (11 total, 2 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.12
Nodes (17): QDialog, _normalize_backend_url(), _project_root(), Path, Dev: repo root. Frozen .exe: folder next to the executable., Path to bundled resource (PyInstaller _MEIPASS) or project assets., Force working Vercel proxy; reject dead Netlify function URLs., resource_path() (+9 more)

### Community 1 - "Community 1"
Cohesion: 0.12
Nodes (8): QThread, OverlayPanel, Image, QWidget, Show HUD and immediately run default analysis (what + craft)., When player flips Кратко/Расширенно after an answer — re-query AI., Wide horizontal HUD overlay. Click outside to close., Worker

### Community 2 - "Community 2"
Cohesion: 0.14
Nodes (10): ActivationReason, QApplication, QIcon, Slot, AppController, build_app_icon(), _install_crash_hooks(), _log() (+2 more)

### Community 3 - "Community 3"
Cohesion: 0.16
Nodes (8): _HotkeyHost, HotkeyService, MSG, parse_hotkey_win(), QObject, QWidget, Global hotkey via Win32 RegisterHotKey on a dedicated host window., Tiny native window that owns RegisterHotKey HWND. Handles WM_HOTKEY only on…

### Community 4 - "Community 4"
Cohesion: 0.17
Nodes (6): grab_region(), Image, QWidget, Fullscreen dim overlay; drag to select a rectangle., Region, RegionSelector

### Community 5 - "Community 5"
Cohesion: 0.29
Nodes (5): AnalysisResult, Image, VisionClient, build_analysis_prompt(), build_image_prompt()

### Community 6 - "Community 6"
Cohesion: 0.23
Nodes (3): ItemCache, Path, Simple file cache for banal/common item answers.

### Community 7 - "Community 7"
Cohesion: 0.22
Nodes (4): ChatTurn, GameSession, Holds game context for the current play session., Update detected game. Returns a warning string for the player if needed.

### Community 8 - "Community 8"
Cohesion: 0.25
Nodes (5): Bridge, QObject, QWidget, Control panel (tray companion). Closing does not quit the app., TrayWindow

## Knowledge Gaps
- **2 isolated node(s):** `viewing-application`, `MSG`
  These have ≤1 connection - possible missing edges or undocumented components.
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `OverlayPanel` connect `Community 1` to `Community 8`, `Community 0`, `Community 2`, `Community 5`?**
  _High betweenness centrality (0.251) - this node is a cross-community bridge._
- **Why does `AppController` connect `Community 2` to `Community 0`, `Community 1`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 8`?**
  _High betweenness centrality (0.209) - this node is a cross-community bridge._
- **Why does `ItemCache` connect `Community 6` to `Community 0`, `Community 2`, `Community 5`, `Community 7`, `Community 8`?**
  _High betweenness centrality (0.123) - this node is a cross-community bridge._
- **Are the 5 inferred relationships involving `OverlayPanel` (e.g. with `AppController` and `Bridge`) actually correct?**
  _`OverlayPanel` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `AppController` (e.g. with `VisionClient` and `ItemCache`) actually correct?**
  _`AppController` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `VisionClient` (e.g. with `ItemCache` and `Settings`) actually correct?**
  _`VisionClient` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `ItemCache` (e.g. with `AnalysisResult` and `VisionClient`) actually correct?**
  _`ItemCache` has 4 INFERRED edges - model-reasoned connections that need verification._